# this is copied code from lab 5. i just put it here first for base

# ====== Import Modiles
from socket import *
from utils import *
import sys  # In order to terminate the program
from dictionary import peers_IP, peer_profiles
import threading

# ====== Set Up
BROADCAST_IP = '<broadcast>' # will be used for PING or PROFILE

sock = socket(AF_INET, SOCK_DGRAM) # AF_INET means IPv4, SOCK_DGRAM means UDP
sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

PORT = 50999
sock.bind(('', PORT)) # bind to port 50999

# ====== Server Proper
print('===== >> LSNP is active << =====\n')

def print_known_peers():
    while True:
        cmd = input("Type 'peers' to list known peers:\n> ")
        if cmd.strip().lower() == "peers":
            print("\n--- Known Peers ---")
            for user_id, (name, ip) in peer_profiles.items():
                print(f"{name} ({user_id}) @ {ip}")
            print("-------------------\n")

threading.Thread(target=print_known_peers, daemon=True).start()

while True:
    try:
        data, addr = sock.recvfrom(65535) # 65535 is max packet size for UDP
        message = data.decode('utf-8', errors='ignore') # converts bytes to String

        # IP Address Log
        log_IP(addr[0], message)
        store_IP(addr[0])

        # handle PROFILE messages (mDNS-like behavior)
        user_id, display_name = parse_profile_message(message)
        if user_id and display_name:
            peer_profiles[user_id] = (display_name, addr[0])
            print(f">> [PROFILE] {display_name} ({user_id}) added/updated from IP {addr[0]}\n")

        extracted_msg_id = extract_message_id(message)
        if extracted_msg_id:
            ack = f"TYPE: ACK\nSTATUS: RECEIVED\nMESSAGE_ID: {extracted_msg_id}\n\n"
            sock.sendto(ack.encode(), addr)

    except Exception as e:
        print("Error:", e)