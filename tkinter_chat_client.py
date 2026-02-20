"""
Chat client - connects to the server and lets you send/receive messages
"""

import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
import queue

# connection settings
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024


class ChatClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Client")
        self.master.geometry("500x500")
        self.master.configure(bg="#f0f0f0")

        self.sock = None
        self.connected = False
        self.username = None
        self.msg_queue = queue.Queue()

        self.build_gui()

        self.master.after(100, self.check_incoming)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_gui(self):
        # top bar - name + connect button
        top = tk.Frame(self.master, bg="#f0f0f0")
        top.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top, text="Name:", bg="#f0f0f0",
                 font=("Arial", 10)).pack(side=tk.LEFT)

        self.name_entry = tk.Entry(top, width=15, font=("Arial", 10))
        self.name_entry.pack(side=tk.LEFT, padx=5)
        self.name_entry.insert(0, "User1")

        self.connect_btn = tk.Button(top, text="Connect",
                                     command=self.connect,
                                     font=("Arial", 9),
                                     bg="#4CAF50", fg="white")
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(top, text="Disconnected",
                                     font=("Arial", 9), fg="red",
                                     bg="#f0f0f0")
        self.status_label.pack(side=tk.RIGHT)

        # chat display
        self.chat_area = scrolledtext.ScrolledText(
            self.master, wrap=tk.WORD, width=55, height=20,
            state='disabled', font=("Consolas", 10))
        self.chat_area.pack(padx=10, pady=5)

        # different colors for server vs normal messages
        # found out how to do this from Google
        self.chat_area.tag_config("server", foreground="#808080")
        self.chat_area.tag_config("normal", foreground="#000000")

        # message input
        bottom = tk.Frame(self.master, bg="#f0f0f0")
        bottom.pack(fill=tk.X, padx=10, pady=5)

        self.msg_entry = tk.Entry(bottom, width=40, font=("Arial", 10))
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", self.send_msg)

        send_btn = tk.Button(bottom, text="Send", command=self.send_msg,
                             font=("Arial", 9), bg="#2196F3", fg="white")
        send_btn.pack(side=tk.RIGHT, padx=5)

        # little help text
        tk.Label(self.master, text="Type a message and press Enter to send",
                 font=("Arial", 8), fg="#666666", bg="#f0f0f0").pack(pady=2)

    def connect(self):
        if self.connected:
            return  # TODO: add disconnect button later maybe

        self.username = self.name_entry.get().strip()
        if not self.username:
            messagebox.showwarning("Oops", "Please enter a name!")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.connected = True

            # send our name first so the server knows who we are
            self.sock.sendall(self.username.encode('utf-8'))

            self.status_label.config(text=f"Connected as {self.username}", fg="green")
            self.connect_btn.config(state='disabled')
            self.name_entry.config(state='disabled')

            self.show_msg(f"Connected to server at {HOST}:{PORT}", "server")
            self.show_msg(f"Your name: {self.username}", "server")
            self.show_msg("---", "server")

            # background thread to receive messages
            t = threading.Thread(target=self.recv_loop, daemon=True)
            t.start()

        except ConnectionRefusedError:
            messagebox.showerror("Connection Error",
                                 "Could not connect to server.\nMake sure the server is running!")
            self.cleanup()
        except Exception as e:
            messagebox.showerror("Error", f"Connection failed: {e}")
            self.cleanup()

    def recv_loop(self):
        """receives messages from server in background thread"""
        while self.connected:
            try:
                data = self.sock.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    self.msg_queue.put(("__DC__", ""))
                    break

                # print(f"DEBUG got: {data}")

                if data.startswith("[Server]"):
                    self.msg_queue.put((data, "server"))
                else:
                    self.msg_queue.put((data, "normal"))

            except ConnectionResetError:
                self.msg_queue.put(("__DC__", ""))
                break
            except OSError:
                break
            except Exception as e:
                # print(f"DEBUG recv error: {e}")
                if self.connected:
                    self.msg_queue.put((f"Error: {e}", "server"))
                break

    def send_msg(self, event=None):
        if not self.connected:
            return

        message = self.msg_entry.get().strip()
        if message == "":
            return

        try:
            self.sock.sendall(message.encode('utf-8'))
            self.show_msg(f"You: {message}", "normal")
            self.msg_entry.delete(0, tk.END)
        except:
            self.show_msg("Failed to send message :(", "server")

    def show_msg(self, text, tag="normal"):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, text + "\n", tag)
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def check_incoming(self):
        """check for new messages from the recv thread"""
        while not self.msg_queue.empty():
            try:
                msg, tag = self.msg_queue.get_nowait()

                if msg == "__DC__":
                    self.show_msg("Disconnected from server.", "server")
                    self.connected = False
                    self.status_label.config(text="Disconnected", fg="red")
                    self.connect_btn.config(state='normal')
                    self.name_entry.config(state='normal')
                else:
                    self.show_msg(msg, tag)
            except queue.Empty:
                break

        self.master.after(100, self.check_incoming)

    def cleanup(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def on_close(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()

# NOTE to self: if you get a weird error about "main thread" something
# its because youre trying to update tkinter from the wrong thread
# use the queue!! thats what its there for