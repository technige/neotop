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

from prompt_toolkit.layout import UIContent, UIControl
from prompt_toolkit.utils import Event

from neotop.monitor import ServerMonitor


DEFAULT_FIELDS = [
    ("", "QID"),
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


class ServerControl(UIControl):

    data = None

    def __init__(self, address, auth, status_style):
        self.address = address
        self.title = []
        self.lines = [
            self.title,
            [("", "")],
        ]
        self.alignments = ["<"]
        self.payload_key = "text"
        self.status_style = status_style
        self.header_style = "fg:ansiwhite bg:ansibrightblack"

        self.monitor = ServerMonitor(address, auth, on_error=self.set_error)     # TODO: display errors
        self.monitor.add_refresh_handler(self.on_refresh)
        self.invalidate = Event(self)
        self.error = None

    def set_error(self, error):
        self.error = error

    def set_payload_key(self, event, key):
        self.payload_key = key
        return True

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
        self.title[:] = [(self.status_style, "  "), ("fg:ansiblack bg:ansigray", " ")]
        self.clear()
        self.set_fields(DEFAULT_FIELDS)
        self.set_alignments(DEFAULT_ALIGNMENTS)
        title = str(self.data.system)
        self.lines[1][-1] = ("", self.payload_key.upper())
        for q in sorted(self.data.queries, key=lambda q0: q0.elapsed_time, reverse=True):
            # q["queryId"] = q["queryId"].partition("-")[-1]
            q.text = q.text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            client = "{}/{}".format(q.protocol[0].upper(), q.client_address)
            if q.status == "running":
                payload_style = "fg:ansigreen"
            elif q.status == "planning":
                payload_style = "fg:ansiblue"
            else:
                print(q.status)
                payload_style = ""
            self.append([
                ("", q.id),
                ("fg:ansibrightblack" if q.user == "neo4j" else "", q.user),
                ("", client),
                ("", q.allocated_bytes),
                ("", q.active_lock_count),
                ("", q.page_hits),
                ("", q.page_faults),
                ("", q.elapsed_time),
                ("", q.cpu_time),
                ("", q.wait_time),
                ("", q.idle_time),
                (payload_style, getattr(q, self.payload_key)),
            ])
        self.title.append(("fg:ansiblack bg:ansigray", title))
        self.invalidate.fire()

    def get_invalidate_events(self):
        """
        Return the Window invalidate events.
        """
        yield self.invalidate

    def create_content(self, width, height):
        widths = self.widths()
        used_width = sum(widths)
        widths[-1] += width - used_width

        def get_status_line():
            if self.data:
                status_text = " {} {}".format(self.address, self.data.system.status_text())
                # status_text += ", tx={}".format(self.data.transactions.begin_count)
                # status_text += ", store={}".format(self.data.storage.total_store_size)
                meters = self.data.memory.heap_meter(10) + " " + self.data.system.cpu_meter(10)
                status_text = status_text.ljust(76 - len(meters)) + "  " + meters
                style = "fg:ansiblack bg:ansigray"
            else:
                status_text = " {} unavailable -- {}".format(self.address, self.error)
                style = "fg:ansiwhite bg:ansired"
            return [
                (self.status_style, "  "),
                (style, status_text.ljust(width - 2)),
            ]

        def get_line(y):
            if y == 0:
                return get_status_line()
            line = []
            try:
                li = self.lines[y]
            except IndexError:
                pass
            else:
                for x, (style, cell) in enumerate(li):
                    if y == 1:
                        style = self.header_style
                    if x > 0:
                        line.append((style, " "))
                    alignment = self.alignments[x]
                    cell_width = widths[x]
                    if alignment == ">":
                        line.append((style, cell.rjust(cell_width)))
                    else:
                        line.append((style, cell.ljust(cell_width)))
            return line

        return UIContent(
            get_line=get_line,
            line_count=len(self.lines),
            show_cursor=False,
        )

    def exit(self):
        self.monitor.exit()
