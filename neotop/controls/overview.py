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


from neo4j.v1 import urlparse
from prompt_toolkit.layout import UIContent

from neotop.controls.data import DataControl


class OverviewControl(DataControl):

    server_roles = [
        u"LEADER",
        u"FOLLOWER",
        u"READ_REPLICA",
    ]

    def __init__(self, address, auth):
        super(OverviewControl, self).__init__(address, auth)
        self.config = {}
        self.mode = None
        self.servers = dict.fromkeys(self.server_roles, [])
        self.max_width = 0
        self.selected_role = u"LEADER"
        self.selected_index = 0

    def preferred_width(self, max_available_width):
        return self.max_width

    def fetch_data(self, tx):
        self.config.clear()
        for record in tx.run("CALL dbms.listConfig"):
            self.config[record["name"]] = record["value"]
        self.mode = self.config[u"dbms.mode"]
        if self.mode == u"CORE":
            overview = tx.run("CALL dbms.cluster.overview").data()
            widths = [0]
            for role in self.servers:
                self.servers[role] = [urlparse(server[u"addresses"][0]).netloc
                                      for server in overview if server[u"role"] == role]
                widths.extend(map(len, self.servers[role]))
            self.max_width = max(widths) + 4
        elif self.mode == u"SINGLE":
            self.servers[u"LEADER"] = [self.address]
            self.max_width = len(self.address) + 4

    def create_content(self, width, height):
        lines = []

        def append_servers(role):
            for i, server in enumerate(self.servers[role]):
                if role == self.selected_role and i == self.selected_index:
                    lines.append([
                        ("", " "),
                        ("fg:ansigreen", ">"),
                        ("", " "),
                        ("", server.ljust(width - 4)),
                        ("", " "),
                    ])
                else:
                    lines.append([
                        ("", "   "),
                        ("", server.ljust(width - 4)),
                        ("", " "),
                    ])

        if self.servers[u"LEADER"]:
            if self.mode == u"CORE":
                lines.append([("fg:ansibrightblack", " Leader".ljust(width))])
            else:
                lines.append([("fg:ansibrightblack", " Single".ljust(width))])
            append_servers(u"LEADER")
            lines.append([])
        if self.servers[u"FOLLOWER"]:
            lines.append([("fg:ansibrightblack", " Followers".ljust(width))])
            append_servers(u"FOLLOWER")
            lines.append([])
        if self.servers[u"READ_REPLICA"]:
            lines.append([("fg:ansibrightblack", " Read replicas".ljust(width))])
            append_servers(u"READ_REPLICA")
            lines.append([])

        def get_line(y):
            return lines[y]

        return UIContent(
            get_line=get_line,
            line_count=len(lines),
            show_cursor=False,
        )

    @property
    def selected_address(self):
        return self.servers[self.selected_role][self.selected_index]

    def home(self, event):
        if not self.servers[self.selected_role]:
            return False
        selected_role = self.server_roles[0]
        selected_index = 0
        if selected_role != self.selected_role or selected_index != self.selected_index:
            self.selected_role = selected_role
            self.selected_index = selected_index
            return True
        else:
            return False

    def end(self, event):
        if not self.servers[self.selected_role]:
            return False
        selected_role = self.server_roles[-1]
        selected_index = len(self.servers[self.selected_role]) - 1
        if selected_role != self.selected_role or selected_index != self.selected_index:
            self.selected_role = selected_role
            self.selected_index = selected_index
            return True
        else:
            return False

    def page_up(self, event):
        if not self.servers[self.selected_role]:
            return False
        self.selected_index -= 1
        while self.selected_index < 0:
            old_role_index = self.server_roles.index(self.selected_role)
            new_role_index = (old_role_index - 1) % len(self.server_roles)
            self.selected_role = self.server_roles[new_role_index]
            self.selected_index = len(self.servers[self.selected_role]) - 1
        return True

    def page_down(self, event):
        if not self.servers[self.selected_role]:
            return False
        self.selected_index += 1
        while self.selected_index >= len(self.servers[self.selected_role]):
            old_role_index = self.server_roles.index(self.selected_role)
            new_role_index = (old_role_index + 1) % len(self.server_roles)
            self.selected_role = self.server_roles[new_role_index]
            self.selected_index = 0
        return True
