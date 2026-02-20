"""
tkinter_chat_client.py
Chat client with GUI - connects to the chat server
all messages get broadcasted to everyone

this was honestly harder to write than the server lol
had to figure out the threading stuff for receiving messages
"""

import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import queue

# --- connection settings ---
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024


class ChatClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Client")
        self.master.geometry("500x500")
        self.master.configure(bg="#f0f0f0")

        self.client_socket = None
        self.connected = False
        self.username = None
        self.msg_queue = queue.Queue()

        self._setup_gui()

        # start checking queue for incoming messages
        self.master.after(100, self.process_queue)
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_gui(self):
        """builds all the gui widgets"""

        # --- connection frame at the top ---
        conn_frame = tk.Frame(self.master, bg="#f0f0f0")
        conn_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(conn_frame, text="Name:", bg="#f0f0f0",
                 font=("Arial", 10)).pack(side=tk.LEFT)

        self.name_entry = tk.Entry(conn_frame, width=15, font=("Arial", 10))
        self.name_entry.pack(side=tk.LEFT, padx=5)
        self.name_entry.insert(0, "User1")  # default name, user can change it

        self.connect_btn = tk.Button(conn_frame, text="Connect",
                                      command=self._connect_to_server,
                                      font=("Arial", 9), bg="#4CAF50", fg="white")
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        # status label
        self.status_label = tk.Label(conn_frame, text="Disconnected",
                                      font=("Arial", 9), fg="red", bg="#f0f0f0")
        self.status_label.pack(side=tk.RIGHT)

        # --- chat display area ---
        self.chat_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD,
                                                    width=55, height=20,
                                                    state='disabled',
                                                    font=("Consolas", 10))
        self.chat_area.pack(padx=10, pady=5)

        # setup text tags for different message types
        # figured this out from a stackoverflow answer lol
        self.chat_area.tag_config("server", foreground="#808080")   # gray for server messages
        self.chat_area.tag_config("normal", foreground="#000000")   # black for regular

        # --- message input area ---
        input_frame = tk.Frame(self.master, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        self.msg_entry = tk.Entry(input_frame, width=40, font=("Arial", 10))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", self._send_message)  # press enter to send

        self.send_btn = tk.Button(input_frame, text="Send",
                                   command=self._send_message,
                                   font=("Arial", 9), bg="#2196F3", fg="white")
        self.send_btn.pack(side=tk.RIGHT, padx=5)

        # help label at the bottom
        help_text = "Type a message and press Enter to send to everyone"
        help_label = tk.Label(self.master, text=help_text,
                               font=("Arial", 8), fg="#666666", bg="#f0f0f0")
        help_label.pack(pady=2)

    def _connect_to_server(self):
        """connects to the chat server"""
        if self.connected:
            # already connected, maybe disconnect?
            # TODO: add a disconnect button later
            return

        self.username = self.name_entry.get().strip()
        if not self.username:
            messagebox.showwarning("Oops", "Please enter a name!")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            self.connected = True

            # send username as the first message (for registration on server)
            self.client_socket.sendall(self.username.encode('utf-8'))

            # update gui
            self.status_label.config(text=f"Connected as {self.username}", fg="green")
            self.connect_btn.config(state='disabled')
            self.name_entry.config(state='disabled')

            self._display_message(f"Connected to server at {HOST}:{PORT}", "server")
            self._display_message(f"Your name: {self.username}", "server")
            self._display_message("---", "server")

            # start receiving messages in a background thread
            recv_thread = threading.Thread(target=self._receive_messages, daemon=True)
            recv_thread.start()

        except ConnectionRefusedError:
            messagebox.showerror("Connection Error",
                                  "Could not connect to server.\nMake sure the server is running!")
            self._cleanup_socket()
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")
            self._cleanup_socket()

    def _receive_messages(self):
        """
        runs in background thread, receives messages from server
        and puts them in the queue for the gui to display
        """
        while self.connected:
            try:
                data = self.client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    # server closed the connection
                    self.msg_queue.put(("__DISCONNECTED__", ""))
                    break

                # print(f"DEBUG received: {data}")  # for debugging

                # figure out the tag/color based on message content
                if data.startswith("[Server]"):
                    self.msg_queue.put((data, "server"))
                else:
                    self.msg_queue.put((data, "normal"))

            except ConnectionResetError:
                self.msg_queue.put(("__DISCONNECTED__", ""))
                break
            except OSError:
                # socket was closed
                break
            except Exception as e:
                # print(f"DEBUG receive error: {e}")
                if self.connected:
                    self.msg_queue.put((f"Error: {e}", "server"))
                break

    def _send_message(self, event=None):
        """sends a message to the server"""
        if not self.connected:
            # not connected yet, just ignore
            return

        message = self.msg_entry.get().strip()
        if not message:
            return  # dont send empty messages

        try:
            self.client_socket.sendall(message.encode('utf-8'))

            # show our own message in the chat
            self._display_message(f"You: {message}", "normal")

            # clear the input field
            self.msg_entry.delete(0, tk.END)

        except Exception as e:
            self._display_message(f"Failed to send message: {e}", "server")

    def _display_message(self, message, tag="normal"):
        """adds a message to the chat display area"""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, message + "\n", tag)
        self.chat_area.see(tk.END)  # scroll to bottom
        self.chat_area.config(state='disabled')

    def process_queue(self):
        """checks queue for new messages - called periodically by tkinter"""
        while not self.msg_queue.empty():
            try:
                msg, tag = self.msg_queue.get_nowait()

                if msg == "__DISCONNECTED__":
                    self._display_message("Disconnected from server.", "server")
                    self.connected = False
                    self.status_label.config(text="Disconnected", fg="red")
                    self.connect_btn.config(state='normal')
                    self.name_entry.config(state='normal')
                else:
                    self._display_message(msg, tag)

            except queue.Empty:
                break

        # keep checking
        self.master.after(100, self.process_queue)

    def _cleanup_socket(self):
        """cleans up the socket connection"""
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass  # dont care if close fails
            self.client_socket = None

    def _on_closing(self):
        """called when window is closed"""
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.master.destroy()


# --- main ---
if __name__ == "__main__":
    root = tk.Tk()
    client = ChatClient(root)
    root.mainloop()

# NOTE to self: if you get a weird error about "main thread" something
# its probably because youre updating tkinter from the wrong thread
# use the queue!! thats what its for
# - me, at 2am debugging this
