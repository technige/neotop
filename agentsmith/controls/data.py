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


from prompt_toolkit.layout import UIControl
from prompt_toolkit.utils import Event

from agentsmith.monitor import ServerMonitor


class DataControl(UIControl):

    def __init__(self, address, auth, prefer_routing=False, key_bindings=None):
        self.address = address
        self.monitor = ServerMonitor(address, auth, prefer_routing=prefer_routing, on_error=self.on_error)
        self.key_bindings = key_bindings
        self.invalidate = Event(self)

    def attach(self):
        self.monitor.attach(self.on_refresh)

    def detach(self):
        self.monitor.detach(self.on_refresh)

    @property
    def for_cluster_core(self):
        return self.monitor.for_cluster_core

    def exit(self):
        self.monitor.detach(self.on_refresh)
        self.monitor.exit()

    def on_refresh(self, data):
        pass

    def on_error(self, error):
        pass

    def create_content(self, width, height):
        pass

    def get_key_bindings(self):
        return self.key_bindings

    def get_invalidate_events(self):
        yield self.invalidate
