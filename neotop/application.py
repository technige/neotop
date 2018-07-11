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

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, VSplit, HSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame

from neotop.controls.overview import OverviewControl
from neotop.controls.server import ServerControl


NEO4J_ADDRESS = getenv("NEO4J_ADDRESS", "localhost:7687")
NEO4J_AUTH = tuple(getenv("NEO4J_AUTH", "neo4j:password").partition(":")[::2])


class Neotop(Application):

    style = Style.from_dict({
        # TODO
    })

    def __init__(self, address=None, user=None, password=None):
        host, _, port = (address or "localhost:7687").partition(":")
        self.address = "%s:%s" % (host or "localhost", port or 7687)
        self.user = user or "neo4j"
        self.auth = (self.user, password or "")
        self.overview = OverviewControl(self.address, self.auth)
        self.overview_visible = False
        self.overview_window = Window(content=self.overview, dont_extend_width=True)
        self.server_windows = [Window(content=ServerControl(self.address, self.auth, self.overview.add_highlight()))]
        super(Neotop, self).__init__(
            key_bindings=self.bindings,
            style=self.style,
            # mouse_support=True,
            full_screen=True,
        )
        self.update_layout()

    def update_layout(self):
        if self.overview_visible:
            self.layout = Layout(
                VSplit([
                    HSplit(self.server_windows),
                    Frame(self.overview_window),
                ]),
            )
        else:
            self.layout = Layout(
                VSplit([
                    HSplit(self.server_windows),
                ]),
            )

    def insert(self, event):
        address_style = self.overview.add_highlight()
        if address_style is not None:
            selected_address = self.overview.selected_address
            for window in self.server_windows:
                if window.content.address == selected_address:
                    return
            self.server_windows.append(Window(content=ServerControl(selected_address, self.auth, address_style)))
            self.update_layout()

    def delete(self, event):
        if len(self.server_windows) > 1:
            selected_address = self.overview.selected_address
            for window in list(self.server_windows):
                if window.content.address == selected_address:
                    window.content.exit()
                    self.server_windows.remove(window)
                    self.overview.remove_highlight()
            self.update_layout()

    @property
    def bindings(self):
        bindings = KeyBindings()
        bindings.add('c-c')(self.do_exit)
        bindings.add('i')(self.action(self.server_windows[0].content.set_payload_key, "indexes"))
        bindings.add('m')(self.action(self.server_windows[0].content.set_payload_key, "metaData"))
        bindings.add('p')(self.action(self.server_windows[0].content.set_payload_key, "parameters"))
        bindings.add('q')(self.action(self.server_windows[0].content.set_payload_key, "query"))
        bindings.add('f12')(self.toggle_overview)
        bindings.add('insert')(self.action(self.insert))
        bindings.add('delete')(self.action(self.delete))
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
        self.overview_visible = not self.overview_visible
        self.update_layout()

    def do_exit(self, _):
        self.overview.exit()
        for window in self.server_windows:
            window.content.exit()
        get_app().exit(result=0)
