from websock import create_connection
import threading
import time
import sys

CURSOR_UP_ONE = '\x1b[1A' 
ERASE_LINE = '\x1b[2K'

print("state conn")
# ws = create_connection("ws://echo.websocket.org/")
ws = create_connection("ws://localhost:5001/")

meflag = True
def input_sender():
    while True:
        time.sleep(0.1)
        s = input("")
        ws.send(s)
        # sys.stdout.write("\033[2K\033[G\033[E")
        sys.stdout.flush()
def recv_stdio():
    while True:
        result =  ws.recv()
        # data_on_first_line =  CURSOR_UP_ONE + ERASE_LINE + "\n"
        # sys.stdout.write(data_on_first_line)

        # data_on_second_line = "def\r"
        # sys.stdout.write(data_on_second_line)
        # sys.stdout.flush()
        print("%s" % result)

thread1 = threading.Thread(target=input_sender)
thread2 = threading.Thread(target=recv_stdio)
thread1.start()
thread2.start()
# thread1.join()
# thread2.join()
