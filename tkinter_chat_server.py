"""
Multi-client chat server with GUI broadcasts messages to all connected clients
"""

import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
import queue

# server config
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024

# 1024 seems fine for chat messages, but if you want to allow larger messages you can increase this
# BUFFER_SIZE = 2048


class ChatServer:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Server")
        self.master.geometry("500x450")
        self.master.configure(bg="#f0f0f0")

        self.clients = {}  # name -> (socket, address)
        self.lock = threading.Lock()
        self.server_socket = None
        self.running = False
        self.msg_queue = queue.Queue()

        self.setup_gui()
        self.start_server()

        # check queue every 100ms for new messages to display
        self.master.after(100, self.check_queue)
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        # title
        title = tk.Label(self.master, text="Chat Server",
                         font=("Arial", 16, "bold"), bg="#f0f0f0")
        title.pack(pady=5)

        # shows if server is running
        self.status_label = tk.Label(self.master, text="Status: Starting...",
                                     font=("Arial", 10), fg="orange",
                                     bg="#f0f0f0")
        self.status_label.pack()

        # log area
        self.log_area = scrolledtext.ScrolledText(
            self.master, wrap=tk.WORD, width=55, height=20,
            state='disabled', font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=10)

        # client count
        self.clients_label = tk.Label(self.master, text="Connected clients: 0",
                                      font=("Arial", 9), bg="#f0f0f0")
        self.clients_label.pack()

    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # so the accept loop can check self.running
            self.running = True

            self.log(f"Server started on {HOST}:{PORT}")
            self.log("Waiting for connections...")

            # start accepting connections in background
            t = threading.Thread(target=self.accept_loop, daemon=True)
            t.start()

            self.status_label.config(text="Status: Running", fg="green")

        except Exception as e:
            self.log(f"ERROR starting server: {e}")
            self.status_label.config(text="Status: Error", fg="red")

    def log(self, msg):
        """puts a message in the queue so the gui can show it"""
        self.msg_queue.put(msg)

    def accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                self.log(f"New connection from {addr}")

                # new thread for each client
                t = threading.Thread(target=self.handle_client,
                                     args=(conn, addr), daemon=True)
                t.start()

            except socket.timeout:
                continue
            except OSError:
                break
            except:
                if self.running:
                    self.log("Error accepting connection")
                break

    def handle_client(self, conn, addr):
        client_name = None
        try:
            # first message should be their name
            name_data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if not name_data:
                conn.close()
                return

            client_name = name_data.strip()
            # print(f"DEBUG: got name = {client_name}")

            with self.lock:
                self.clients[client_name] = (conn, addr)

            self.log(f"{client_name} has joined the chat! ({addr})")

            # tell everyone
            self.broadcast(f"[Server] {client_name} has joined the chat!",
                          skip=client_name)

            # update count label
            with self.lock:
                n = len(self.clients)
            self.msg_queue.put(f"##COUNT##{n}")

            # main receive loop
            while self.running:
                try:
                    data = conn.recv(BUFFER_SIZE).decode('utf-8')
                    if not data:
                        break  # disconnected

                    # print(f"DEBUG: {client_name} says: {data}")

                    msg = f"{client_name}: {data}"
                    self.log(f"[Broadcast] {msg}")
                    self.broadcast(msg)

                except socket.timeout:
                    continue
                except ConnectionResetError:
                    self.log(f"Connection reset by {client_name}")
                    break
                except Exception as e:
                    self.log(f"Error receiving from {client_name}: {e}")
                    break

        except Exception as e:
            self.log(f"Error in handle_client: {e}")

        # cleanup
        try:
            conn.close()
        except:
            pass

        if client_name:
            with self.lock:
                if client_name in self.clients:
                    del self.clients[client_name]

            self.log(f"{client_name} has left the chat.")
            self.broadcast(f"[Server] {client_name} has left the chat.")

            with self.lock:
                n = len(self.clients)
            self.msg_queue.put(f"##COUNT##{n}")

    def broadcast(self, message, skip=None):
        """send message to all connected clients"""
        with self.lock:
            # had to use dict instead of list here because of index issues
            for name in list(self.clients.keys()):
                if name == skip:
                    continue
                sock = self.clients[name][0]
                try:
                    sock.sendall(message.encode('utf-8'))
                except:
                    self.log(f"Couldnt send to {name}")
                    # let the receive loop handle removing them

    def check_queue(self):
        """checks queue and updates GUI"""
        while not self.msg_queue.empty():
            try:
                msg = self.msg_queue.get_nowait()

                if msg.startswith("##COUNT##"):
                    count = msg.replace("##COUNT##", "")
                    self.clients_label.config(text=f"Connected clients: {count}")
                else:
                    self.log_area.config(state='normal')
                    self.log_area.insert(tk.END, msg + "\n")
                    self.log_area.see(tk.END)
                    self.log_area.config(state='disabled')
            except queue.Empty:
                break

        if self.running:
            self.master.after(100, self.check_queue)

    def on_closing(self):
        self.running = False

        # close all client sockets
        with self.lock:
            for name in self.clients:
                try:
                    self.clients[name][0].close()
                except:
                    pass
            self.clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatServer(root)
    root.mainloop()
