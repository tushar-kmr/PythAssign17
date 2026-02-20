# Chat Application - Network Programming with Sockets

## What This Does

So this is my chat application project for the Network Programming module. It's basically a **multi-client chat app** where multiple people can connect and talk to each other in real time. I built it using Python's `socket` module for the networking part and `tkinter` for the GUI.

Every message you send gets **broadcasted** to all connected clients - so its like a group chat room.

Here's how it works basically:
1. You start the **server** first - it opens up a window that shows a log of everything happening (who connected, messages sent, etc.)
2. Then you open one or more **clients** - each client gets their own window where they can type a name, connect, and start chatting
3. Messages get sent to the server through sockets, and the server broadcasts them to everyone
4. Everything runs on threads so the GUI doesn't freeze while waiting for network stuff

## How to Set It Up

### What You Need
- **Python 3.x** (I used 3.11 but anything recent should work)
- That's it! Everything uses Python's built-in libraries:
  - `socket` - for the networking
  - `threading` - so the GUI doesn't freeze
  - `tkinter` - for the graphical interface
  - `queue` - for passing messages between threads safely

No need to `pip install` anything which is nice.

### Files
- `tkinter_chat_server.py` - The server that handles all the connections and broadcasts messages
- `tkinter_chat_client.py` - The client that users run to connect and chat

## How to Run It

**Step 1: Start the server first**
```
python tkinter_chat_server.py
```
A window will pop up showing the server log. It should say "Status: Running" in green.

**Step 2: Open a client (in a new terminal)**
```
python tkinter_chat_client.py
```
Type your name in the "Name" field and click **Connect**.

**Step 3: Open more clients** (each in their own terminal)
```
python tkinter_chat_client.py
```
Give each one a different name so you can tell them apart.

**Step 4: Start chatting!**
Just type a message and hit Enter or click Send - it goes to everyone connected.

**Important:** Always start the server before the clients, otherwise you'll get a connection refused error (I learned that the hard way lol).

## Challenges I Faced & How I Solved Them

### Challenge 1: The GUI Kept Freezing 😩

This one drove me CRAZY. When I first wrote the client, every time I connected to the server, the entire window would just freeze and become unresponsive. I couldn't type anything, couldn't click buttons, nothing.

It took me a while to figure out what was happening. Turns out, the `recv()` function is **blocking** - it just sits there waiting for data and won't let anything else run. So when I called it on the main thread, it basically hijacked the entire GUI.

The fix was using `threading`. I moved all the network receiving code into a separate background thread (a **daemon thread** specifically, so it dies when the main program closes). But then I hit ANOTHER problem - you can't update tkinter widgets from a background thread!! It would crash with some weird error about "main thread."

So I had to use a `queue.Queue()` as a middleman. The background thread puts messages into the queue, and then the main tkinter thread checks the queue every 100ms using `master.after()` and displays whatever it finds. It felt like such a roundabout way to do it but it works perfectly now and I actually understand why it has to be this way.

### Challenge 2: Clients Not Seeing Each Other's Messages At First 😅

When I first got multiple clients connecting, they could all connect fine but nobody could see each other's messages. Messages I sent just... disappeared into the void. The server was receiving them (I could see in the debug prints) but nothing was showing up on the other clients.

Turned out I had a really dumb bug in my broadcast function. I was originally storing clients in a **list** and when I tried to loop through and send to each one, I kept getting index errors because the list would change size when someone disconnected. Sometimes it would just skip clients entirely.

I switched to using a **dictionary** instead (`{name: (socket, address)}`) and added a `threading.Lock()` to protect it since multiple threads were reading/writing to it at the same time. My professor had talked about race conditions in the lecture and it suddenly clicked when I saw it happening in real time. After that fix, broadcasting worked perfectly and everyone could see each other's messages.

---

*This project was built as part of ASSIGNMENT 17 - Network Programming in Python Using Socket: Building A Chat Application.*
