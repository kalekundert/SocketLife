#!/usr/bin/python

import sys
import socket, select, messages

follows = {}

HOST = ""
PORT = 12345

stdin = sys.stdin
server = socket.socket()
poll = select.poll()

try:
    server.bind((HOST, PORT))
    server.listen(5)
    server.setblocking(0)

    poll.register(stdin.fileno())
    poll.register(server.fileno())

    while True:
        events = poll.poll(10)

        for fileno, event in events:
            if not event & select.POLLIN:
                continue

            if fileno == server.fileno():
                print "Accepting a connection."

                follow, address = server.accept()
                follow.settimeout(0)
                follows[follow.fileno()] = follow

                poll.register(follow.fileno())

            if fileno == stdin.fileno():
                print "Requesting an update."

                garbage = stdin.readline()
                message = messages.request_update

                for follow in follows.values():
                    try: follow.send(message)

                    # Gracefully handle broken connections.
                    except socket.error:
                        print "Closing a broken connection."
                        del follows[follow.fileno()]
                        follow.close()

except KeyboardInterrupt:
    print

finally:
    server.close()
    for follow in follows.values():
        follow.close()

    print "Closing all sockets."


