import socket
import json

HOST = '127.0.0.1'   # The server's hostname or IP address
PORT = 23000         # The port used by the server
AUTH = 'fixme'       # The token required by the server

def json_message():
    data = {
        'type': 'MESSAGE.CLEAR',
        'params': {'AUTH': AUTH}
    }

    json_data = json.dumps(data, sort_keys=False, indent=2)
    send_message(json_data)

def send_message(data):
    sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((HOST, PORT))
    sock.sendall(data.encode())

json_message()

