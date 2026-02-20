"""
tkinter_chat_server.py
Multi-client chat server - broadcasts messages to everyone
Built using sockets + threading + tkinter

I spent way too long getting this to work lol
the threading part was the hardest for me
"""

import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
import queue

# --- server config ---
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024

# i tried using 2048 at first but 1024 seems fine for chat messages
# BUFFER_SIZE = 2048


class ChatServer:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Server")
        self.master.geometry("500x450")
        self.master.configure(bg="#f0f0f0")

        # the clients dictionary - stores name -> (socket, address)
        self.clients = {}
        self.lock = threading.Lock()  # learned about this for thread safety
        self.server_socket = None
        self.running = False
        self.msg_queue = queue.Queue()

        self._setup_gui()
        self._start_server()

        # check queue every 100ms for new messages to display
        self.master.after(100, self.process_queue)
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_gui(self):
        """sets up all the tkinter widgets"""
        # title label
        title_label = tk.Label(self.master, text="Chat Server", font=("Arial", 16, "bold"),
                               bg="#f0f0f0")
        title_label.pack(pady=5)

        # status label - shows if server is running or not
        self.status_label = tk.Label(self.master, text="Status: Starting...",
                                      font=("Arial", 10), fg="orange", bg="#f0f0f0")
        self.status_label.pack()

        # the main log area
        self.log_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD,
                                                   width=55, height=20,
                                                   state='disabled',
                                                   font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=10)

        # connected clients count
        self.clients_label = tk.Label(self.master, text="Connected clients: 0",
                                       font=("Arial", 9), bg="#f0f0f0")
        self.clients_label.pack()

    def _start_server(self):
        """starts the server socket and begins accepting connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(5)
            # i had to set timeout so the accept loop can check self.running
            self.server_socket.settimeout(1.0)
            self.running = True

            self.msg_queue.put(f"Server started on {HOST}:{PORT}")
            self.msg_queue.put("Waiting for connections...")

            # start accept thread
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()

            # update status
            self.status_label.config(text="Status: Running", fg="green")

        except Exception as e:
            self.msg_queue.put(f"ERROR starting server: {e}")
            self.status_label.config(text="Status: Error", fg="red")

    def _accept_connections(self):
        """loop that accepts new client connections"""
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                self.msg_queue.put(f"New connection from {addr}")

                # start a new thread for each client
                client_thread = threading.Thread(target=self._handle_client,
                                                  args=(conn, addr), daemon=True)
                client_thread.start()

            except socket.timeout:
                continue  # just loop again and check if still running
            except OSError:
                # server socket was closed
                break
            except Exception as e:
                if self.running:
                    self.msg_queue.put(f"Accept error: {e}")
                break

    def _handle_client(self, conn, addr):
        """handles a single client connection - receives messages and routes them"""
        client_name = None
        try:
            # first message from client is their name
            name_data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if not name_data:
                conn.close()
                return

            client_name = name_data.strip()
            # print(f"DEBUG: client name = {client_name}")  # left this in for debugging

            # add to clients dict
            with self.lock:
                self.clients[client_name] = (conn, addr)

            self.msg_queue.put(f"{client_name} has joined the chat! ({addr})")

            # tell everyone that someone joined
            join_msg = f"[Server] {client_name} has joined the chat!"
            self._broadcast_message(join_msg, exclude_name=client_name)

            # update client count on gui
            self._update_client_count()

            # now keep receiving messages from this client
            while self.running:
                try:
                    data = conn.recv(BUFFER_SIZE).decode('utf-8')
                    if not data:
                        # client disconnected
                        break

                    # print(f"DEBUG: raw message from {client_name}: {data}")

                    # broadcast the message to everyone
                    broadcast_text = f"{client_name}: {data}"
                    self.msg_queue.put(f"[Broadcast] {broadcast_text}")
                    self._broadcast_message(broadcast_text)

                except socket.timeout:
                    continue
                except ConnectionResetError:
                    # client crashed or something
                    self.msg_queue.put(f"Connection reset by {client_name}")
                    break
                except Exception as e:
                    self.msg_queue.put(f"Error receiving from {client_name}: {e}")
                    break

        except Exception as e:
            self.msg_queue.put(f"Error in handle_client: {e}")

        finally:
            # cleanup - remove client and close connection
            self._remove_client(client_name, conn)

    def _broadcast_message(self, message, exclude_name=None):
        """sends message to ALL connected clients (except excluded one)"""
        with self.lock:
            # i originally had a list here and changed to dict, had to update this
            for name, (conn, addr) in self.clients.items():
                if name == exclude_name:
                    continue
                try:
                    conn.sendall(message.encode('utf-8'))
                except Exception as e:
                    self.msg_queue.put(f"Error broadcasting to {name}: {e}")
                    # dont remove here, let the receive loop handle it

    def _remove_client(self, client_name, conn):
        """removes a client from the dict and notifies others"""
        try:
            conn.close()
        except:
            pass  # already closed probably

        if client_name:
            with self.lock:
                if client_name in self.clients:
                    del self.clients[client_name]

            self.msg_queue.put(f"{client_name} has left the chat.")
            leave_msg = f"[Server] {client_name} has left the chat."
            self._broadcast_message(leave_msg)
            self._update_client_count()

    def _update_client_count(self):
        """updates the connected clients label"""
        with self.lock:
            count = len(self.clients)
        # cant update gui from thread directly, so put it in queue
        # actually wait, i can just use the label... hmm
        # gonna use queue to be safe
        self.msg_queue.put(f"__UPDATE_COUNT__{count}")

    def process_queue(self):
        """checks the queue and updates the GUI - runs on main thread"""
        while not self.msg_queue.empty():
            try:
                msg = self.msg_queue.get_nowait()

                # check if its a special count update message
                if msg.startswith("__UPDATE_COUNT__"):
                    count = msg.replace("__UPDATE_COUNT__", "")
                    self.clients_label.config(text=f"Connected clients: {count}")
                else:
                    # regular log message
                    self.log_area.config(state='normal')
                    self.log_area.insert(tk.END, msg + "\n")
                    self.log_area.see(tk.END)  # auto scroll to bottom
                    self.log_area.config(state='disabled')

            except queue.Empty:
                break

        # schedule next check
        if self.running:
            self.master.after(100, self.process_queue)

    def _on_closing(self):
        """called when the window is closed"""
        self.running = False

        # close all client connections
        with self.lock:
            for name, (conn, addr) in self.clients.items():
                try:
                    conn.close()
                except:
                    pass
            self.clients.clear()

        # close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        self.master.destroy()


# --- main ---
if __name__ == "__main__":
    root = tk.Tk()
    server = ChatServer(root)
    root.mainloop()
