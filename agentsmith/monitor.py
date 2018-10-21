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


from __future__ import division

from collections import deque
from datetime import datetime
from threading import Thread, Lock

from neo4j.v1 import GraphDatabase, CypherError, ServiceUnavailable, READ_ACCESS, sleep, SessionExpired, urlparse

from agentsmith.units import Load, BytesAmount, Time, Product, Amount


def nested_get(d, *keys):
    if keys:
        try:
            return nested_get(d[keys[0]], *keys[1:])
        except (KeyError, TypeError):
            return None
    else:
        return d


class SystemData(object):

    os = None
    jvm = None
    dbms = None

    _editions = {
        u"community": u"CE",
        u"enterprise": u"EE",
    }

    def __init__(self, os, java_runtime, java_threading, dbms_components, dbms_kernel, dbms_config):
        if os:
            self.os = Product(os[u"Name"], os[u"Version"], arch=os[u"Arch"])
            self.available_processors = Amount(os[u"AvailableProcessors"])
            self.process_cpu_time = Time(ns=os[u"ProcessCpuTime"])
            self.process_cpu_load = Load(os[u"ProcessCpuLoad"])
            self.system_cpu_load = Load(os[u"SystemCpuLoad"])
            self.system_load_average = Load(os[u"SystemLoadAverage"])
        if java_runtime:
            self.jvm = Product(java_runtime[u"VmName"], java_runtime[u"SpecVersion"],
                               uptime=Time(ms=java_runtime[u"Uptime"]))
        if java_threading:
            self.daemon_thread_count = Amount(java_threading[u"DaemonThreadCount"])
            self.peak_thread_count = Amount(java_threading[u"PeakThreadCount"])
            self.thread_count = Amount(java_threading[u"ThreadCount"])
            self.total_started_thread_count = Amount(java_threading[u"TotalStartedThreadCount"])
        if dbms_components:
            t0 = dbms_kernel[u"KernelStartTime"]
            t1 = 1000 * datetime.now().timestamp()
            dbms_component = dbms_components[0]
            dbms_component_name = dbms_component[u"name"]
            if dbms_component_name == "Neo4j Kernel":
                dbms_component_name = "Neo4j"
            self.dbms = Product(dbms_component_name,
                                dbms_component[u"versions"][0],
                                edition=self._editions[dbms_component[u"edition"]],
                                mode=dbms_config.get(u"dbms.mode", u"SINGLE"),
                                uptime=(Time(ms=(t1 - t0))))

    def __repr__(self):
        s = ["System:"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "<" + "\n".join(s) + ">"

    def __str__(self):
        return self.status_text()

    def status_text(self):
        return ("{major}.{minor} {dbms_edition} up {dbms_uptime}".format(
                    major=self.dbms.version.major,
                    minor=self.dbms.version.minor,
                    dbms_edition=self.dbms.edition,
                    dbms_uptime=self.dbms.uptime))

    def cpu_meter(self, size):
        process_load = int(round(size * self.process_cpu_load.value))
        system_load = int(round(size * self.system_cpu_load.value))
        return "CPU [{}]".format((":" * process_load).ljust(system_load, ".").ljust(size))


class MemoryData(object):

    def __init__(self, os, java_memory):
        """
        TotalPhysicalMemorySize: 33588854784
        FreePhysicalMemorySize: 22521024512
        TotalSwapSpaceSize: 34221322240
        FreeSwapSpaceSize: 34221322240
        CommittedVirtualMemorySize: 14924046336
        """
        self.total_physical_memory_size = BytesAmount(os[u"TotalPhysicalMemorySize"])
        self.free_physical_memory_size = BytesAmount(os[u"FreePhysicalMemorySize"])
        self.total_swap_space_size = BytesAmount(os[u"TotalSwapSpaceSize"])
        self.free_swap_space_size = BytesAmount(os[u"FreeSwapSpaceSize"])
        self.committed_virtual_memory_size = BytesAmount(os[u"CommittedVirtualMemorySize"])
        self.committed_heap_memory_size = BytesAmount(nested_get(java_memory, u"HeapMemoryUsage", u"properties", u"committed"))
        self.initial_heap_memory_size = BytesAmount(nested_get(java_memory, u"HeapMemoryUsage", u"properties", u"init"))
        self.max_heap_memory_size = BytesAmount(nested_get(java_memory, u"HeapMemoryUsage", u"properties", u"max"))
        self.used_heap_memory_size = BytesAmount(nested_get(java_memory, u"HeapMemoryUsage", u"properties", u"used"))
        self.committed_non_heap_memory_size = BytesAmount(nested_get(java_memory, u"NonHeapMemoryUsage", u"properties", u"committed"))
        self.initial_non_heap_memory_size = BytesAmount(nested_get(java_memory, u"NonHeapMemoryUsage", u"properties", u"init"))
        self.max_non_heap_memory_size = BytesAmount(nested_get(java_memory, u"NonHeapMemoryUsage", u"properties", u"max"))
        self.used_non_heap_memory_size = BytesAmount(nested_get(java_memory, u"NonHeapMemoryUsage", u"properties", u"used"))

    def __repr__(self):
        s = ["Memory:"]
        for attr in sorted(dir(self)):
            if attr.endswith("size"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)

    def heap_meter(self, size):
        unit = self.committed_heap_memory_size.value / size
        bytes_used = self.used_heap_memory_size.value
        # bytes_committed = self.committed_heap_memory_size.value
        units_used = int(round(bytes_used / unit))
        # units_committed = int(round(bytes_committed / unit))
        return "{} heap [{}]".format(self.committed_heap_memory_size, (":" * units_used).ljust(size))


class StorageData(object):

    def __init__(self, os, dbms_kernel, dbms_stores, dbms_primitives):
        """
        MaxFileDescriptorCount: 40000
        OpenFileDescriptorCount: 515
        """
        self.max_file_descriptor_count = Amount(os[u"MaxFileDescriptorCount"])
        self.open_file_descriptor_count = Amount(os[u"OpenFileDescriptorCount"])
        self.database_name = dbms_kernel[u"DatabaseName"]
        self.read_only = dbms_kernel[u"ReadOnly"]
        self.store_creation_date = dbms_kernel[u"StoreCreationDate"]    # TODO
        self.store_id = dbms_kernel[u"StoreId"]
        self.array_store_size = BytesAmount(dbms_stores[u"ArrayStoreSize"])
        self.count_store_size = BytesAmount(dbms_stores[u"CountStoreSize"])
        self.index_store_size = BytesAmount(dbms_stores[u"IndexStoreSize"])
        self.label_store_size = BytesAmount(dbms_stores[u"LabelStoreSize"])
        self.node_store_size = BytesAmount(dbms_stores[u"NodeStoreSize"])
        self.property_store_size = BytesAmount(dbms_stores[u"PropertyStoreSize"])
        self.relationship_store_size = BytesAmount(dbms_stores[u"RelationshipStoreSize"])
        self.schema_store_size = BytesAmount(dbms_stores[u"SchemaStoreSize"])
        self.string_store_size = BytesAmount(dbms_stores[u"StringStoreSize"])
        self.total_store_size = BytesAmount(dbms_stores[u"TotalStoreSize"])
        self.transaction_logs_size = BytesAmount(dbms_stores[u"TransactionLogsSize"])
        self.node_id_count = Amount(dbms_primitives[u"NumberOfNodeIdsInUse"])
        self.property_id_count = Amount(dbms_primitives[u"NumberOfPropertyIdsInUse"])
        self.relationship_id_count = Amount(dbms_primitives[u"NumberOfRelationshipIdsInUse"])
        self.relationship_type_id_count = Amount(dbms_primitives[u"NumberOfRelationshipTypeIdsInUse"])

    def __repr__(self):
        s = ["Storage:"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)


class QueryListData(object):

    def __init__(self, queries):
        self.__items = list(map(QueryData, queries))

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, item):
        return self.__items[item]

    def __iter__(self):
        return iter(self.__items)

    def __repr__(self):
        s = ["Queries:", "    list: [...]"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)


