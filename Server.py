import socket, threading, traceback, random
import time

IP = "0.0.0.0"
PORT = 9320

server_sock = socket.socket()
threads = []
clients = {}

def recv(sock):
    byte_data = sock.recv(1024)
    if byte_data == b'':
        return ""
    else:
        return byte_data.decode("utf-8")

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
    pass

def handle_client(cli_sock, addr):
    print(f"New client from {addr}")
    finish = False
    key = diffie_hellman(cli_sock)
    while not finish:
        try:
            received = recv(cli_sock)
            if received != "":
                data = decrypt(received, key)
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
    server_sock.listen()
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # releasing the port
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
