import socket
import json

HOST = '127.0.0.1'   # The server's hostname or IP address
PORT = 23000         # The port used by the server
AUTH = 'fixme'       # The token required by the server

def json_message(direction):
    local_ip = socket.gethostbyname(socket.gethostname())
    
    data = {
        'type': 'SPOT.GRID',
        'params': {'AUTH': AUTH, 'CALL': 'T32ZA', 'GRID': 'BJ11LV', 'COLOR': '#ff2a00'},
        'sender': local_ip,
        'instruction': direction
    }

    json_data = json.dumps(data, sort_keys=False, indent=2)
    print("data %s" % json_data)

    send_message(json_data)

    return json_data

def send_message(data):
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((HOST, PORT))
    s.sendall(data.encode())

##    data = s.recv(1024)
##    print('Received', repr(data))

json_message("SOME_DIRECTION")

"""
Scratch Pad

T32ZA, BJ11LV
E51AAA, BG08AP
ZF2ZL, EK99IG
V63NA, PJ77GH


'params': {'AUTH': 'fixme', 'CALL': 'T32ZA', 'GRID': 'BJ11LV', 'COLOR': '#ff2a00'}

'params': {'AUTH': 'fixme', 'MESSAGE': '01234567890123456789012345678901234567890123456789'}


{'SPOT': 'Point,Test Point,45.0,-122.0,#ff2600'}

{
  "Type": "Csv",
  "Data": "Point,Test Point,45.0,-122.0,#ff0000
Location,PostalCode,97045,Oregon City,#ffaa00"
}

params = {
    'Type': 'Point',
    'Label': '"Test Point 2"',
    'ShowPoint': 'True',
    'Lat': '45.0',
    'Lng': '-122.0',
    'Color': '#ff2600',
    'Icon': {"ImageURL":"","ImageHash":"","Rotation":0.0}
}


"""
