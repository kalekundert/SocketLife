#!/usr/bin/python

import sys
import socket, select

stdin = sys.stdin
server = socket.socket()
poll = select.poll()

follows = {}

server.bind(("", 12345))
server.listen(5)
server.setblocking(0)

poll.register(stdin.fileno())
poll.register(server.fileno())

try:
    while True:
        events = poll.poll(10)

        for fileno, event in events:
            if not event & select.POLLIN:
                continue

            if fileno == server.fileno():
                print "Accepting a connection."

                follow, address = server.accept()
                follows[follow.fileno()] = follow

                poll.register(follow.fileno())

            if fileno == stdin.fileno():
                print "Requesting an update."
                buffer = stdin.readline()

except KeyboardInterrupt:
    print

finally:
    server.close()
    for follow in follows.values():
        follow.close()

