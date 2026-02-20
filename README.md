# Chat Application - Network Programming with Sockets

## What This Does

This is my chat application for the Network Programming module. Its a **client-server chat app** where people can connect and talk to each other in real time. I used Python's `socket` module for the networking and `threading` for handling multiple clients.

How it works:
1. Start the **server** first - it runs in the terminal and logs everything (connections, messages, disconnects)
2. Open one or more **clients** in separate terminals - enter a name and start chatting
3. Messages get sent through sockets to the server, and the server broadcasts them to everyone else
4. Type **`bye`** to disconnect from the chat

## Setup

### Requirements
- **Python 3.x** (I used 3.11 but anything recent should be fine)
- No external packages needed, everything is built-in:
  - `socket` for networking
  - `threading` so things dont block each other

No need to pip install anything.

### Files
- `chat_server.py` - The server, handles connections and broadcasts messages
- `chat_client.py` - The client that users run to chat

## Running It

**1. Start server first**
```
python chat_server.py
```
Should print "Server started on 127.0.0.1:12345" and wait for connections.

**2. Open a client (new terminal)**
```
python chat_client.py
```
Enter your name when asked. You'll see a confirmation that you're connected.

**3. Open more clients if you want** (separate terminals)
```
python chat_client.py
```
Use different names so you can tell them apart.

**4. Chat!**
Type your message and press Enter. It gets sent to everyone.

**5. To leave the chat**
Type `bye` and press Enter. You'll be disconnected and everyone else will see that you left.

**Important:** start the server before clients or you get connection refused (learned that the hard way lol).

## Challenges I Had

### Threading confusion

When I first wrote the client, I tried to do receiving and sending in the same loop and it just didnt work. The `recv()` call blocks everything until data comes in, so I couldnt type while waiting for messages.

Fixed it by putting the receive code in a **background thread** (daemon thread so it stops when the program closes). That way the main thread handles input and the background thread handles incoming messages. Took me a bit to understand why I needed `daemon=True` though - without it the program wouldnt close properly when I typed bye.

### Messages not showing up for other clients

When I got multiple clients working, they connected fine but couldnt see each others messages. I could see in my debug prints that the server was getting them but nothing appeared on the other side.

The problem was in my broadcast function. I was using a **list** to store clients and looping through it to send, but the list kept changing size when people disconnected so I got index errors and it would skip clients sometimes.
Fixed it by switching to a **dictionary** (`{name: socket}`) and using `threading.Lock()` since multiple threads access it at the same time. Professor talked about race conditions in lecture and it finally made sense when I saw it happen for real. After that broadcasting worked fine.

### The 'bye' exit

Getting the `bye` command to work cleanly took some thought. I had to make sure both the client AND the server handle it properly. The client sends "bye", the server sees it, removes that client from the list, tells everyone they left, and the client closes its socket. Had to be careful about the order of operations here or it would crash with broken pipe errors.

---

## Bonus: GUI Version

I also made a more advanced version with a GUI using `tkinter`. If you want to try it:

- `tkinter_chat_server.py` - Server with a log window
- `tkinter_chat_client.py` - Client with full chat GUI (name entry, message display, send button)

The GUI version uses `queue.Queue()` for thread-safe message passing between the network thread and the tkinter main thread, which was actually pretty tricky to figure out. Its the same core functionality but wrapped in a nice interface.

---

*Assignment 17 - Network Programming in Python Using Socket: Building A Chat Application*