class QueryData(object):

    def __init__(self, query):
        """
        'activeLockCount': 0,
        'allocatedBytes': None,
        'clientAddress': '127.0.0.1:46718',
        'cpuTimeMillis': None,
        'elapsedTimeMillis': 0,
        'idleTimeMillis': None,
        'indexes': [],
        'metaData': {},
        'pageFaults': 0,
        'pageHits': 0,
        'parameters': {},
        'planner': 'idp',
        'protocol': 'bolt',
        'query': 'CALL dbms.listQueries',
        'queryId': 'query-64',
        'requestUri': '127.0.0.1:7687',
        'resourceInformation': {},
        'runtime': 'procedure',
        'startTime': '2018-07-13T14:06:55.851Z',
        'status': 'running',
        'username': 'neo4j',
        'waitTimeMillis': 0,

        :param query:
        """
        self.active_lock_count = Amount(query[u"activeLockCount"])
        self.allocated_bytes = BytesAmount(query[u"allocatedBytes"])
        self.client_address = query[u"clientAddress"]
        self.cpu_time = Time(ms=query[u"cpuTimeMillis"])
        self.elapsed_time = Time(ms=query[u"elapsedTimeMillis"])
        self.idle_time = Time(ms=query[u"idleTimeMillis"])
        self.wait_time = Time(ms=query[u"waitTimeMillis"])
        self.indexes = query[u"indexes"]
        self.metadata = query[u"metaData"]
        self.page_faults = Amount(query[u"pageFaults"])
        self.page_hits = Amount(query[u"pageHits"])
        self.parameters = query[u"parameters"]
        self.planner = query[u"planner"]
        self.protocol = query[u"protocol"]
        self.text = query[u"query"]
        self.request_uri = query[u"requestUri"]
        self.resource_information = query[u"resourceInformation"]
        self.runtime = query[u"runtime"]
        self.start_time = query[u"startTime"]  # TODO: unit
        self.status = query[u"status"]
        self.user = query[u"username"]
        self.id = int(query[u"queryId"].partition("-")[-1])

    def __repr__(self):
        s = ["Query:"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)


