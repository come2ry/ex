# Import socket module
from socket import *
import threading
import sys # In order to terminate the program
import utils_multi as utils
import time
import subprocess
from collections import deque
import traceback

FLAG = False  # this is a flag variable for checking quit
job_queue = deque([])
threads = []
connectionSockets = []
# TODO (1) - define HOST name, this would be an IP address or 'localhost' (1 line)
HOST = 'localhost'
# HOST = '192.168.179.2'
# TODO (2) - define PORT number (1 line) (Google, what should be a valid port number)
# make sure the ports are not used for any other application
serverPort = 10001
backlog = 5  # how many connections to accept

def accept_client(serverSocket):
    global FLAG, threads
    while not FLAG:
        try:
            connectionSocket, addr = utils.accept_with_timeout(serverSocket)
            if connectionSocket is None or addr is None:
                break
            print('Sever is connected with a chat client\n')
            t_rcv = threading.Thread(target=recv_from_client, args=(connectionSocket,))
            t_send = threading.Thread(target=send_to_client, args=(connectionSocket,))
            # call the function to receive message server
            # recv_from_server(clientSocket)
            threads.append(t_rcv)
            threads.append(t_send)
            t_rcv.start()
            t_send.start()

            t_rcv.join()
            t_send.join()

        except TimeoutError:
            continue
        except OSError:
            continue
        except KeyboardInterrupt:
            print("終了したい場合は q を入力してください")
            return None, None
        except Exception as e:
            traceback.print_exc()
            break



# function for receiving message from client
def recv_from_client(conn):
    global FLAG
    # Receives the request message from the client
    while not FLAG:
        try:
            message = utils.recieve_with_timeout(conn, 1024)
            # if 'q' is received from the client the server quits
            if message == '':
                continue

            print('Client: ' + message)
            if message == 'q':
                FLAG = True
                break
            elif message == 'quit':
                FLAG = True
                break
            else:
                cmds = utils.parse_message(message)
                if cmds is None:
                    res_message = "ERROR: コマンドが正しくありません。\n例) u -i 1 -b 1000M -t 1000 -f test_1.txt"
                    print(res_message)
                    job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す
                    continue
                else:
                    parsed_cmds, status = utils.parse_command(cmds, HOST)
                    if status == 400:
                        message = parsed_cmds.get("error_message", "予期せぬエラー")
                        print(message)
                        job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す
                        continue
                    elif status == 200:
                        # serverもclientも実行
                        s_bash_cmd = parsed_cmds.get('s', None)
                        c_bash_cmd = parsed_cmds.get('c', None)
                        if s_bash_cmd is None or c_bash_cmd is None:
                            print('ERROR: 予期せぬエラー')
                            job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す
                        else:
                            res_message = ' Server Command Run: ' + s_bash_cmd
                            print(res_message)
                            job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す
                            res_message = ' Send Client Command: ' + c_bash_cmd
                            print(res_message)
                            job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す

                            proc = subprocess.run(s_bash_cmd, shell=True, text=True)
                            if proc.returncode != 0:
                                # error
                                res = proc.stderr
                            else:
                                res = proc.stdout
                                res = 'success' if res == '' else res

                            job_queue.append(('c', c_bash_cmd)) # 後からsend_to_clientがpopして返す
                            res = "出力なし" if res is None else res
                            res_message = ' Result: ' + res
                            print(res_message)
                            job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す

                    elif status == 201:
                        # serverのみ実行
                        s_bash_cmd = parsed_cmds.get('s', None)
                        res_message = ' Only Server Command Run: ' + s_bash_cmd
                        print(res_message)
                        job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す
                        proc = subprocess.run(s_bash_cmd, shell=True, text=True)
                        res_message = ' Result: ' + proc
                        print(res_message)
                        job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す

                    elif status == 202:
                        res_message = ' Only Send Client Command: ' + c_bash_cmd
                        print(res_message)
                        job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す
                        job_queue.append(('c', c_bash_cmd)) # 後からsend_to_clientがpopして返す

        except TimeoutError:
            pass
        except OSError:
            pass
        except Exception as e:
            # print(str(e))
            traceback.print_exc()
            FLAG = True
            break


    print('Closing connection')
    conn.close()


