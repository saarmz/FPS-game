import socket, threading, traceback, random

IP = "127.0.0.1"
PORT = 9320

server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
threads = []
clients = {}

def diffie_hellman(cli_sock):
    n = int(cli_sock.recv(1024).decode("utf-8"))
    g = int(cli_sock.recv(1024).decode("utf-8"))
    b = random.randint(0, n)
    
    bg = (g**b) % n
    cli_sock.send(str(bg).encode("utf-8"))
    ag = int(cli_sock.recv(1024).decode("utf-8"))

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
            byte_data = cli_sock.recv(1024)
            if byte_data == b'':
                print('Seems client disconnected')
                break
            data = decrypt(byte_data.decode('utf-8'), key)
            handle_request(cli_sock, data)
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

    server_sock.listen()
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((IP, PORT))
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
