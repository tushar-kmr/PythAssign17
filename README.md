# Chat Application - Network Programming with Sockets

## What This Does

This is my chat application for the Network Programming module. Its a **multi-client chat app** where people can connect and talk to each other in real time. I used Python's `socket` module for the networking and `tkinter` for the GUI.

Messages get **broadcasted** to all connected clients so its basically a group chat room.

How it works:
1. Start the **server** first - it has a window that logs everything (connections, messages, etc)
2. Open one or more **clients** - each one has its own window where you type a name and connect
3. Messages go through sockets to the server, server sends them to everyone else
4. Uses threads so the GUI doesnt freeze while waiting for network stuff

## Setup

### Requirements
- **Python 3.x** (I used 3.11 but anything recent should be fine)
- No external packages needed, everything is built-in:
  - `socket` for networking
  - `threading` so things dont block
  - `tkinter` for the GUI
  - `queue` for thread-safe message passing

No need to pip install anything.

### Files
- `tkinter_chat_server.py` - The server, handles connections and broadcasts messages
- `tkinter_chat_client.py` - The client that users run to chat

## Running It

**1. Start server first**
```
python tkinter_chat_server.py
```
Window pops up with server log. Should say "Status: Running" in green.

**2. Open a client (new terminal)**
```
python tkinter_chat_client.py
```
Put your name in the Name field and click Connect.

**3. Open more clients if you want** (separate terminals)
```
python tkinter_chat_client.py
```
Use different names so you can tell them apart.

**4. Chat!**
Type and hit Enter or click Send. Goes to everyone.

**Important:** start the server before clients or you get connection refused (learned that the hard way lol).

## Challenges I Had

### The GUI kept freezing

This drove me crazy. When I first wrote the client, connecting to the server made the whole window freeze up. Couldnt type, couldnt click, nothing worked.
Took me a while to realize whats going on. `recv()` is a **blocking** call - it just waits for data and nothing else can run. When I had it on the main thread it basically took over the whole GUI.

Fixed it with `threading` - moved the receive code to a background thread (daemon thread so it stops when the program closes). But then I got errors because you cant update tkinter from a different thread. Something about "main thread" in the error message.
So I ended up using `queue.Queue()` as a middleman. Background thread puts messages in the queue, and the main thread checks it every 100ms with `master.after()` and displays whatever is there. Felt like a hacky workaround at first but it actually makes sense now and works well.

### Messages not showing up for other clients

When I got multiple clients working, they connected fine but couldnt see each others messages. I could see in my debug prints that the server was getting them but nothing appeared on the other side.

The problem was in my broadcast function. I was using a **list** to store clients and looping through it to send, but the list kept changing size when people disconnected so I got index errors and it would skip clients sometimes.
Fixed it by switching to a **dictionary** (`{name: (socket, address)}`) and using `threading.Lock()` since multiple threads access it at the same time. Professor talked about race conditions in lecture and it finally made sense when I saw it happen for real. After that broadcasting worked fine.

---

*Assignment 17 - Network Programming in Python Using Socket: Building A Chat Application*
