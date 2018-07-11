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

from neotop.config import Config
from neotop.controls.data import DataControl
from neotop.units import number_string, number_text, time_text


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


class ServerControl(DataControl):

    def __init__(self, address, auth, status_style):
        super(ServerControl, self).__init__(address, auth)
        self.title = []
        self.lines = [
            self.title,
            [("", "")],
        ]
        self.alignments = ["<"]
        self.payload_key = "query"
        self.config = None
        self.queries = None
        self.status_style = status_style
        self.header_style = "fg:ansiwhite bg:ansibrightblack"

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

    def fetch_data(self, tx):
        config_result = tx.run("CALL dbms.queryJmx('org.neo4j:*')")
        queries_result = tx.run("CALL dbms.listQueries")
        self.config = Config(config_result.data())
        self.queries = queries_result.data()
        self.update_content()

    def on_fetch_error(self, error):
        self.title[:] = [("bg:ansired", "  "), ("fg:ansiblack bg:ansigray", " ")]
        self.clear()
        self.set_fields([])
        self.set_alignments([])
        title = "{} down -- {}".format(self.address, error)
        self.title.append(("", title))

    def update_content(self):
        self.title[:] = [(self.status_style, "  "), ("fg:ansiblack bg:ansigray", " ")]
        self.clear()
        self.set_fields(DEFAULT_FIELDS)
        self.set_alignments(DEFAULT_ALIGNMENTS)
        k0 = self.config.instances[u"kernel#0"]
        title = ("{address} up {uptime}, "
                 "{major}.{minor}.{patch} "
                 "tx(b={begun} c={committed} r={rolled_back} hi={peak}) "
                 "store={store_size}").format(
            mode=k0.configuration[u"dbms.mode"][0],
            address=self.address,
            uptime=k0.kernel.uptime,
            store_size=number_string(k0.store_sizes[u"TotalStoreSize"], K=1024),
            product=k0.kernel.product_info[0],
            major=k0.kernel.product_info[1],
            minor=k0.kernel.product_info[2],
            patch=k0.kernel.product_info[3],
            begun=number_string(k0.transactions[u"NumberOfOpenedTransactions"]),
            committed=number_string(k0.transactions[u"NumberOfCommittedTransactions"]),
            rolled_back=number_string(k0.transactions[u"NumberOfRolledBackTransactions"]),
            peak=number_string(k0.transactions[u"PeakNumberOfConcurrentTransactions"]),
        )
        self.lines[1][-1] = ("", self.payload_key.upper())
        for q in sorted(self.queries, key=lambda q0: q0["elapsedTimeMillis"], reverse=True):
            q["queryId"] = q["queryId"].partition("-")[-1]
            q["query"] = q["query"].replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            client = "{}/{}".format(q["protocol"][0].upper(), q["clientAddress"])
            if q["status"] == "running":
                payload_style = "fg:ansigreen"
            elif q["status"] == "planning":
                payload_style = "fg:ansiblue"
            else:
                print(q["status"])
                payload_style = ""
            self.append([
                ("", q["queryId"]),
                ("fg:ansibrightblack" if q["username"] == "neo4j" else "", q["username"]),
                ("", client),
                number_text(q["allocatedBytes"], K=1024),
                number_text(q["activeLockCount"]),
                number_text(q["pageHits"]),
                number_text(q["pageFaults"]),
                time_text(q["elapsedTimeMillis"]),
                time_text(q["cpuTimeMillis"]),
                time_text(q["waitTimeMillis"]),
                time_text(q["idleTimeMillis"]),
                (payload_style, q[self.payload_key]),
            ])
        self.title.append(("fg:ansiblack bg:ansigray", title))

    def create_content(self, width, height):
        widths = self.widths()
        used_width = sum(widths)
        widths[-1] += width - used_width

        def get_line(y):
            if y == 0:
                u_width = sum(len(cell) for style, cell in self.lines[y])
                return [(style, cell) for style, cell in self.lines[y]] + \
                       [("fg:ansiblack bg:ansigray", " " * (width - u_width))]
            line = []
            for x, (style, cell) in enumerate(self.lines[y]):
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
