"""
Simple chat client - connects to the server and lets you send/receive messages
Console based version (no GUI)
"""

import socket
import threading
import sys

# connection settings - same as the server
HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024


def receive_messages(sock):
    """runs in background thread, keeps printing messages from server"""
    while True:
        try:
            data = sock.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                print("\n[Disconnected from server]")
                break

            # print the message we got
            print(f"\n{data}")
            print("You: ", end="", flush=True)  # reprint prompt so it looks clean

        except ConnectionResetError:
            print("\n[Server closed the connection]")
            break
        except OSError:
            # socket was closed, just exit quietly
            break
        except Exception as e:
            print(f"\n[Error receiving: {e}]")
            break


def main():
    """connects to server and lets you chat"""

    print("=" * 40)
    print("  Simple Chat Client")
    print("=" * 40)

    # get username
    username = input("Enter your name: ").strip()
    if not username:
        print("Name cant be empty!")
        return

    # try to connect
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Could not connect to server!")
        print("Make sure the server is running first.")
        return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # send our name first - thats how the server knows who we are
    sock.sendall(username.encode('utf-8'))

    print(f"\nConnected to server at {HOST}:{PORT}")
    print(f"Your name: {username}")
    print("Type your messages below. Type 'bye' to exit.\n")
    print("-" * 40)

    # start receiving messages in background
    recv_thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    recv_thread.start()

    # main loop - read input and send messages
    try:
        while True:
            msg = input("You: ")
            msg = msg.strip()

            if msg == "":
                continue

            try:
                sock.sendall(msg.encode('utf-8'))
            except:
                print("[Failed to send message]")
                break

            # check if user wants to leave
            if msg.lower() == 'bye':
                print("\nGoodbye! Disconnecting...")
                break

    except KeyboardInterrupt:
        print("\n\nDisconnecting...")
    except EOFError:
        # happens if stdin is closed
        pass

    # cleanup
    try:
        sock.close()
    except:
        pass

    print("Disconnected from chat.")


if __name__ == "__main__":
    main()
