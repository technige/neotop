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

from neotop.monitor import ServerMonitor


class DataControl(UIControl):

    def __init__(self, address, auth):
        self.address = address
        self.monitor = ServerMonitor(address, auth, on_error=self.on_error)
        self.monitor.attach(self.on_refresh)
        self.invalidate = Event(self)

    def exit(self):
        self.monitor.detach(self.on_refresh)

    def on_refresh(self, data):
        pass

    def on_error(self, error):
        pass

    def create_content(self, width, height):
        pass

    def get_invalidate_events(self):
        yield self.invalidate
