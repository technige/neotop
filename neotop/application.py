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
from threading import Thread
from time import sleep

from neo4j.v1 import urlparse
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, VSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style

from neotop.controls.overview import OverviewControl
from neotop.database import DatabaseInfo
from neotop.table import TableViewControl
from neotop.units import number_string, time_str


NEO4J_ADDRESS = getenv("NEO4J_ADDRESS", "localhost:7687")
NEO4J_AUTH = tuple(getenv("NEO4J_AUTH", "neo4j:password").partition(":")[::2])


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

style = Style.from_dict({
})


class Neotop(Application):

    def __init__(self):
        self.database = DatabaseInfo(NEO4J_ADDRESS, NEO4J_AUTH)
        self.panel = Panel(self, self.database)
        self.overview = OverviewControl(NEO4J_ADDRESS, NEO4J_AUTH, on_select=self.database.set_address)
        self.overview_window = Window(content=self.overview, width=0, dont_extend_width=False)
        self.separator_window = Window(width=0, dont_extend_width=True)
        self.panel_window = Window(content=self.panel.control)
        super(Neotop, self).__init__(
            layout=Layout(
                VSplit([
                    self.overview_window,
                    self.separator_window,
                    self.panel_window,
                ]),
            ),
            key_bindings=self.bindings(),
            style=style,
            # mouse_support=True,
            full_screen=True,
        )
        self.payload_key = "query"
        self.changed = False
        self.running = True
        self.loop_thread = Thread(target=self.loop)
        self.loop_thread.start()

    def loop(self):
        while self.running:
            self.update_info()
            self.update_content()
            self.changed = False
            self.sleep()

    def update_info(self):
        self.database.update()
        # self.overview.recalculate()

    def update_content(self):
        self.panel.update_content()
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
        bindings.add('f12')(self.toggle_overview)
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
        if self.overview_window.width == 0:
            self.overview_window.width = self.overview.max_width
        else:
            self.overview_window.width = 0
        self.separator_window.width = 1 if self.overview_window.width else 0
        self.changed = True

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
        self.overview.close()
        self.running = False
        get_app().exit(result=0)


# 'SINGLE' for stand-alone operation
# 'HA' for operating as a member in an HA cluster
# 'ARBITER' for a cluster member with no database in an HA cluster
# 'CORE' for operating as a core member of a Causal Cluster
# 'READ_REPLICA' for operating as a read replica member of a Causal Cluster.
mode_styles = {

    "SINGLE": "fg:ansiwhite bg:ansiblue",

    "CORE": "fg:ansiwhite bg:ansiblue",
    "READ_REPLICA": "fg:ansiwhite bg:ansiblue",

    "HA": "fg:ansiwhite bg:ansiblue",
    "ARBITER": "fg:ansiwhite bg:ansiblue",

}


class Panel(object):

    def __init__(self, application, database):
        self.application = application
        self.database = database
        self.title = []
        self.control = TableViewControl(self.title)

    def update_content(self):
        self.title[:] = []
        self.control.clear()
        if self.database.up:
            self.control.set_fields(DEFAULT_FIELDS)
            self.control.set_alignments(DEFAULT_ALIGNMENTS)
            k0 = self.database.config.instances[u"kernel#0"]
            title = ("{mode} {address}:{port} up {uptime}, "
                     "{major}.{minor}.{patch} "
                     "tx(b={begun} c={committed} r={rolled_back} hi={peak}) "
                     "store={store_size}").format(
                mode=k0.configuration[u"dbms.mode"][0],
                address=k0.configuration[u"dbms.connectors.default_advertised_address"],
                port=urlparse(self.database.uri).port,
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
            self.control.lines[1][-1] = ("", self.application.payload_key.upper())
            for q in sorted(self.database.queries, key=lambda q0: q0["elapsedTimeMillis"], reverse=True):
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
                self.control.append([
                    ("", q["queryId"]),
                    ("fg:ansibrightblack" if q["username"] == "neo4j" else "", q["username"]),
                    ("", client),
                    ("", number_string(q["allocatedBytes"], K=1024)),
                    ("", number_string(q["activeLockCount"])),
                    ("", number_string(q["pageHits"])),
                    ("", number_string(q["pageFaults"])),
                    ("", time_str(q["elapsedTimeMillis"])),
                    ("", time_str(q["cpuTimeMillis"])),
                    ("", time_str(q["waitTimeMillis"])),
                    ("", time_str(q["idleTimeMillis"])),
                    (payload_style, q[self.application.payload_key]),
                ])
            self.control.set_title_style(mode_styles[k0.configuration[u"dbms.mode"]])
        else:
            self.control.set_fields([])
            self.control.set_alignments([])
            title = "{} down".format(urlparse(self.database.uri).netloc)
            self.control.set_title_style("fg:ansiwhite bg:ansired")
        self.title.append(("", title))
