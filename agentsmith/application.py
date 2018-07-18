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

from neo4j.exceptions import ServiceUnavailable
from neo4j.v1 import SessionExpired
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl
from prompt_toolkit.layout.containers import Window, VSplit, HSplit, WindowAlign
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from agentsmith.controls.overview import OverviewControl, StyleList
from agentsmith.controls.server import ServerControl
from agentsmith.meta import __version__


NEO4J_ADDRESS = getenv("NEO4J_ADDRESS", "localhost:7687")
NEO4J_AUTH = tuple(getenv("NEO4J_AUTH", "neo4j:password").partition(":")[::2])


class Smith(Application):

    overview_control = None
    overview = None

    style = Style.from_dict({
        # TODO
    })

    def __init__(self, address=None, user=None, password=None):
        host, _, port = (address or "localhost:7687").partition(":")
        self.address = "%s:%s" % (host or "localhost", port or 7687)
        self.user = user or "neo4j"
        self.auth = (self.user, password or "")
        self.style_list = StyleList()
        primary_server = ServerControl(self.address, self.auth, self.style_list.assign_style(self.address))
        self.server_windows = [Window(content=primary_server)]
        self.header = Window(content=FormattedTextControl(text="Agent Smith {}".format(__version__)), always_hide_cursor=True,
                             height=1, dont_extend_height=True, style="bg:#202020 fg:ansiwhite")
        self.footer = Window(content=FormattedTextControl(text="[Ctrl+C] Exit  [F12] Overview"), always_hide_cursor=True,
                             height=1, dont_extend_height=True, style="bg:#202020 fg:ansiwhite")
        super(Smith, self).__init__(
            key_bindings=self.bindings,
            style=self.style,
            # mouse_support=True,
            full_screen=True,
        )
        self.update_layout()

    def update_layout(self):
        if self.overview:
            self.layout = Layout(
                HSplit([
                    self.header,
                    VSplit([
                        HSplit(self.server_windows),
                        HSplit([
                            self.overview,
                            Window(FormattedTextControl(text="[Ins ][Home][PgUp]\n[Del ][End ][PgDn]"),
                                   style="bg:#202020 fg:ansigray", height=2, align=WindowAlign.CENTER,
                                   dont_extend_height=True),
                        ]),
                    ]),
                    self.footer,
                ]),
            )
        else:
            self.layout = Layout(
                HSplit([
                    self.header,
                    VSplit([
                        HSplit(self.server_windows),
                    ]),
                    self.footer,
                ]),
            )

    def insert(self, event):
        address_style = self.overview.content.add_highlight()
        if address_style is not None:
            selected_address = self.overview.content.selected_address
            for window in self.server_windows:
                if window.content.address == selected_address:
                    return
            self.server_windows.append(Window(content=ServerControl(selected_address, self.auth, address_style)))
            self.update_layout()

    def delete(self, event):
        if len(self.server_windows) > 1:
            selected_address = self.overview.content.selected_address
            for window in list(self.server_windows):
                if window.content.address == selected_address:
                    window.content.exit()
                    self.server_windows.remove(window)
                    self.overview.content.remove_highlight()
            self.update_layout()

    @property
    def bindings(self):
        bindings = KeyBindings()
        bindings.add('c-c')(self.do_exit)

        bindings.add('0')(self.toggle_overview)
        bindings.add('f12')(self.toggle_overview)

        bindings.add('insert')(self.action(self.insert))
        bindings.add('+')(self.action(self.insert))
        bindings.add('delete')(self.action(self.delete))
        bindings.add('-')(self.action(self.delete))
        bindings.add('home')(self.action(self.home))
        bindings.add('end')(self.action(self.end))
        bindings.add('pageup')(self.action(self.page_up))
        bindings.add('pagedown')(self.action(self.page_down))

        return bindings

    def home(self, event):
        if self.overview:
            return self.overview.content.home(event)

    def end(self, event):
        if self.overview:
            return self.overview.content.end(event)

    def page_up(self, event):
        if self.overview:
            return self.overview.content.page_up(event)

    def page_down(self, event):
        if self.overview:
            return self.overview.content.page_down(event)

    def action(self, handler, *args, **kwargs):

        def f(event):
            self.changed = handler(event, *args, **kwargs)

        return f

    def toggle_overview(self, _):
        if self.overview is None:
            if self.overview_control is None:
                try:
                    self.overview_control = OverviewControl(self.address, self.auth, self.style_list)
                except (ServiceUnavailable, SessionExpired):
                    pass
            if self.overview_control:
                self.overview = Window(content=self.overview_control, width=20, dont_extend_width=True, style="bg:#202020")
        else:
            self.overview = None
        self.update_layout()

    def do_exit(self, _):
        if self.overview_control:
            self.overview_control.exit()
        for window in self.server_windows:
            window.content.exit()
        get_app().exit(result=0)
