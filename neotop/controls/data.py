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

from neo4j.v1 import GraphDatabase, ServiceUnavailable, READ_ACCESS
from prompt_toolkit.layout import UIControl


class DataControl(UIControl):

    def __init__(self, address, auth):
        self._address = address
        self._uri = "bolt://{}".format(self.address)
        self._auth = auth
        self._driver = None
        self._error = None
        self._running = True
        self._invalidated = False
        self._refresh_period = 1.0
        self._refresh_thread = Thread(target=self.loop)
        self._refresh_thread.start()

    @property
    def address(self):
        return self._address

    def loop(self):
        while self._running:
            try:
                if not self._driver:
                    self._driver = GraphDatabase.driver(self._uri, auth=self._auth)
                with self._driver.session(READ_ACCESS) as session:
                    session.read_transaction(self.fetch_data)
            except ServiceUnavailable as error:
                self._driver = None
                self._error = error
            else:
                self._error = None
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

    def fetch_data(self, tx):
        """ Retrieve data from database.

        :return:
        """

    def create_content(self, width, height):
        """ Generate content.

        :param width:
        :param height:
        :return:
        """