# function for receiving message from client
def send_to_client(conns):
    global FLAG
    while not FLAG:
        try:
            while len(job_queue):
                who, bash_cmd = job_queue.popleft()
                if who == 'c':
                    utils.send_for_conns(conns, bash_cmd)
                elif who == 's':
                    res_message = ' Que Server Command Run: ' + bash_cmd
                    print(res_message)
                    job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す

                    proc = subprocess.run(bash_cmd, shell=True, text=True)
                    res_message = ' Result: ' + proc
                    print(res_message)
                    job_queue.append(('c', res_message)) # 後からsend_to_clientがpopして返す

            send_msg = utils.input_with_timeout('')
            # the server can provide 'q' as an input if it wish to quit
            if send_msg == '':
                continue
            elif send_msg == 'q':
                FLAG = True
                utils.send_for_conns(conns, 'q')
                break

            utils.send_for_conns(conns, send_msg)

        except TimeoutError:
            pass
        except OSError:
            pass
        except Exception as e:
            traceback.print_exc()
            traceback.print_exc()
            FLAG = True
            utils.send_for_conns(conns, 'q')
            break

    try:
        utils.send_for_conns(conns, 'q')
    except Exception as e:
        traceback.print_exc()

    print('Closing connection')
    utils.close_conns(conns)


# this is main function
def main():
    global FLAG, threads, connectionSockets

    # Create a TCP server socket
    # (AF_INET is used for IPv4 protocols)
    # (SOCK_STREAM is used for TCP)
    # TODO (3) - CREATE a socket for IPv4 TCP connection (1 line)
    serverSocket = socket(AF_INET, SOCK_STREAM)

    # Bind the socket to server address and server port
    # TODO (4) - bind the socket for HOSR and serverPort (1 line)
    for i in range(40):
        try:
            serverSocket.bind((HOST, serverPort))
            break
        # except OSError:
        #     print("ポートが空くまで待機中...")
        #     time.sleep(1)
        #     continue
        except Exception as e:
            if '48' in str(e):
                print("ポートが空くまで待機中...")
                time.sleep(3)
                continue
            elif '49' in str(e):
                pass
            traceback.print_exc()

    # Listen to at most 1 connection at a time
    # TODO (5) - listen and wait for request from client (1 line)
    serverSocket.listen(backlog)

    # Server should be up and running and listening to the incoming connections
    print('The chat server is ready to connect to a chat client')
    # TODO (6) - accept any connection request from a client (1 line)

    # t_accept = threading.Thread(target=accept_client, args=(serverSocket,))


    client_count = 0

    while not FLAG and client_count != 2:
        try:
            connectionSocket, addr = serverSocket.accept()
            # connectionSocket, addr = utils.accept_with_timeout(serverSocket)
            if connectionSocket is None or addr is None:
                break
            client_count += 1
            print('Sever is connected with a chat client {}\n'.format(client_count))
            connectionSockets.append(connectionSocket)

        except TimeoutError:
            print("1")
            continue
        # except OSError:
        #     print("2")
        #     continue
        except KeyboardInterrupt:
            print("終了したい場合は q を入力してください")
            return None, None
        except Exception as e:
            traceback.print_exc()
            break

    t_send = threading.Thread(target=send_to_client, args=(connectionSockets,))
    threads.append(t_send)
    for connectionSocket in connectionSockets:
        t_rcv = threading.Thread(target=recv_from_client, args=(connectionSocket,))
        threads.append(t_rcv)

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # closing serverScoket before exiting
    print('EXITING')
    serverSocket.close()
    #Terminate the program after sending the corresponding data
    sys.exit()


# This is where the program starts
if __name__ == '__main__':
    try:
        main()
    except OSError as e:
        traceback.print_exc()
        # print("ERROR: Portを開放中です。20秒くらいしてからもう一度実行してください。")
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        traceback.print_exc()