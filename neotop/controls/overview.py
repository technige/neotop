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


from neo4j.v1 import urlparse, CypherError
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
        self.mode = None
        self.servers = dict.fromkeys(self.server_roles, [])
        self.address_styles = {}
        self.unused_styles = {
            "fg:ansiwhite bg:ansiblue",
            "fg:ansiwhite bg:ansicyan",
            "fg:ansiwhite bg:ansimagenta",
            "fg:ansiwhite bg:ansiyellow",
        }
        self.max_width = 0
        self.padding = 0
        self.selected_role = u"LEADER"
        self.selected_index = 0

    def preferred_width(self, max_available_width):
        return self.max_width

    def fetch_data(self, tx):
        if self.edition != "enterprise":
            # print("Neotop requires Neo4j Enterprise Edition (%s Edition found)" % self.edition.title())
            return
        try:
            config = {}
            for record in tx.run("CALL dbms.listConfig"):
                config[record["name"]] = record["value"]
        except CypherError as error:
            if error.code == "Neo.ClientError.Security.Forbidden":
                self.mode = u"UNKNOWN"
            else:
                raise
        else:
            self.mode = config[u"dbms.mode"]
        if self.mode == u"CORE":
            overview = tx.run("CALL dbms.cluster.overview").data()
            widths = [0]
            for role in self.servers:
                self.servers[role] = [urlparse(server[u"addresses"][0]).netloc
                                      for server in overview if server[u"role"] == role]
                widths.extend(map(len, self.servers[role]))
            self.max_width = max(widths)
        else:
            self.servers[u"LEADER"] = [self.address]
            self.max_width = len(self.address)
        self.padding = 6 if self.max_width % 2 == 0 else 5
        self.max_width += self.padding

    def create_content(self, width, height):
        lines = []

        def append_servers(role):
            for i, address in enumerate(self.servers[role]):
                address_style = self.address_styles.get(address, "")
                if role == self.selected_role and i == self.selected_index:
                    lines.append([
                        ("", " "),
                        (address_style, "  "),
                        ("", " "),
                        ("fg:ansiblack bg:ansigray", address.ljust(width - self.padding)),
                        ("", " "),
                    ])
                else:
                    lines.append([
                        ("", " "),
                        (address_style, "  "),
                        ("", " "),
                        ("", address.ljust(width - self.padding)),
                        ("", " "),
                    ])

        if self.servers[u"LEADER"]:
            if self.mode == u"CORE":
                lines.append([("fg:#A0A0A0", " Leader".ljust(width))])
            else:
                lines.append([("fg:#A0A0A0", " Server".ljust(width))])
            append_servers(u"LEADER")
            lines.append([])
        if self.servers[u"FOLLOWER"]:
            lines.append([("fg:#A0A0A0", " Followers".ljust(width))])
            append_servers(u"FOLLOWER")
            lines.append([])
        if self.servers[u"READ_REPLICA"]:
            lines.append([("fg:#A0A0A0", " Read replicas".ljust(width))])
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
        try:
            return self.servers[self.selected_role][self.selected_index]
        except IndexError:
            return self.address

    def add_highlight(self):
        address = self.selected_address
        if address not in self.address_styles and self.unused_styles:
            address_style = sorted(self.unused_styles)[0]
            self.unused_styles.remove(address_style)
            self.address_styles[address] = address_style
        return self.address_styles.get(address)

    def remove_highlight(self):
        address = self.selected_address
        if address in self.address_styles:
            address_style = self.address_styles[address]
            self.unused_styles.add(address_style)
            del self.address_styles[address]
            return address_style
        return None

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
        y = -1
        while not self.servers[self.server_roles[y]]:
            y -= 1
        selected_role = self.server_roles[y]
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
