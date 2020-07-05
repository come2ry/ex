from wrapt_timeout_decorator import *
import platform
from datetime import datetime
import traceback

DEFAULT_TIMEOUT = 5
DEFAULT_t = 1000 # デフォルトの-tの値 測定する時間[s] 信頼区間にする
DEFAULT_i = 1 # デフォルトの-iの値 表示間隔[s]
DEFAULT_b = "1000M" # デフォルトの-bの値 送るパケットバイト数[M]

TIME_SUM = 0
WHODICT = {
    "server": "s",
    "s": "s",
    "client": "c",
    "c": "c"
}

# テスト
# MULTI_SERVER_COMMAND = "echo s_mul_{HOST}_{i}_{t} > {file_name}" # マルチキャスト
# UNI_SERVER_COMMAND = "echo s_uni_{HOST}_{i}_{t} > {file_name}" # ユニキャスト
# MULTI_CLIENT_COMMAND = "echo c_mul_{HOST}_{i}_{b}_{t} > test.txt" # マルチキャスト
# UNI_CLIENT_COMMAND = "echo c_uni_{HOST}_{i}_{b}_{t} > test.txt" # ユニキャスト
# テスト

MULTI_SERVER_COMMAND = "iperf -s -B {HOST} -i {i} -u -f m -p 5001 -w 1M -t {t} > {file_name}" # マルチキャスト
UNI_SERVER_COMMAND = "iperf -s -B {HOST} -i {i} -u -f m -p 5001 -w 1M -t {t} > {file_name}" # ユニキャスト
# MULTI_SERVER_COMMAND = "powershell -Command \"iperf -s -B {HOST} -i {i} -u -f m -p 5001 -w 1M -t {t} | Add-Content -Path {file_name}.txt -PassThru\"" # マルチキャスト
# UNI_SERVER_COMMAND = "powershell -Command \"iperf -s -B {HOST} -i {i} -u -f m -p 5001 -w 1M -t {t} | Add-Content -Path {file_name}.txt -PassThru\"" # ユニキャスト
MULTI_CLIENT_COMMAND = "iperf -s -B {HOST} -i {i} -u -f m -p 5001 -b {b}  -t {t}" # マルチキャスト
UNI_CLIENT_COMMAND = "iperf -s -B {HOST} -i {i} -u -f m -p 5001 -b {b} -t {t}" # ユニキャスト


COMMANDDICT = {
    "s": {
        "multi": MULTI_SERVER_COMMAND,
        "m": MULTI_SERVER_COMMAND,
        "uni": UNI_SERVER_COMMAND,
        "u": UNI_SERVER_COMMAND
    },
    "c": {
        "multi": MULTI_CLIENT_COMMAND,
        "m": MULTI_CLIENT_COMMAND,
        "uni": UNI_CLIENT_COMMAND,
        "u": UNI_CLIENT_COMMAND
    }
}

if "windows" in platform.system().lower():
    import msvcrt
    import time

    def input_with_timeout(prompt='', timeout=DEFAULT_TIMEOUT):
        begin = time.monotonic()
        end = begin + timeout
        for c in prompt:
            msvcrt.putwch(c)
        line = ''
        is_timeout = True
        while time.monotonic() < end:
            if msvcrt.kbhit():
                c = msvcrt.getwch()
                msvcrt.putwch(c)
                if c == '\r' or c == '\n':
                    is_timeout = False
                    break
                if c == '\003':
                    return 'q'
                if c == '\b':
                    line = line[:-1]
                else:
                    line = line + c
            time.sleep(0.05)

        if is_timeout:
            return ''

        msvcrt.putwch('\r')
        msvcrt.putwch('\n')

        return line

else:
    import sys
    import select

    def input_with_timeout(prompt, timeout=DEFAULT_TIMEOUT):
        while 1:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            ready, _, _ = select.select([sys.stdin], [],[], timeout)
            if ready:
                send = sys.stdin.readline().rstrip('\n')
                if send == '':
                    print("1")
                    continue
                elif send == 'q':
                    break
                return send # expect stdin to be line-buffered

            else:
                return ''

        return 'q'


