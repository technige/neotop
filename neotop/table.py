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


class TableViewControl(UIControl):

    def __init__(self, title):
        self.lines = [
            title,
            [("", "")],
        ]
        self.line_styles = {
            0: "fg:ansiwhite bg:ansibrightblack",
            1: "fg:ansiwhite bg:ansibrightblack",
        }
        self.alignments = ["<"]

    def set_title_style(self, style):
        self.line_styles[0] = style

    def set_fields(self, fields):
        self.lines[1] = list(fields or [("", "")])

    def set_alignments(self, alignments):
        self.alignments[:] = list(alignments or ["<"])

    def clear(self):
        self.lines[2:] = []

    def append(self, values):
        self.lines.append([(style, str(value)) for style, value in values])

    def widths(self):
        widths = list(map(len, self.lines[1]))
        for row in self.lines[1:]:
            for x, (_, cell) in enumerate(row):
                size = len(cell)
                if size > widths[x]:
                    widths[x] = size
        return widths

    def create_content(self, width, height):
        widths = self.widths()
        used_width = sum(widths)
        widths[-1] += width - used_width

        def get_line(y):
            if y == 0:
                u_width = sum(len(cell) for style, cell in self.lines[y])
                return [(style or self.line_styles[y], cell) for style, cell in self.lines[y]] + \
                       [(self.line_styles[y], " " * (width - u_width))]
            line = []
            for x, (style, cell) in enumerate(self.lines[y]):
                if x > 0:
                    line.append((self.line_styles.get(y, ""), " "))
                alignment = self.alignments[x]
                cell_width = widths[x]
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
