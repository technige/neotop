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
        self.title = []
        self.lines = [
            self.title,
            [("", "")],
        ]
        self.alignments = ["<"]
        self.status_style = self.application.style_list.get_style(self.address)
        self.header_style = "class:data-header"
        self.selected_qid = None
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

        if self.data.transactions:
            for q in sorted(self.data.transactions, key=lambda q0: q0.elapsed_time, reverse=True):
                q.current_query = q.current_query.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
                if q.protocol or q.client_address:
                    client = "{}/{}".format(q.protocol[0].upper(), q.client_address)
                else:
                    client = ""
                if q.status == "running":
                    payload_style = "class:data-status-running"
                elif q.status == "planning":
                    payload_style = "class:data-status-planning"
                else:
                    payload_style = ""
                self.append([
                    ("class:data-primary", q.id),
                    ("class:data-secondary" if q.user == "neo4j" else "class:data-primary", q.user),
                    ("class:data-primary", client),
                    ("class:data-primary", q.allocated_bytes),
                    stat_tuple(q.active_lock_count),
                    stat_tuple(q.page_hits),
                    stat_tuple(q.page_faults),
                    stat_tuple(q.elapsed_time),
                    stat_tuple(q.cpu_time),
                    stat_tuple(q.wait_time),
                    stat_tuple(q.idle_time),
                    (payload_style, q.current_query),
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
                status_text = " {} unavailable -- {}".format(self.address, self.error)
                style = "fg:ansiwhite bg:ansired"
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
                style = "class:server-header-focus" if self.has_focus() else "fg:ansiblack bg:ansiyellow"
            return [
                (self.status_style, "  "),
                (style, status_text.ljust(width - 2)),
            ]

        def get_header_line():
            line = []
            if self.data is None:
                pass
            elif self.data.queries is None:
                message = "Query list not available"
                if self.data.system.dbms.edition == u"CE":
                    message += " in Neo4j Community Edition"
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
            elif self.data.queries is None:
                pass
            else:
                try:
                    li = self.lines[y]
                except IndexError:
                    pass
                else:
                    for x, (style, cell) in enumerate(li):
                        if x == 0 and self.has_focus() and str(self.selected_qid) == cell:
                            style = "bg:ansibrightgreen fg:ansiblack"
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

    def down(self, event):
        self.selected_qid = self.data.queries[0].id
        self.invalidate.fire()
