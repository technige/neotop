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


BASE03 = "#002b36"  # background
BASE02 = "#073642"  # background highlights
BASE01 = "#586e75"  # comments / secondary content
BASE00 = "#657b83"
BASE0 = "#839496"   # body text / default code / primary content
BASE1 = "#93a1a1"   # optional emphasized content
BASE2 = "#eee8d5"
BASE3 = "#fdf6e3"

YELLOW = "#b58900"
ORANGE = "#cb4b16"
RED = "#dc322f"
MAGENTA = "#d33682"
VIOLET = "#6c71c4"
BLUE = "#268bd2"
CYAN = "#2aa198"
GREEN = "#859900"


class AgentSmith(Application):

    overview_control = None
    overview = None

    style = Style.from_dict({
        "page-header": "fg:{} bg:{}".format(BASE1, BASE02),
        "page-footer": "fg:{} bg:{}".format(BASE1, BASE02),
        "overview": "fg:{} bg:{}".format(BASE0, BASE02),
        "server": "fg:{} bg:{}".format(BASE0, BASE03),
        "server-header-focus": "fg:{} bg:{}".format(BASE00, BASE3),
        "server-header": "fg:{} bg:{}".format(BASE1, BASE02),
        "data-header": BASE01,
        "data-primary": BASE0,
        "data-secondary": BASE01,
        "data-status-running": GREEN,
        "data-status-planning": CYAN,
        "member-1": "bg:{}".format("ansigreen"),
        "member-2": "bg:{}".format("ansicyan"),
        "member-3": "bg:{}".format("ansiblue"),
        "member-4": "bg:{}".format("ansibrightmagenta"),
        "member-5": "bg:{}".format("ansimagenta"),
        "member-6": "bg:{}".format("ansired"),
        "member-7": "bg:{}".format("ansibrightred"),
        "member-8": "bg:{}".format("ansiyellow"),
        # TODO
    })

    def __init__(self, address=None, user=None, password=None):
        host, _, port = (address or "localhost:7687").partition(":")
        self.address = "%s:%s" % (host or "localhost", port or 7687)
        self.user = user or "neo4j"
        self.auth = (self.user, password or "")
        self.style_list = StyleList()
        self.style_list.assign_style(self.address)
        primary_server = ServerControl(self, self.address, self.auth)
        self.server_windows = [Window(content=primary_server, style="class:server")]
        self.header = Window(content=FormattedTextControl(text="AGENT SMITH v{}".format(__version__)), always_hide_cursor=True,
                             height=1, dont_extend_height=True, style="class:page-header")
        self.footer = Window(content=FormattedTextControl(text="[O] Overview  [Ctrl+C] Exit"), always_hide_cursor=True,
                             height=1, dont_extend_height=True, style="class:page-footer")
        self.focus_index = 0
        super(AgentSmith, self).__init__(
            key_bindings=self.bindings,
            style=self.style,
            # mouse_support=True,
            full_screen=True,
        )
        self.update_layout()

    @property
    def focused_address(self):
        if self.overview:
            return self.overview.content.focused_address
        else:
            return self.server_windows[self.focus_index].content.address

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
                                   style="class:overview", height=2, align=WindowAlign.CENTER,
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

    def on_selection_change(self):
        windows = []
        old_addresses = [window.content.address for window in self.server_windows]
        for address in self.overview.content.selected_addresses:
            try:
                address_index = old_addresses.index(address)
            except ValueError:
                windows.append(Window(content=ServerControl(self, address, self.auth), style="class:server"))
            else:
                windows.append(self.server_windows[address_index])
        self.server_windows[:] = windows
        self.update_layout()

    def insert(self, event):
        address_style = self.style_list.assign_style(self.overview.content.focused_address)
        if address_style is not None:
            selected_address = self.overview.content.focused_address
            for window in self.server_windows:
                if window.content.address == selected_address:
                    return
            self.on_selection_change()

    def delete(self, event):
        if len(self.server_windows) > 1:
            selected_address = self.overview.content.focused_address
            for window in list(self.server_windows):
                if window.content.address == selected_address:
                    window.content.exit()
                    self.style_list.unassign_style(self.overview.content.focused_address)
                    self.on_selection_change()

    @property
    def bindings(self):
        bindings = KeyBindings()
        bindings.add('c-c')(self.do_exit)

        bindings.add('o')(self.toggle_overview)
        bindings.add('f12')(self.toggle_overview)

        bindings.add('insert')(self.action(self.insert))
        bindings.add('+')(self.action(self.insert))
        bindings.add('delete')(self.action(self.delete))
        bindings.add('-')(self.action(self.delete))
        bindings.add('home')(self.action(self.home))
        bindings.add('end')(self.action(self.end))
        bindings.add('pageup')(self.action(self.page_up))
        bindings.add('pagedown')(self.action(self.page_down))
        bindings.add('down')(self.action(self.down))

        return bindings

    def home(self, event):
        if self.overview:
            return self.overview.content.home(event)
        elif self.focus_index == 0:
            return False
        else:
            self.focus_index = 0
            return True

    def end(self, event):
        if self.overview:
            return self.overview.content.end(event)
        elif self.focus_index == len(self.server_windows) - 1:
            return False
        else:
            self.focus_index = len(self.server_windows) - 1
            return True

    def page_up(self, event):
        if self.overview:
            return self.overview.content.page_up(event)
        new_focus_index = (self.focus_index - 1) % len(self.server_windows)
        if self.focus_index == new_focus_index:
            return False
        else:
            self.focus_index = new_focus_index
            return True

    def page_down(self, event):
        if self.overview:
            return self.overview.content.page_down(event)
        new_focus_index = (self.focus_index + 1) % len(self.server_windows)
        if self.focus_index == new_focus_index:
            return False
        else:
            self.focus_index = new_focus_index
            return True

    @property
    def focused_window(self):
        return self.server_windows[self.focus_index]

    def down(self, event):
        self.focused_window.content.down(event)

    def action(self, handler, *args, **kwargs):

        def f(event):
            self.changed = handler(event, *args, **kwargs)

        return f

    def toggle_overview(self, _):
        if self.overview is None:
            # Turn overview on
            if self.overview_control is None:
                try:
                    self.overview_control = OverviewControl(self.address, self.auth, self.style_list)
                except (ServiceUnavailable, SessionExpired):
                    pass
            if self.overview_control:
                self.overview = Window(content=self.overview_control, width=20, dont_extend_width=True,
                                       style="class:overview")
                self.overview_control.focused_address = self.server_windows[self.focus_index].content.address
        else:
            # Turn overview off
            self.overview = None
            self.focus_index = 0
            for i, window in enumerate(self.server_windows):
                if window.content.address == self.overview_control.focused_address:
                    self.focus_index = i
                    break
        self.update_layout()

    def do_exit(self, _):
        if self.overview_control:
            self.overview_control.exit()
        for window in self.server_windows:
            window.content.exit()
        get_app().exit(result=0)
