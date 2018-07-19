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


class Load(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        return "%3.1f%%" % (100.0 * self.value)


class Amount(object):

    K = 1000
    M = K ** 2
    G = K ** 3
    T = K ** 4

    def __init__(self, value):
        self.value = value

    def __int__(self):
        return int(self.value)

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        if self.value is None:
            return "~"
        if self.value == 0:
            return "0"
        elif self.value < self.K:
            return "%d" % self.value
        elif self.value < self.M:
            return "%.3g" % (self.value / self.K) + "K"
        elif self.value < self.G:
            return "%.3g" % (self.value / self.M) + "M"
        elif self.value < T:
            return "%.3g" % (self.value / self.G) + "G"
        else:
            return "%.3g" % (self.value / self.T) + "T"

    def text(self):
        s = self.__str__()
        return "", s


class BytesAmount(object):

    K = 1024
    M = K ** 2
    G = K ** 3
    T = K ** 4

    def __init__(self, value):
        self.value = value

    def __int__(self):
        return int(self.value)

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        if self.value is None or self.value < 0:
            return "~"
        if self.value == 0:
            return "0"
        elif self.value < self.K:
            return "%d" % self.value
        elif self.value < self.M:
            return "%.3g" % (self.value / self.K) + "K"
        elif self.value < self.G:
            return "%.3g" % (self.value / self.M) + "M"
        elif self.value < self.T:
            return "%.3g" % (self.value / self.G) + "G"
        else:
            return "%.3g" % (self.value / self.T) + "T"


class Product(object):

    def __init__(self, name, version, **metadata):
        self.name = name
        self.version = Version(version)
        self.metadata = metadata

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        s = "%s/%s" % (self.name, self.version)
        if self.metadata:
            s += " (%s)" % ", ".join("%s=%r" % (key, value) for key, value in self.metadata.items())
        return s

    def __getattr__(self, name):
        try:
            return self.metadata[name]
        except KeyError:
            raise AttributeError(name)


class Time(object):

    def __init__(self, ns=None, ms=None):
        if ns is None and ms is None:
            self.ns = None
        elif ms is None:
            self.ns = ns
        elif ns is None:
            self.ns = ms * 1000000
        else:
            self.ns = ns + ms * 1000000

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        if self.ns is None:
            return "~"
        n_millis = self.ns // 1000000
        if n_millis == 0:
            return "0"
        if n_millis < 1000:
            # Less than 1s, display as 0.23s
            n_secs = (n_millis / 1000)
            s = "%0.02fs" % n_secs
            if s == "0.00s":
                s = "ε"
            return s
        if n_millis < 60000:
            # Less than 60s, display as 12s
            n_secs = (n_millis / 1000)
            return "%ds" % n_secs
        n_secs = (n_millis // 1000)
        n_mins, n_secs = divmod(n_secs, 60)
        if n_mins < 60:
            # Less than 60 mins, display as 1m02
            return "%dm%02d" % (n_mins, n_secs)
        n_hours, n_mins = divmod(n_mins, 60)
        # Display as 1h02
        return "%dh%02d" % (n_hours, n_mins)

    def __lt__(self, other):
        return self.ns < other.ns


class Version(object):

    version = ()
    tags = ()

    def __init__(self, data):
        version, _, tags = data.partition("-")
        self.version = tuple(map(int, version.split(".")))
        if tags:
            self.tags = tuple(tags.split("-"))

    def __repr__(self):
        return "<%s>" % self.__str__()

    def __str__(self):
        r = ".".join(map(str, self.version))
        if self.tags:
            r += "-" + "-".join(self.tags)
        return r

    @property
    def major(self):
        return self.version[0]

    @property
    def minor(self):
        return self.version[1]
