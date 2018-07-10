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


from neo4j.v1 import GraphDatabase, CypherError, ServiceUnavailable, READ_ACCESS, urlparse

from neotop.config import Config


def get_info(tx, db):
    config_result = tx.run("CALL dbms.queryJmx('org.neo4j:*')")
    queries_result = tx.run("CALL dbms.listQueries")
    if db.is_cluster is not False:
        overview_result = tx.run("CALL dbms.cluster.overview")
    db.config = Config(config_result.data())
    db.queries = queries_result.data()
    if db.is_cluster is not False:
        try:
            db.overview = overview_result.data()
        except CypherError as error:
            if error.code == u"Neo.ClientError.Procedure.ProcedureNotFound":
                db.is_cluster = False
            else:
                raise
        else:
            db.is_cluster = True


class DatabaseInfo(object):

    def __init__(self, address, auth):
        self.address = address
        self.auth = auth
        self.driver = None
        self.config = None
        self.queries = None
        self.overview = []
        self.last_error = None
        self.is_cluster = None

    @property
    def uri(self):
        return "bolt://{}".format(self.address)

    def set_address(self, address):
        self.address = address
        self.driver = None

    def has_servers(self, role):
        for server in self.overview:
            if server[u"role"] == role:
                return True
        return False

    def get_servers(self, role):
        return [urlparse(server[u"addresses"][0]).netloc for server in self.overview if server[u"role"] == role]

    @property
    def up(self):
        return bool(self.driver)

    def get_driver(self):
        if not self.driver:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=self.auth, max_retry_time=1.0)
            except (CypherError, ServiceUnavailable) as error:
                self.driver = None
                self.last_error = error
        return self.driver

    def update(self):
        driver = self.get_driver()
        if driver is None:
            return False
        try:
            with driver.session(READ_ACCESS) as session:
                session.read_transaction(get_info, self)
        except CypherError as error:
            if error.code != u"Neo.ClientError.Transaction.TransactionMarkedAsFailed":
                self.driver = None
                self.last_error = error
                return False
        except ServiceUnavailable as error:
            self.driver = None
            self.last_error = error
            return False
