"""
Simple chat server - accepts multiple clients and broadcasts messages
Basic version using just the console (no GUI)
"""

import socket
import threading

# server settings
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024

# store all connected clients
# using a dict so i can track names -> sockets
clients = {}
lock = threading.Lock()  # need this because multiple threads touch the clients dict


def broadcast(message, skip_name=None):
    """send a message to all connected clients (except the one we want to skip)"""
    with lock:
        for name in list(clients.keys()):
            if name == skip_name:
                continue
            try:
                clients[name].sendall(message.encode('utf-8'))
            except:
                # if sending fails, just skip - they probably disconnected
                # the handle_client function will clean them up
                print(f"  [!] couldnt send to {name}, skipping")


def handle_client(conn, addr):
    """handles one client connection in its own thread"""
    client_name = None

    try:
        # first thing the client sends is their name
        name_data = conn.recv(BUFFER_SIZE).decode('utf-8')
        if not name_data:
            conn.close()
            return

        client_name = name_data.strip()
        # print(f"DEBUG: received name = '{client_name}'")

        with lock:
            clients[client_name] = conn

        print(f"[+] {client_name} joined the chat (from {addr})")

        # let everyone know someone new connected
        broadcast(f"[Server] {client_name} has joined the chat!", skip_name=client_name)

        # main loop - keep receiving messages from this client
        while True:
            data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                break  # client disconnected

            msg = data.strip()
            # print(f"DEBUG: {client_name} sent: '{msg}'")

            # check if client wants to leave
            if msg.lower() == 'bye':
                print(f"[-] {client_name} said bye, disconnecting them")
                # let the client know we got it
                try:
                    conn.sendall("[Server] Goodbye! You have left the chat.".encode('utf-8'))
                except:
                    pass
                break

            # normal message - broadcast to everyone
            print(f"  {client_name}: {msg}")
            broadcast(f"{client_name}: {msg}", skip_name=client_name)

    except ConnectionResetError:
        print(f"[!] {client_name or addr} connection was reset")
    except Exception as e:
        print(f"[!] error with {client_name or addr}: {e}")

    # cleanup - remove client and close connection
    if client_name:
        with lock:
            if client_name in clients:
                del clients[client_name]
        broadcast(f"[Server] {client_name} has left the chat.")
        print(f"[-] {client_name} removed from chat")

    try:
        conn.close()
    except:
        pass


def main():
    """starts the server and listens for connections"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # SO_REUSEADDR so we can restart quickly without "address already in use" error
    # learned about this one the hard way lol
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((HOST, PORT))
    server.listen(5)

    print(f"Server started on {HOST}:{PORT}")
    print("Waiting for connections...")
    print("(press Ctrl+C to stop)\n")

    try:
        while True:
            conn, addr = server.accept()
            print(f"[*] New connection from {addr}")

            # start a new thread for each client so they dont block each other
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

    except KeyboardInterrupt:
        print("\n\nShutting down server...")

    # close everything
    with lock:
        for name in clients:
            try:
                clients[name].close()
            except:
                pass
        clients.clear()

    server.close()
    print("Server stopped.")


if __name__ == "__main__":
    main()
