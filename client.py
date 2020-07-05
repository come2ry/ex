from socket import *
import threading
import sys
import utils_multi as utils
from wrapt_timeout_decorator import *

FLAG = False  # this is a flag variable for checking quit
threads = []

# TODO (1) - define HOST name, this would be an IP address or 'localhost' (1 line)
HOST = 'localhost'  # The server's hostname or IP address
# HOST = '192.168.179.2'  # The server's hostname or IP address
# TODO (2) - define PORT number (1 line) (Google, what should be a valid port number)
PORT = 10001        # The port used by the server


# function for receiving message from client
def send_to_server(clsock):
    global FLAG
    while not FLAG:
        try:
            send_msg = utils.input_with_timeout('')
            if send_msg == '':
                continue
            if send_msg == 'q':
                FLAG = True
                clsock.send('q'.encode())
                break

            clsock.send(send_msg.encode())

        except TimeoutError:
            pass
        except OSError:
            pass
        except EOFError:
            pass
        except Exception as e:
            print(str(e))
            FLAG = True
            clsock.sendall('q'.encode())
            break

    print('Closing connection')
    clsock.close()


# function for receiving message from server
def recv_from_server(clsock):
    global FLAG
    while not FLAG:
        try:
            data = utils.recieve_with_timeout(clsock, 1024)
            if data == '':
                continue
            elif data == 'q':
                FLAG = True
                break
            elif data == 'qq':
                FLAG = True
                break
            elif data == 'quit':
                FLAG = True
                clsock.send('q'.encode())
                break
            elif data == 'start':
                proc = subprocess.run("cat ok > output.txt", shell=True, text=True)
                data = data + ": " + proc

            print('Server: ' + data)

        except TimeoutError:
            pass
        except OSError:
            pass
        except Exception as e:
            print(str(e))
            FLAG = True
            break

    print('Closing connection')


# this is main function
def main():
    global threads
    # Create a TCP client socket
    #(AF_INET is used for IPv4 protocols)
    #(SOCK_STREAM is used for TCP)
    # TODO (3) - CREATE a socket for IPv4 TCP connection (1 line)
    clientSocket = socket(AF_INET, SOCK_STREAM)

    # request to connect sent to server defined by HOST and PORT
    # TODO (4) - request a connection to the server (1 line)
    clientSocket.connect((HOST, PORT))
    print('Client is connected to a chat sever!\n')


    # call the function to send message to server
    #send_to_server(clientSocket)
    t_send = threading.Thread(target=send_to_server, args=(clientSocket,))
    # call the function to receive message server
    #recv_from_server(clientSocket)
    t_rcv = threading.Thread(target=recv_from_server, args=(clientSocket,))
    threads.append(t_send)
    threads.append(t_rcv)
    t_send.start()
    t_rcv.start()

    t_send.join()
    t_rcv.join()

    print('EXITING')
    sys.exit()

# This is where the program starts
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()
    except ConnectionRefusedError:
        print("ERROR: server.pyを先に実行してください")