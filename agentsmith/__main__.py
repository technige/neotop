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


@click.command(help="""\
Monitor Neo4j servers and clusters.

The ADDRESS should be supplied in either host:port format or as a simple host name or IP address.
If the port is omitted, 7687 is assumed.
""")
@click.option("-u", "--user",
              metavar="USER",
              envvar="NEO4J_USER",
              help="Neo4j user name (can also be supplied in NEO4J_USER environment variable)")
@click.option("-p", "--password",
              metavar="PASSWORD",
              envvar="NEO4J_PASSWORD",
              prompt="Neo4j password",
              help="Neo4j password (can also be supplied in NEO4J_PASSWORD environment variable)",
              confirmation_prompt=False,
              hide_input=True)
@click.argument("address",
                envvar="NEO4J_ADDRESS",
                default="localhost:7687")
def main(address=None, user=None, password=None):
    from agentsmith.application import AgentSmith
    raise SystemExit(AgentSmith(
        address=address,
        user=user,
        password=password,
    ).run())


if __name__ == '__main__':
    main()
