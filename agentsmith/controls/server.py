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


from __future__ import unicode_literals

from prompt_toolkit.layout import UIContent

from agentsmith.controls.data import DataControl


DEFAULT_FIELDS = [
    ("", "TXID"),
    ("", "USER"),
    ("", "CLIENT"),
    ("", "  MEM"),
    ("", "LOCKS"),
    ("", " HITS"),
    ("", " FLTS"),
    ("", " TIME"),
    ("", "  CPU"),
    ("", " WAIT"),
    ("", " IDLE"),
    ("", "QUERY"),
]
DEFAULT_ALIGNMENTS = [
    ">",
    "<",
    "<",
    ">",
    ">",
    ">",
    ">",
    ">",
    ">",
    ">",
    ">",
    "<",
]


class ServerControl(DataControl):

    overview = None
    data = None

    def __init__(self, application, address, auth):
        super(ServerControl, self).__init__(address, auth)
        self.application = application
        self.transactions = []
        self.title = []
        self.lines = [
            self.title,
            [("", "")],
        ]
        self.alignments = ["<"]
        self.status_style = self.application.style_list.get_style(self.address)
        self.header_style = "class:data-header"
        self.selected_txid = None
        self.error = None

    def set_fields(self, fields):
        self.lines[1] = list(fields or [("", "")])

    def set_alignments(self, alignments):
        self.alignments[:] = list(alignments or ["<"])

    def clear(self):
        self.lines[2:] = []

    def append(self, values):
        self.lines.append([(style, str(value)) for style, value in values])

    def widths(self):
        widths = list(map(len, self.lines[1]))
        for row in self.lines[1:]:
            for x, (_, cell) in enumerate(row):
                size = len(cell)
                if size > widths[x]:
                    widths[x] = size
        return widths

    def on_refresh(self, data):
        self.data = data
        if self.data is None:
            self.invalidate.fire()
            return
        self.clear()
        self.set_fields(DEFAULT_FIELDS)
        self.set_alignments(DEFAULT_ALIGNMENTS)

        def stat_tuple(stat):
            s = str(stat)
            if s == "0" or s == "~":
                return "class:data-secondary", s
            else:
                return "class:data-primary", s

        self.transactions[:] = sorted(self.data.transactions, key=lambda q0: q0.elapsed_time, reverse=True)
        for tx in self.transactions:
            tx.current_query = tx.current_query.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            if tx.protocol or tx.client_address:
                client = "{}/{}".format(tx.client_address, tx.protocol[0].upper())
            else:
                client = ""
            if tx.status == "running":
                payload_style = "class:data-status-running"
            elif tx.status == "planning":
                payload_style = "class:data-status-planning"
            else:
                payload_style = ""
            self.append([
                ("class:data-primary", tx.id),
                ("class:data-secondary" if tx.user == "neo4j" else "class:data-primary", tx.user),
                ("class:data-primary", client),
                ("class:data-primary", tx.allocated_bytes),
                stat_tuple(tx.active_lock_count),
                stat_tuple(tx.page_hits),
                stat_tuple(tx.page_faults),
                stat_tuple(tx.elapsed_time),
                stat_tuple(tx.cpu_time),
                stat_tuple(tx.wait_time),
                stat_tuple(tx.idle_time),
                (payload_style, tx.current_query),
            ])
        self.error = None
        self.invalidate.fire()

    def on_error(self, error):
        self.error = error

    def has_focus(self):
        return self.application.focused_address == self.address

    def create_content(self, width, height):

        widths = self.widths()
        used_width = sum(widths)
        widths[-1] += width - used_width

        def get_status_line():
            if self.error:
                status_text = " {} down -- {}".format(self.address, self.error)
                # style = "fg:ansiwhite bg:ansired"
                style = "class:server-header-focus fg:ansibrightred" if self.has_focus() else "class:server-header fg:ansibrightred"
            elif self.data:
                status_text = " {} {}, {}, {}".format(
                    self.address,
                    self.data.system.status_text(),
                    self.data.memory.heap_meter(10),
                    self.data.system.cpu_meter(10))
                # status_text += ", tx={}".format(self.data.transactions.begin_count)
                # status_text += ", store={}".format(self.data.storage.total_store_size)
                style = "class:server-header-focus" if self.has_focus() else "class:server-header"
            else:
                # no data yet
                status_text = " {} connecting...".format(self.address)
                style = "class:server-header-focus" if self.has_focus() else "class:server-header fg:ansiyellow"
            return [
                (self.status_style, "  "),
                (style, status_text.ljust(width - 2)),
            ]

        def get_header_line():
            line = []
            if self.data is None:
                pass
            elif self.transactions is None:
                dbms = self.data.system.dbms
                message = "Transaction list not available in Neo4j {}.{} {}".format(
                    dbms.version.major, dbms.version.minor, dbms.edition)
                line.append((self.header_style, message.ljust(width)))
            else:
                try:
                    li = self.lines[1]
                except IndexError:
                    pass
                else:
                    for x, (_, cell) in enumerate(li):
                        if x > 0:
                            line.append((self.header_style, " "))
                        alignment = self.alignments[x]
                        cell_width = widths[x]
                        if alignment == ">":
                            line.append((self.header_style, cell.rjust(cell_width)))
                        else:
                            line.append((self.header_style, cell.ljust(cell_width)))
            return line

        def get_data_line(y):
            line = []
            if self.data is None:
                pass
            elif self.data.transactions is None:
                pass
            else:
                try:
                    li = self.lines[y]
                except IndexError:
                    pass
                else:
                    selected = str(self.selected_txid) == li[0][1]
                    for x, (style, cell) in enumerate(li):
                        if self.has_focus() and selected:
                            style = "class:data-highlight"
                        if x > 0:
                            line.append((style, " "))
                        alignment = self.alignments[x]
                        cell_width = widths[x]
                        if alignment == ">":
                            line.append((style, cell.rjust(cell_width)))
                        else:
                            line.append((style, cell.ljust(cell_width)))
            return line

        def get_line(y):
            if y == 0:
                return get_status_line()
            elif y == 1:
                return get_header_line()
            else:
                return get_data_line(y)

        return UIContent(
            get_line=get_line,
            line_count=len(self.lines),
            show_cursor=False,
        )

    def up(self, event):
        new_selected_txid = None
        for tx in self.transactions:
            if tx.id == self.selected_txid:
                break
            else:
                new_selected_txid = tx.id
        if new_selected_txid != self.selected_txid:
            self.selected_txid = new_selected_txid
            self.invalidate.fire()

    def down(self, event):
        new_selected_txid = None
        for tx in reversed(self.transactions):
            if tx.id == self.selected_txid:
                break
            else:
                new_selected_txid = tx.id
        # print("%s -> %s" % (self.selected_txid, new_selected_txid), end="")
        if new_selected_txid != self.selected_txid:
            self.selected_txid = new_selected_txid
            self.invalidate.fire()

    def kill(self, event):
        for tx in self.transactions:
            if tx.id == self.selected_txid:
                self.monitor.kill(tx)
