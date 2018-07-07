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


from prompt_toolkit.layout import UIControl, UIContent


class TableControl(UIControl):

    def __init__(self, columns, alignments):
        self.lines = [columns]
        self.line_styles = {}
        self.alignments = list(alignments)

    def clear(self):
        self.lines[1:] = []

    def append(self, values):
        self.lines.append([(style, str(value)) for style, value in values])

    def widths(self):
        widths = list(map(len, self.lines[0]))
        for row in self.lines:
            for i, (_, cell) in enumerate(row):
                size = len(cell)
                if size > widths[i]:
                    widths[i] = size
        return widths

    def create_content(self, width, height):
        widths = self.widths()
        used_width = sum(widths)
        widths[-1] += width - used_width

        def get_line(y):
            line = []
            for i, (style, cell) in enumerate(self.lines[y]):
                if i > 0:
                    line.append((self.line_styles.get(y, ""), " "))
                alignment = self.alignments[i]
                cell_width = widths[i]
                style = self.line_styles.get(y, style)
                if alignment == ">":
                    line.append((style, cell.rjust(cell_width)))
                else:
                    line.append((style, cell.ljust(cell_width)))
            return line

        return UIContent(
            get_line=get_line,
            line_count=len(self.lines),
            show_cursor=False,
        )
