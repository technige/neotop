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

from threading import Thread
from time import sleep

from neo4j.v1 import GraphDatabase, READ_ACCESS
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from neotop.table import TableControl
from neotop.units import number_string, time_str


top_control = FormattedTextControl(text="")
query_list_control = TableControl([
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
    ("", "Query"),
], alignments=[
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
])
query_list_control.line_styles[0] = "fg:ansiwhite bg:ansibrightblack"


style = Style.from_dict({
})


class Neotop(Application):

    def __init__(self):
        super(Neotop, self).__init__(
            layout=Layout(
                HSplit([
                    # Window(content=top_control, dont_extend_height=True),
                    Window(content=query_list_control, height=10),
                ]),
            ),
            key_bindings=self.bindings(),
            style=style,
            # mouse_support=True,
            full_screen=True,
        )
        self.driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        self.queries = []
        self.payload_key = "query"
        self.changed = False
        self.running = True
        self.loop_thread = Thread(target=self.loop)
        self.loop_thread.start()

    def loop(self):
        while self.running:
            self.update()
            self.update_query_list()
            self.changed = False
            self.sleep()

    def update(self):
        with self.driver.session(READ_ACCESS) as session:
            self.queries = session.run("CALL dbms.listQueries").data()

    def update_query_list(self):
        query_list_control.clear()
        query_list_control.lines[0][-1] = ("", self.payload_key.upper())
        for q in sorted(self.queries, key=lambda q0: q0["queryId"]):
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
            query_list_control.append([
                ("", q["queryId"]),
                ("fg:ansibrightblack" if q["username"] == "neo4j" else "", q["username"]),
                ("", client),
                ("", number_string(q["allocatedBytes"], scale=1024)),
                ("", number_string(q["activeLockCount"])),
                ("", number_string(q["pageHits"])),
                ("", number_string(q["pageFaults"])),
                ("", time_str(q["elapsedTimeMillis"])),
                ("", time_str(q["cpuTimeMillis"])),
                ("", time_str(q["waitTimeMillis"])),
                ("", time_str(q["idleTimeMillis"])),
                (payload_style, q[self.payload_key]),
            ])
        self.invalidate()

    def sleep(self):
        for _ in range(10):
            if self.running and not self.changed:
                sleep(0.1)
            else:
                return

    def bindings(self):
        bindings = KeyBindings()
        bindings.add('c-c')(self.do_exit)
        bindings.add('i')(self.set_indexes_payload)
        bindings.add('m')(self.set_metadata_payload)
        bindings.add('p')(self.set_parameters_payload)
        bindings.add('q')(self.set_query_payload)
        return bindings

    def set_query_payload(self, _):
        self.payload_key = "query"
        self.changed = True

    def set_parameters_payload(self, _):
        self.payload_key = "parameters"
        self.changed = True

    def set_metadata_payload(self, _):
        self.payload_key = "metaData"
        self.changed = True

    def set_indexes_payload(self, _):
        self.payload_key = "indexes"
        self.changed = True

    def do_exit(self, _):
        self.running = False
        get_app().exit(result=0)


application = Neotop()