class TransactionListData(object):

    def __init__(self, transactions, metadata):
        """
        {'LastCommittedTxId': 1,
         'NumberOfCommittedTransactions': 1312,
         'NumberOfOpenTransactions': 1,
         'NumberOfOpenedTransactions': 1321,
         'NumberOfRolledBackTransactions': 8,
         'PeakNumberOfConcurrentTransactions': 2}

        :param transactions:
        :param metadata:
        """
        if transactions is None:
            self.__items = []
        else:
            self.__items = list(map(TransactionData, transactions))
        self.last_committed_id = metadata[u"LastCommittedTxId"]
        self.begin_count = Amount(metadata[u"NumberOfOpenedTransactions"])
        self.open_count = Amount(metadata[u"NumberOfOpenTransactions"])
        self.commit_count = Amount(metadata[u"NumberOfCommittedTransactions"])
        self.rollback_count = Amount(metadata[u"NumberOfRolledBackTransactions"])
        self.peak_concurrent = Amount(metadata[u"PeakNumberOfConcurrentTransactions"])

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, item):
        return self.__items[item]

    def __iter__(self):
        return iter(self.__items)

    def __repr__(self):
        s = ["Transactions:", "    list: [...]"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)


class TransactionData(object):

    def __init__(self, transaction):
        """
        {'transactionId': 'transaction-96',
         'username': 'neo4j',
         'metaData': {},
         'startTime': '2018-10-18T11:04:17.938Z',
         'protocol': 'bolt',
         'clientAddress': '127.0.0.1:41758',
         'requestUri': '127.0.0.1:17100',
         'currentQueryId': 'query-127',
         'currentQuery': 'CALL dbms.listTransactions',
         'activeLockCount': 0,
         'status': 'Running',
         'resourceInformation': {},
         'elapsedTimeMillis': 2,
         'cpuTimeMillis': 0,
         'waitTimeMillis': 0,
         'idleTimeMillis': 2,
         'allocatedBytes': 0,
         'allocatedDirectBytes': 0,
         'pageHits': 0,
         'pageFaults': 0}
        """
        self.id = int(transaction[u"transactionId"].partition("-")[-1])
        self.user = transaction[u"username"]
        self.metadata = transaction[u"metaData"]
        self.start_time = transaction[u"startTime"]  # TODO: unit
        self.protocol = transaction[u"protocol"]
        self.client_address = transaction[u"clientAddress"]
        self.request_uri = transaction[u"requestUri"]
        self.current_query_id_string = transaction[u"currentQueryId"]
        if self.current_query_id_string:
            self.current_query_id = int(self.current_query_id_string.partition("-")[-1])
        else:
            self.current_query_id = None
        self.current_query = transaction[u"currentQuery"]
        self.active_lock_count = Amount(transaction[u"activeLockCount"])
        self.status = transaction[u"status"]
        self.resource_information = transaction[u"resourceInformation"]
        self.elapsed_time = Time(ms=transaction[u"elapsedTimeMillis"])
        self.cpu_time = Time(ms=transaction[u"cpuTimeMillis"])
        self.wait_time = Time(ms=transaction[u"waitTimeMillis"])
        self.idle_time = Time(ms=transaction[u"idleTimeMillis"])
        self.allocated_bytes = BytesAmount(transaction[u"allocatedBytes"])
        self.allocated_direct_bytes = BytesAmount(transaction[u"allocatedDirectBytes"])
        self.page_hits = Amount(transaction[u"pageHits"])
        self.page_faults = Amount(transaction[u"pageFaults"])

    def __repr__(self):
        s = ["Transaction:"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)


