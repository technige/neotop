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


import click


@click.command()
@click.option("-u", "--user",
              envvar="NEO4J_USER")
@click.option("-p", "--password",
              envvar="NEO4J_PASSWORD",
              prompt="Neo4j password",
              confirmation_prompt=False,
              hide_input=True)
@click.argument("address",
                envvar="NEO4J_ADDRESS")
def main(address=None, user=None, password=None):
    from neotop.application import Neotop
    raise SystemExit(Neotop(
        address=address,
        user=user,
        password=password,
    ).run())


if __name__ == '__main__':
    main()
