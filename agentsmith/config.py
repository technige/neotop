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


from datetime import datetime


class Config(object):

    def __init__(self, data):
        self.instances = {}
        for section in data:
            domain, _, attributes = section[u"name"].partition(u":")
            if not domain == u"org.neo4j":
                continue
            attributes = dict(parts.partition(u"=")[::2] for parts in attributes.split(u","))
            instance_name = attributes[u"instance"]
            self.instances.setdefault(instance_name, Instance(instance_name)).add(attributes[u"name"], section)


class Instance(object):

    def __init__(self, name):
        self.name = name
        self.sections = {}

    def add(self, section_name, section_data):
        section_key = section_name.lower()
        if section_key == "kernel":
            self.sections[section_key] = KernelSection(section_name, section_data)
        else:
            self.sections[section_key] = Section(section_name, section_data)

    def __getattr__(self, key):
        key = key.lower().replace("_", " ")
        return self.sections[key]


class Section(object):

    def __init__(self, name, data):
        self.name = name
        self.data = {}
        for key, value in data[u"attributes"].items():
            self.data[key] = value[u"value"]

    def __repr__(self):
        return "\n".join("{}: {}".format(key, value) for key, value in sorted(self.data.items()))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def keys(self):
        return self.data.keys()


class KernelSection(Section):

    def __init__(self, name, data):
        super(KernelSection, self).__init__(name, data)

    @property
    def start_time(self):
        return datetime.fromtimestamp(self.data[u"KernelStartTime"] / 1000)

    @property
    def uptime(self):
        uptime = (datetime.now() - self.start_time)
        days = uptime.days
        minutes, seconds = divmod(uptime.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if days > 0:
            return u"{days}d {hours}h".format(days=days, hours=hours)
        elif hours > 0:
            return u"{hours}h {minutes}m".format(hours=hours, minutes=minutes)
        else:
            return u"{minutes}m {seconds:.0f}s".format(minutes=minutes, seconds=seconds)

    @property
    def product_info(self):
        value = self.data[u"KernelVersion"]
        name, version, build = value.split(u",")
        version = tuple(map(int, version.partition(u":")[-1].strip().partition("-")[0].split(".")))
        return (name,) + version + (build,)


def main():
    """
    [u'org.neo4j:instance=kernel#0,name=Store file sizes',
     u'org.neo4j:instance=kernel#0,name=Kernel',
     u'org.neo4j:instance=kernel#0,name=Locking',
     u'org.neo4j:instance=kernel#0,name=Transactions',
     u'org.neo4j:instance=kernel#0,name=Configuration',
     u'org.neo4j:instance=kernel#0,name=Diagnostics',
     u'org.neo4j:instance=kernel#0,name=Page cache',
     u'org.neo4j:instance=kernel#0,name=BytesAmount Mapping',
     u'org.neo4j:instance=kernel#0,name=Store sizes',
     u'org.neo4j:instance=kernel#0,name=Index sampler',
     u'org.neo4j:instance=kernel#0,name=Primitive count']

    :return:
    """
    from neo4j.v1 import GraphDatabase
    with GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password")) as driver:
        with driver.session() as session:
            config = Config(session.run("CALL dbms.queryJmx('org.neo4j:*')").data())
            print(config.instances[u"kernel#0"].transactions)


if __name__ == "__main__":
    main()
