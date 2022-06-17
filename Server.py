import socket, threading, traceback, random
import time

IP = "0.0.0.0"
PORT = 9321

server_sock = socket.socket()
threads = []
clients = {}
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
    
    def ready(self):
        if not self.playing:
            self.playing = True
            tcp_broadcast("GAMEON", self.name)
            #TODO: send all player's and wall's locations
    

def recv(sock):
    byte_data = sock.recv(1024)
    if byte_data == b'':
        return ""
    else:
        #TODO: delete print line
        print(f"received: {byte_data.decode('utf-8')}")
        return byte_data.decode("utf-8")

def tcp_broadcast(message, lobby):
    global lobbies
    for player in lobbies[lobby].players:
        lobbies[lobby].players[player][0].send(message.encode("utf-8"))

def diffie_hellman(cli_sock):
    n = 1008001 # relatively large prime number
    g = 151 # small prime number
    b = random.randint(0, n)
    
    bg = (g**b) % n
    cli_sock.send(str(bg).encode("utf-8"))
    ag = int(cli_sock.recv(2048).decode("utf-8"))

    key = (ag**b) % n
    return key

def decrypt(data, key):
    pass

def handle_request(cli_sock, data):
    global lobbies

    if data.startswith("NEW"):
        # Create a new lobby
        splits = data.split("~")
        # split 0 - request, 1 - player's nickname, 2 - lobby name, 3 - password
        lobbies[splits[2]] = Lobby(splits[2], splits[3], splits[1], cli_sock)
        print(f"Created a new lobby called {splits[2]}")

    elif data.startswith("JOIN"):
        # Join a lobby
        splits = data.split("~")
        # split 0 - request, 1 - player's nickname, 2 - lobby name, 3 - password
        if splits[2] in lobbies:
            if splits[3] == lobbies[splits[2]].password:
                lobbies[splits[2]].add_player(splits[1], cli_sock)
                print(f"{splits[1]} joined the lobby called {splits[2]}")
            else:
                #TODO: return wrong password message
                pass
        else:
            #TODO: return wrong lobby name message
            pass
    
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
                    pass
            else:
                #TODO: return wrong password message
                pass
        else:
            #TODO: return invalid name error
            pass

def handle_client(cli_sock, addr):
    print(f"New client from {addr}")
    finish = False
    key = diffie_hellman(cli_sock)
    while not finish:
        try:
            data = recv(cli_sock)
            if data != "":
                # data = decrypt(data, key)
                handle_request(cli_sock, data)
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
