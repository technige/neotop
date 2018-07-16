#!/usr/bin/env python


from random import random, choice
from threading import Thread
from time import sleep
from uuid import uuid4

from neo4j.v1 import GraphDatabase


driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))


def get_random_name():
    return uuid4().hex[0:8]


def run_match():
    while True:
        with driver.session() as session:
            session.run("MATCH (a:Person) "
                        "WHERE a.name CONTAINS $first "
                        "AND a.name CONTAINS $second "
                        "AND NOT a.name CONTAINS $third "
                        "AND NOT a.name CONTAINS '" + choice("123456789&^") + "' "
                        "RETURN a.name",
                        first=choice("abc"), second=choice("def"),
                        third=choice("0#!")).data()
        sleep(random())


def main():
    for _ in range(200):
        Thread(target=run_match, daemon=True).start()
    while True:
        with driver.session() as session:
            name = get_random_name()
            print(name)
            session.run("MERGE (a:Person {name:$name}) RETURN id(a)", name=name)
        # sleep(0.2)


if __name__ == "__main__":
    main()
