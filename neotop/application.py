#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Copyright 2018, Nigel Small
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
"""

from __future__ import unicode_literals

from os import getenv
from threading import Thread
from time import sleep

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, VSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from neotop.controls.overview import OverviewControl
from neotop.controls.server import ServerControl


NEO4J_ADDRESS = getenv("NEO4J_ADDRESS", "localhost:7687")
NEO4J_AUTH = tuple(getenv("NEO4J_AUTH", "neo4j:password").partition(":")[::2])


class Neotop(Application):

    style = Style.from_dict({
        # TODO
    })

    def __init__(self):
        self.panel = ServerControl(NEO4J_ADDRESS, NEO4J_AUTH)
        self.overview = OverviewControl(NEO4J_ADDRESS, NEO4J_AUTH, on_select=self.panel.database.set_address)
        self.panel_window = Window(content=self.panel.control)
        self.separator_window = Window(width=0, dont_extend_width=True)
        self.overview_window = Window(content=self.overview, width=0, dont_extend_width=False)
        super(Neotop, self).__init__(
            layout=Layout(
                VSplit([
                    self.panel_window,
                    self.separator_window,
                    self.overview_window,
                ]),
            ),
            key_bindings=self.bindings,
            style=self.style,
            # mouse_support=True,
            full_screen=True,
        )
        self.payload_key = "query"
        self.changed = False
        self.running = True
        self.loop_thread = Thread(target=self.loop)
        self.loop_thread.start()

    def loop(self):
        while self.running:
            self.update_info()
            self.update_content()
            self.changed = False
            self.sleep()

    def update_info(self):
        self.panel.database.update()

    def update_content(self):
        self.panel.update_content()
        self.invalidate()

    def sleep(self):
        for _ in range(10):
            if self.running and not self.changed:
                sleep(0.1)
            else:
                return

    @property
    def bindings(self):
        bindings = KeyBindings()
        bindings.add('c-c')(self.do_exit)
        bindings.add('i')(self.action(self.panel.set_indexes_payload))
        bindings.add('m')(self.action(self.panel.set_metadata_payload))
        bindings.add('p')(self.action(self.panel.set_parameters_payload))
        bindings.add('q')(self.action(self.panel.set_query_payload))
        bindings.add('f12')(self.toggle_overview)
        bindings.add('home')(self.action(self.overview.home))
        bindings.add('end')(self.action(self.overview.end))
        bindings.add('pageup')(self.action(self.overview.page_up))
        bindings.add('pagedown')(self.action(self.overview.page_down))
        return bindings

    def action(self, handler, *args, **kwargs):

        def f(event):
            self.changed = handler(event, *args, **kwargs)

        return f

    def toggle_overview(self, _):
        if self.overview_window.width == 0:
            self.overview_window.width = self.overview.max_width
            if self.overview_window.width:
                self.separator_window.width = 1
                self.changed = True
            else:
                self.separator_window.width = 0
                self.changed = False
        else:
            self.overview_window.width = 0
            self.separator_window.width = 0
            self.changed = True

    def do_exit(self, _):
        self.overview.close()
        self.running = False
        get_app().exit(result=0)
