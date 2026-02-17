import socket
import time

HOST = 'IP_MACHINE_A'
PORT = 5000

s = socket.socket()
s.connect((HOST, PORT))

while True:
    data = s.recv(1024)
    if not data:
        break

    t_remote = float(data.decode())
    t_local = time.time()

    offset = t_local - t_remote
    print(time.time(), offset)