class PageCacheData(object):

    def __init__(self, page_cache):
        """
        {'BytesRead': 147542,
         'BytesWritten': 8192,
         'EvictionExceptions': 0,
         'Evictions': 0,
         'Faults': 19,
         'FileMappings': 36,
         'FileUnmappings': 19,
         'Flushes': 1,
         'HitRatio': 0.5777777777777777,
         'Hits': 26,
         'Pins': 71,
         'Unpins': 44,
         'UsageRatio': 1.2406315990174198e-05}
        """
        self.bytes_read = BytesAmount(page_cache[u"BytesRead"])
        self.bytes_written = BytesAmount(page_cache[u"BytesWritten"])
        self.eviction_exceptions = Amount(page_cache[u"EvictionExceptions"])
        self.evictions = Amount(page_cache[u"Evictions"])
        self.faults = Amount(page_cache[u"Faults"])
        self.file_mappings = Amount(page_cache[u"FileMappings"])
        self.file_unmappings = Amount(page_cache[u"FileUnmappings"])
        self.flushes = Amount(page_cache[u"Flushes"])
        self.hit_ratio = page_cache[u"HitRatio"]
        self.hits = Amount(page_cache.get(u"Hits"))
        self.pins = Amount(page_cache[u"Pins"])
        self.unpins = Amount(page_cache.get(u"Unpins"))
        self.usage_ratio = page_cache.get(u"UsageRatio")

    def __repr__(self):
        s = ["Page Cache:"]
        for attr in sorted(dir(self)):
            if not attr.startswith("_"):
                s.append("    %s: %r" % (attr, getattr(self, attr)))
        return "\n".join(s)


class ClusterOverviewData(object):

    def __init__(self, data):
        self.data = data

        def first_address(server):
            return urlparse(server[u"addresses"][0]).netloc

        leaders = [("Leader", first_address(server))
                   for server in data if server[u"role"] == u"LEADER"]
        followers = [("Followers", first_address(server))
                     for server in data if server[u"role"] == u"FOLLOWER"]
        read_replicas = [("Read replicas", first_address(server))
                         for server in data if server[u"role"] == u"READ_REPLICA"]
        self.servers = leaders + followers + read_replicas


class ServerData(object):

    # System and common DBMS data
    system = None
    process = None
    memory = None
    storage = None

    # Enterprise data
    queries = None
    page_cache = None
    transactions = None
    # TODO: locking = None
    # TODO: memory_mapping = None

    # Causal cluster data
    cluster_membership = None
    cluster_overview = None

    @property
    def enterprise(self):
        return self.system.dbms.edition == u"EE"

    @property
    def cluster(self):
        return self.system.dbms.mode == u"CORE"


