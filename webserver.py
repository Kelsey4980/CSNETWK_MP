# this is copied code from lab 5. i just put it here first for base

# ====== Import Modules
from socket import *
from utils import *
import sys  # In order to terminate the program
import threading
import dictionary

from dictionary import peers_IP, peer_profiles
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

# ====== Set Up
BROADCAST_IP = '<broadcast>' # will be used for PING or PROFILE

sock = socket(AF_INET, SOCK_DGRAM) # AF_INET means IPv4, SOCK_DGRAM means UDP
sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

PORT = 50999
sock.bind(('', PORT)) # bind to port 50999

# ====== Verbose Mode Support
if "--verbose" in sys.argv:
    dictionary.verbose_mode = True

# ====== Server Proper
print('===== >> LSNP is active << =====\n\n')

def server_loop():
    while True:
        try:
            data, addr = sock.recvfrom(65535) # 65535 is max packet size for UDP
            message = data.decode('utf-8', errors='ignore') # converts bytes to String

            # IP Address Log
            log_IP(addr[0])

            # handle PROFILE messages (mDNS-like behavior)
            user_id, display_name = parse_profile_message(message)
            if user_id and display_name:
                peer_profiles[user_id] = (display_name, addr[0])
                print(f">> [LOG] {display_name} ({user_id}) added/updated from IP {addr[0]}\n")

            # print any incoming messages
            print_message(message)

            extracted_msg_id = extract_message_id(message)
            if extracted_msg_id:
                ack = f"TYPE: ACK\nSTATUS: RECEIVED\nMESSAGE_ID: {extracted_msg_id}\n\n"
                sock.sendto(ack.encode(), addr)

        except Exception as e:
            print("Error:", e)
            sys.exit(1)

# start the server in a thread
threading.Thread(target=server_loop, daemon=True).start()

# main input loop with prompt_toolkit patch_stdout for safe async prints
session = PromptSession()
with patch_stdout():
    while True:
        try:
            cmd = session.prompt("Type 'peers' to list known peers:\n> ")
            if cmd.strip().lower() == 'peers':
                print_known_peers(peer_profiles)
                print_saved_ip(peers_IP)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            print("\nExiting...")
            break