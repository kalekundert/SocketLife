#!/usr/bin/python

import sys, time
import socket, select, messages

# State Machine
# =============
# I can imagine at least two distinct states that the follow might be in.  In
# the first, the follow is just accepting connections and listening to the
# server.  The second state begins once the lead requests an update and ends
# once the lead confirms that the update has been received.  During this
# state, new connections to peers are not accepted.
#
# Handshakes
# ==========
# I get the impression that handshakes are a big part of networked
# communication.  In the future, I might want to formalize them into some sort
# of class.
#
# Packet Protocol
# ===============
# I really need to decide on a packet protocol.  If it is going to be
# complicated at all, I'll probably need to hide the low-level socket
# interface.  
#
# For now, I'll just assume all the packets are smaller than 64 bytes and that
# they are received in one call.

# Todo
# ====
# 1. The Updating state falls into an infinite loop if the server closes the
# connection.  The reason is that poll() a closed socket is indicated by a
# buffer that is readable but empty.  Since it will stay readable forever, an
# infinite loop is created.
#
# 2. Figure out what difference socket.settimeout(0) makes.
#
# 3. Hypothesis:  I'll only have to wait for a socket to be closed and
# reopened if the server dies before the client.  In these cases, the
# operating system can't be sure that all the clients are disconnected, so it
# prevents a new socket from being created.  But if the clients are all
# gracefully closed before the server, then the socket will close properly
# and can be reopened immediately.

class Listening:

    def enter(self, status, lead, greeter, peers):
        print "Waiting for the next round."

    def update(self, status, lead, greeter, peers):
        finished = False
        events = status.poll(10)

        for fileno, flags in events:
            if not flags & select.POLLIN:
                continue

            # Make sure nothing is being blocked.
            if fileno == sys.stdin.fileno():
                print "Input acknowledged."
                garbage = sys.stdin.readline()

            # Switch states if an update is requested.
            if fileno == lead.fileno():
                message = lead.recv(4)
                finished = (message == messages.request_update)

                # Close if the connection to the lead is lost.
                if not message:
                    raise KeyboardInterrupt

            # Respond to any peers attempting to connect.
            if fileno == greeter.fileno():
                peer, address = greeter.accept()
                peer.settimeout(0)

                print "Accepting a connection."

                peers[peer.fileno()] = peer
                status.register(peer.fileno())

        return Updating() if finished else self

class Updating:

    # Send game information to all connected peers.
    def enter(self, status, lead, greeter, peers):
        print "Advancing to the next round."

    # Wait for the lead to indicate that the update has finished.
    def update(self, status, lead, greeter, peers):
        finished = False
        events = status.poll(10)

        for fileno, flags in events:

            # Make sure nothing is being blocked.
            if fileno == sys.stdin.fileno():
                if flags & select.POLLIN:
                    print "Input acknowledged."
                    garbage = sys.stdin.readline()

            # Read incoming state information from peers.
            if fileno in peers:
                continue

            # Wait for the lead to indicate that the update has finished.
            if fileno == lead.fileno():
                if not flags & select.POLLIN:
                    continue

                message = lead.recv(4)
                finished = (message == messages.update_complete)

                # Close if the connection to the lead is lost.
                if not message:
                    raise KeyboardInterrupt

        return Listening() if finished else self

class Reporting:

    def enter(self, status, lead, greeter, peers):
        # Send info to the lead.
        message = messages.Report(1)
        lead.send(message.pack())

    def update(self, status, lead, greeter, peers):
        pass

if __name__ == "__main__":

    HOST = "localhost"
    PORT = 12345

    peers = {}

    lead = socket.socket()
    greeter = socket.socket()
    status = select.poll()

    try:
        # Create a connection to the lead.
        lead.connect((HOST, PORT))
        lead.settimeout(0)

        # Listen for incoming connections.
        greeter.bind(("", 0))
        greeter.listen(5)
        greeter.settimeout(0)

        # Publish the port being listened to.
        print "Listening to %s on port %d." % greeter.getsockname()

        # Check the sockets for incoming data.
        status.register(lead.fileno())
        status.register(greeter.fileno())
        status.register(sys.stdin.fileno())

        # Initialize the state machine.
        state = Listening()
        state.enter(status, lead, greeter, peers)

        # Continue updating whichever state is currently active.
        while True:
            next = state.update(status, lead, greeter, peers)
            if next is not state:
                state = next
                state.enter(status, lead, greeter, peers)

    except KeyboardInterrupt:
        # Close nicely on a keyboard interrupt.
        sys.stdout.write("\r")

    finally:
        # Clean up all the sockets that were opened.
        lead.close()
        greeter.close()

        for peer in peers.values():
            peer.close()

        print "Closing all open sockets."