class ServerMonitor(object):

    __lock = Lock()
    __instances = {}

    _address = None
    _routing = None
    _uri = None
    _auth = None
    _running = None
    _refresh_period = None
    _refresh_thread = None
    _on_refresh = None
    _on_error = None
    _lock = None
    _data = None

    @classmethod
    def dbms_mode(cls, address, auth):
        uri = "bolt://{}".format(address)
        with GraphDatabase.driver(uri, auth=auth) as driver:
            with driver.session(READ_ACCESS) as session:
                return session.run("CALL dbms.listConfig('dbms.mode') YIELD value").value()[0]

    @classmethod
    def is_cluster_core(cls, address, auth):
        return cls.dbms_mode(address, auth) == u"CORE"

    def __new__(cls, address, auth, prefer_routing=False, on_error=None):
        with cls.__lock:
            is_cluster_core = prefer_routing and cls.is_cluster_core(address, auth)
            scheme = "bolt+routing" if is_cluster_core else "bolt"
            uri = "{}://{}".format(scheme, address)
            if uri not in cls.__instances:
                inst = cls.__instances[uri] = object.__new__(cls)
                inst._address = address
                inst._for_cluster_core = is_cluster_core
                inst._uri = uri
                inst._auth = auth
                inst._driver = None
                inst._death_row = deque()
                inst._running = True
                inst._refresh_period = 1.0
                inst._refresh_thread = Thread(target=inst.loop)
                inst._refresh_thread.start()
                inst._handlers = set()
                inst._on_error = on_error
                inst._lock = Lock()
                inst._data = None
            return cls.__instances[uri]

    def attach(self, handler):
        with self._lock:
            self._handlers.add(handler)

    def detach(self, handler):
        with self._lock:
            self._handlers.discard(handler)

    def kill(self, tx):
        self._death_row.append(tx)

    def exit(self):
        with self._lock:
            if self._running:
                self._running = False
                self._refresh_thread.join()
                del self.__instances[self.uri]

    def loop(self):
        with GraphDatabase.driver(self._uri, auth=self._auth, max_retry_time=1.0) as driver:

            def kill():
                with driver.session() as s:
                    with s.begin_transaction() as t:
                        while self._death_row:
                            tx_to_kill = self._death_row.pop()
                            qid_to_kill = tx_to_kill.current_query_id_string
                            if qid_to_kill:
                                t.run("CALL dbms.killQuery($qid)", qid=qid_to_kill).consume()

            while self._running:
                try:
                    if self._handlers:
                        with driver.session() as session:
                            with session.begin_transaction() as tx:
                                while self._handlers:
                                    if self._death_row:
                                        kill()
                                    self.work(tx, self.fetch_data)
                                    for handler in self._handlers:
                                        if callable(handler):
                                            handler(self._data)
                                    for _ in range(int(10 * self._refresh_period)):
                                        if self._handlers and self._running:
                                            sleep(0.1)
                                        else:
                                            break
                    else:
                        for _ in range(int(10 * self._refresh_period)):
                            if self._running:
                                sleep(0.1)
                            else:
                                break
                except KeyboardInterrupt:
                    self._running = False

    def work(self, tx, unit):
        try:
            # if not self._driver:
            #     self._driver = GraphDatabase.driver(self._uri, auth=self._auth, max_retry_time=1.0)
            return unit(tx)
        except (CypherError, ServiceUnavailable, SessionExpired) as error:
            # self._driver = None
            self._data = None
            if callable(self._on_error):
                self._on_error(error)
            else:
                raise

    @classmethod
    def _extract_jmx(cls, jmx, section_name):
        sections = [section for section in jmx if section[u"name"] == section_name]
        return {key: value[u"value"] for key, value in sections[0][u"attributes"].items()} if sections else None

    def fetch_data(self, tx):
        """ Retrieve data from database.

        :return:
        """
        data = ServerData()

        jmx = tx.run("CALL dbms.queryJmx('*:*')").data()
        os = self._extract_jmx(jmx, u"java.lang:type=OperatingSystem")
        dbms_config = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Configuration")

        components = tx.run("CALL dbms.components").data()
        jvm = self._extract_jmx(jmx, u"java.lang:type=Runtime")
        java_threading = self._extract_jmx(jmx, u"java.lang:type=Threading")
        dbms_kernel = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Kernel")
        data.system = SystemData(os, jvm, java_threading, components, dbms_kernel, dbms_config)

        java_memory = self._extract_jmx(jmx, u"java.lang:type=Memory")
        data.memory = MemoryData(os, java_memory)

        dbms_stores = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Store sizes")
        dbms_primitives = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Primitive count")
        data.storage = StorageData(os, dbms_kernel, dbms_stores, dbms_primitives)

        if data.system.dbms.edition == u"EE":

            data.queries = QueryListData(
                tx.run("CALL dbms.listQueries").data())

            # # TODO: detect dbms.listTransactions (only available in 3.4+)
            try:
                transactions = tx.run("CALL dbms.listTransactions").data()
            except CypherError as error:
                if error.code.endswith("ProcedureNotFound"):
                    transactions = None
                else:
                    raise
            data.transactions = TransactionListData(
                transactions,
                self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Transactions"))

            data.page_cache = PageCacheData(
                self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Page cache"))

            # TODO: data.locking = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Locking")

            # TODO: data.memory_mapping = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Memory Mapping")

            if data.system.dbms.mode == u"CORE":
                data.cluster_membership = self._extract_jmx(jmx, u"org.neo4j:instance=kernel#0,name=Causal Clustering")
                data.cluster_overview = ClusterOverviewData(tx.run("CALL dbms.cluster.overview").data())

        else:

            data.queries = None

        self._data = data

    @property
    def for_cluster_core(self):
        return self._for_cluster_core

    @property
    def uri(self):
        return self._uri

    @property
    def address(self):
        return self._address

    @property
    def up(self):
        return bool(self._driver)


def print_stats(data):
    if data:
        print("up: True")
        print(data.system)    # 1
        print(data.memory)    # 3
        print(data.storage)   # 4
        if data.enterprise:
            print(data.queries)       # 5
            print(data.transactions)  # 6
            print(data.page_cache)
            if data.cluster:
                print("Cluster Overview: {}".format(data.cluster_overview))
    else:
        print("up: False")
    print()


def main():
    server = ServerMonitor("localhost:17100", auth=("neo4j", "password"))
    try:
        server.attach(print_stats)
        sleep(300)
    finally:
        server.detach(print_stats)


if __name__ == "__main__":
    main()
