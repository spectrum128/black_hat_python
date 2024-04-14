import sys
import socket
import threading


# hex dumping function taken from http://code.activestate.com/recipes/142812-hex-dumper/
def hexdump(src, length=16):
    result = []
    digits = 4 if isinstance(src, unicode) else 2

    for i in xrange(0, len(src), length):
        s = src[i:i+length]
        hexa = b" ".join(["%0*X" % (digits, ord(x)) for x in s])
        text = b"".join([x if 0x20 <= ord(x) < 0x7F else b"." for x in s])
        result.append(b"%04X %-*s %s" % (i, length*(digits + 1), hexa, text))

    print(b"\n".join(result))


def receive_from(connection):
    buffer = b""

    # We set a 2 second timeout but this might need to be adjusted
    # depending on the target
    connection.settimeout(2)

    try:
        # keep reading into the buffer until there is no more data
        # or we timeout
        while True:
            data = connection.recv(4096)

            if not data:
                break

            buffer += data

    except:
        pass

    return buffer


def request_handler(buffer):
    # perform any packet modifications to requests
    return buffer


def response_handler(buffer):
    # perform any packet modifications required to responses
    return buffer




def proxy_handler(client_socket, remote_host, remote_port, receive_first):

    # connect to the remote host
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_socket.connect((remote_host, remote_port))

    # receive data from the remote end if necessary
    if receive_first:
        remote_buffer = receive_from(remote_socket)
        hexdump(remote_buffer)

        # send it to our response handler
        remote_buffer = response_handler(remote_buffer)

        # if there is data to send to the local client send it
        if len(remote_buffer):
            print(f"[<==] Sending {len(remote_buffer)} to localhost.")
            client_socket.send(remote_buffer)

    # now loop and read from local, send to remote, send to local -> repeat
    while True:
        # read from local host
        local_buffer = receive_from(client_socket)

        if len(local_buffer):
            print(f"[==>] Received {len(local_buffer)} bytes from localhost.")
            hexdump(local_buffer)

            # send it to our request handler
            local_buffer = request_handler(local_buffer)

            # send off data to the remote host
            remote_socket.send(local_buffer)
            print(f"[==>] Sent to remote.")

        # receive back the response
        remote_buffer = receive_from(remote_socket)

        if len(remote_buffer):
            print(f"[<==] Received {len(remote_buffer)} bytes from remote.")
            hexdump(remote_buffer)

            # send to our response handler
            remote_buffer = response_handler(remote_buffer)

            # send the response to the local socket
            client_socket.send(remote_buffer)

            print(f"[<==] Sent to localhost.")


        # if no more data on either side close the connection
        if not len(local_buffer) or not len(remote_buffer):
            client_socket.close()
            remote_socket.close()

            print(f"[*] No more data. Closing connections.")
            break


                



def server_loop(local_host, local_port, remote_host, remote_port, receive_first):
    """Bind to a socket, listen for connections and then spin off a client handler thread to handle the request."""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.bind((local_host, local_port))
    except:
        print(f"[!!] Failed to listen on {local_host}:{local_port}")
        print("[!!] Check for other listening sockets or correct permissions.")
        sys.exit(1)

    print(f"[*] Listening on {local_host}:{local_port}")

    server.listen(5)

    while True:
        client_socket, addr = server.accept()

        print(f"[==>] Received incoming connection from {addr[0]}:{addr[1]}")

        proxy_thread = threading.Thread(target=proxy_handler, args=(client_socket, remote_host, remote_port, receive_first))

        proxy_thread.start()


def main():

    # no fancy command line parsing
    if len(sys.argv[1:]) != 5:
        print(f"Usage: ./proxy.py [localhost] [localport] [remotehost] [remoteport] [receive_first]")
        print(f"Example: ./proxy.py 127.0.0.1 9000 10.12.132.1 9000 True")
        sys.exit(0)

    # set up local params
    local_host = sys.argv[1]
    local_port = int(sys.argv[2])

    # set up remote target
    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])

    # this tells our proxy to connect and receive data
    # before sending it to the remote host
    receive_first = sys.argv[5]

    if "True" in receive_first or "true" in receive_first:
        receive_first = True
    else:
        receive_first = False

    # now sping up our listening socket
    server_loop(local_host, local_port, remote_host, remote_port, receive_first)


main()