@timeout(DEFAULT_TIMEOUT, use_signals=False)
def recieve_with_timeout(clsock, bytes_n=1024):
    while 1:
        try:
            rec = clsock.recv(bytes_n).decode()
            if rec == '':
                continue
            return rec

        except TimeoutError:
            pass
        except OSError:
            pass
        except KeyboardInterrupt:
            print("終了したい場合は q を入力してください")
            return 'quit'
        except Exception as e:
            traceback.print_exc()


@timeout(DEFAULT_TIMEOUT, use_signals=False)
def accept_with_timeout(serverSocket):
    while 1:
        try:
            connectionSocket, addr = serverSocket.accept()
            return connectionSocket, addr

        except TimeoutError:
            continue
        except OSError:
            continue
        except KeyboardInterrupt:
            print("終了したい場合は q を入力してください")
            return None, None
        except Exception as e:
            traceback.print_exc()


def send_for_conns(conns, message):
    for conn in conns:
        try:
            conn.send(message.encode())
        except OSError:
            continue
        except Exception as e:
            traceback.print_exc()


def close_conns(conns):
    for conn in conns:
        conn.close()


def parse_message(message):
    _cmds = message.split(' ')
    _cmds = [_ for _ in _cmds if _ != '']

    cmds = {}
    opt = None

    if _cmds[0] in ['s', 'server', 'c', 'client']:
        cmds["who"] = _cmds[0]
        _cmds = _cmds[1:]

    if _cmds[0] in ['u', 'uni', 'm', 'multi']:
        cmds["mode"] = _cmds[0]
        _cmds = _cmds[1:]

    for i, cmd in enumerate(_cmds):
        if not opt is None:
            cmds[opt] = cmd
            opt = None
        elif cmd[0] == '-':
            opt = cmd[1]
        else:
            return None

    return cmds


def parse_command(cmds, HOST):
    error = []
    status = 200
    parsed_cmds = {}
    try:
        mode = cmds.get("mode")
        if mode is None or mode not in COMMANDDICT['s'].keys():
            error.append("ERROR: コマンドにu(uni) or m(multi)の指定がありません。")

        who = cmds.get("who")
        if who is None:
            who = ['s', 'c']
        else:
            who = [WHODICT[who]]
            status += 1 if who == 's' else 2

        if len(error):
            return ({"error_message": "\n".join(error)}, 400)

        for w in who:
            bash_cmd = COMMANDDICT[w][mode]

            i = cmds.get("i", DEFAULT_i)
            if not i.isdigit():
                error.append("ERROR: -iの値が正しくありません。数字のみ指定できます。")
            else:
                i = int(i)

            t = cmds.get("t", DEFAULT_t)
            if not t.isdigit():
                error.append("ERROR: -tの値が正しくありません。数字のみ指定できます。")
            else:
                t = int(t)

            b = cmds.get("b", DEFAULT_b)
            if not b[:-1].isdigit() or b[-1] != 'M':
                error.append("ERROR: -bの値が正しくありません。-b 1000M のように指定してください。")

            if len(error):
                return ({"error_message": "\n".join(error)}, 400)

            if w == 's':
                now_str = datetime.now().strftime("%m%d%H%M%S%f")
                fle_name = "{now_str}_{who}_{mode}_i-{i}_t-{t}.log".format(
                    now_str=now_str,
                    who=who,
                    mode=mode,
                    i=i,
                    t=t
                )
                bash_cmd = bash_cmd.format(HOST=HOST, i=i, t=t, file_name=fle_name)
                parsed_cmds[w] = bash_cmd

            elif w == 'c':
                bash_cmd = bash_cmd.format(HOST=HOST, i=i, b=b, t=t)
                parsed_cmds[w] = bash_cmd

        return (parsed_cmds, status)

    except Exception as e:
        traceback.print_exc()
        return (None, None)
