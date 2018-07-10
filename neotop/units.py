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


def trim(n):
    return n.rstrip("0").rstrip(".")


def number_string(n, K=1000):
    M = K ** 2
    G = K ** 3
    T = K ** 4
    if n == 0:
        return "0"
    elif n < K:
        return "%d" % n
    elif n < M:
        return "%.3g" % (n / K) + "K"
    elif n < G:
        return "%.3g" % (n / M) + "M"
    elif n < T:
        return "%.3g" % (n / G) + "G"
    else:
        return "%.3g" % (n / T) + "T"


def time_str(n_millis):
    if n_millis == 0:
        return "0"
    if n_millis < 10000:
        # Less than 10s, display as 1.234
        n_secs = (n_millis / 1000)
        return "%0.03f" % n_secs
    if n_millis < 60000:
        # Less than 60s, display as 12.34
        n_secs = (n_millis / 1000)
        return "%0.02f" % n_secs
    n_secs = (n_millis // 1000)
    n_mins, n_secs = divmod(n_secs, 60)
    if n_mins < 60:
        # Less than 60 mins, display as 1m02
        return "%dm%02d" % (n_mins, n_secs)
    n_hours, n_mins = divmod(n_mins, 60)
    # Display as 1h02
    return "%dh%02d" % (n_hours, n_mins)
