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


from threading import Thread
from time import sleep

from neo4j.v1 import GraphDatabase, CypherError, ServiceUnavailable, READ_ACCESS
from prompt_toolkit.layout import UIControl
from prompt_toolkit.utils import Event


class DataControl(UIControl):

    def __init__(self, address, auth):
        self._address = address
        self._uri = "bolt://{}".format(self.address)
        self._auth = auth
        self._driver = None
        self._running = True
        self._invalidated = False
        self._refresh_period = 1.0
        self._refresh_thread = Thread(target=self.loop)
        self._on_fresh_data = Event(self)
        self._refresh_thread.start()

    @property
    def address(self):
        return self._address

    @property
    def up(self):
        return bool(self._driver)

    def work(self, unit, on_error):
        try:
            if not self._driver:
                self._driver = GraphDatabase.driver(self._uri, auth=self._auth, max_retry_time=1.0)
            with self._driver.session(READ_ACCESS) as session:
                session.read_transaction(unit)
        except (CypherError, ServiceUnavailable) as error:
            self._driver = None
            on_error(error)

    def loop(self):
        while self._running:
            self.work(self.fetch_data, self.on_fetch_error)
            self._on_fresh_data.fire()
            self._invalidated = False
            for _ in range(int(10 * self._refresh_period)):
                if self._running and not self._invalidated:
                    sleep(0.1)
                else:
                    break

    def invalidate(self):
        self._invalidated = True

    def exit(self):
        self._running = False
        self._refresh_thread.join()
        if self._driver:
            self._driver.close()

    def get_invalidate_events(self):
        """
        Return the Window invalidate events.
        """
        yield self._on_fresh_data

    def fetch_data(self, tx):
        """ Retrieve data from database.

        :return:
        """

    def on_fetch_error(self, error):
        """ Raised if an error occurs while fetching data.

        :param error:
        :return:
        """

    def create_content(self, width, height):
        """ Generate content.

        :param width:
        :param height:
        :return:
        """
