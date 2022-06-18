import socket, threading, traceback, random, time
# encryption imports:
import json
from base64 import b64encode, b64decode
from Crypto.Cipher import ChaCha20

IP = "0.0.0.0"
PORT = 9321

server_sock = socket.socket()
threads = []
keys = {}
lobbies = {}

class Lobby():
    def __init__(self, name, password, host, host_sock):
        self.name = name
        self.password = password
        self.host = host
        self.players = {host : [host_sock]}
        self.playing = False

    def add_player(self, name, player_sock):
        self.players[name] = [player_sock]
    
    def generate_locations(self):
        #TODO: generate locations that don't collide with walls
        pass

    def ready(self):
        if not self.playing:
            self.playing = True
            tcp_broadcast("GAMEON", self.name)
            print(f"Starting lobby called {self.name}")
            #TODO: send wall's locations
            tcp_broadcast("WALL~-13~0~0~13~5~1", self.name)
            time.sleep(3)
            tcp_broadcast("WALL~-13~0~15~13~5~1", self.name)
            time.sleep(3)
            tcp_broadcast("WALL~-13~0~30~13~5~1", self.name)
            time.sleep(3)
            # generating and sending player locations
            self.generate_locations()
            tcp_broadcast("START", self.name)
    

def encrypt_send(sock, text, key):
    #encrypt
    cipher = ChaCha20.new(key=key)
    ciphertext = cipher.encrypt(text.encode("utf-8"))
    # get the nonce and text and build message
    nonce = b64encode(cipher.nonce).decode("utf-8")
    ct = b64encode(ciphertext).decode("utf-8")
    result = json.dumps({'nonce':nonce, 'ciphertext':ct})
    #send it to the client
    sock.send(result.encode("utf-8"))

    #TODO: remove print after debug
    print(result)

def decrypt(data, key):
    try:
        # split dictionary to ciphertext and nonce
        b64 = json.loads(data)
        nonce = b64decode(b64['nonce'])
        ciphertext = b64decode(b64['ciphertext'])
        # decrypt
        cipher = ChaCha20.new(key=key, nonce=nonce)
        text = cipher.decrypt(ciphertext).decode("utf-8")

        #TODO: remove print after debugging
        print(f"received - {text}")


        return text

    except (ValueError, KeyError):
        print("Incorrect decryption")

def recv(sock):
    byte_data = sock.recv(1024)
    if byte_data == b'':
        return ""
    else:
        return byte_data.decode("utf-8")

def tcp_broadcast(message, lobby):
    global lobbies
    print(f"broadcasting - {message}")
    for player in lobbies[lobby].players:
        encrypt_send(lobbies[lobby].players[player][0], message, keys[player])

def diffie_hellman(cli_sock):
    n = 1008001 # relatively large prime number
    g = 151 # small prime number
    b = random.randint(0, n)
    
    bg = (g**b) % n
    cli_sock.send(str(bg).encode("utf-8"))
    ag = int(cli_sock.recv(2048).decode("utf-8"))

    key = (ag**b) % n
    return key.to_bytes(32, "little")


def handle_request(cli_sock, data, key):
    global lobbies

    if data.startswith("NEW"):
        # Create a new lobby
        splits = data.split("~")
        keys[splits[1]] = key
        # split 0 - request, 1 - player's nickname, 2 - lobby name, 3 - password
        if splits[2] not in lobbies:
            lobbies[splits[2]] = Lobby(splits[2], splits[3], splits[1], cli_sock)
            print(f"Created a new lobby called {splits[2]}")
            encrypt_send(cli_sock, "CREATED", key)
        else:
            encrypt_send(cli_sock, "ERROR~TAKEN", key)

    elif data.startswith("JOIN"):
        # Join a lobby
        splits = data.split("~")
        # split 0 - request, 1 - player's nickname, 2 - lobby name, 3 - password
        keys[splits[1]] = key
        if splits[2] in lobbies:
            if splits[3] == lobbies[splits[2]].password:
                lobbies[splits[2]].add_player(splits[1], cli_sock)
                print(f"{splits[1]} joined the lobby called {splits[2]}")
                encrypt_send(cli_sock, "JOINED", key)
            else:
                #return wrong password message
                encrypt_send(cli_sock, "ERROR~password", key)
        else:
            #return wrong lobby name message
            encrypt_send(cli_sock, "ERROR~name", key)
    
    elif data.startswith("READY"):
        # host wants to start the game
        splits = data.split("~")
        # split 0 - request, 1 - player's nickname, 2 - lobby name, 3 - password
        if splits[2] in lobbies:
            if splits[3] == lobbies[splits[2]].password:
                if splits[1] == lobbies[splits[2]].host:
                    lobbies[splits[2]].ready()
                else:
                    #TODO: return only host can start message
                    encrypt_send(cli_sock, "ERROR~not_host", key)
            else:
                #TODO: return wrong password message
                encrypt_send(cli_sock, "ERROR~password", key)
        else:
            #TODO: return invalid name error
            encrypt_send(cli_sock, "ERROR~name", key)

def handle_client(cli_sock, addr):
    print(f"New client from {addr}")
    finish = False
    key = diffie_hellman(cli_sock)
    while not finish:
        try:
            data = recv(cli_sock)
            print(f"received - {data}")
            if data != "":
                message = decrypt(data, key)
                handle_request(cli_sock, message, key)
            else:
                break
            if finish:
                break
        except socket.error as err:
            print(f'Socket Error {addr} - {err}')
            break
        except Exception as err:
            print(f'General Error {addr} - {err}')
            print(traceback.format_exc())
            break

def main():
    global server_sock

    server_sock.bind((IP, PORT))
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # releasing the port
    server_sock.listen()
    print("Server running...")

    while True:
        try:
            cli_sock, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(cli_sock, addr))
            t.start()
            threads.append(t)

        except Exception as ex:
            print(f"Client exception: {str(ex)}")
    
    for t in threads:
        t.join()
    server_sock.close()
    print("Server closed")

if __name__ == "__main__":
    main()
