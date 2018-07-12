======
Neotop
======

Neo4j query monitor

Installation
============

::

    $ pip install neotop


Usage
=========

::

    $ neotop --help

    Usage: neotop [OPTIONS] ADDRESS

      Monitor Neo4j servers and clusters.

      The ADDRESS should be supplied in either host:port format or as a simple
      host name or IP address. If the port is omitted, 7687 is assumed.

    Options:
      -u, --user USER          Neo4j user name (can also be supplied in NEO4J_USER
                               environment variable)
      -p, --password PASSWORD  Neo4j password (can also be supplied in
                               NEO4J_PASSWORD environment variable)
      --help                   Show this message and exit.

    $ neotop  --user neo4j --password secret localhost:7687


Screenshot
==========

.. image:: docs/screenshot.png