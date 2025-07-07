# this is copied code from lab 5. i just put it here first for base

# ====== Import Modiles
from socket import *
from utils import *
import sys  # In order to terminate the program

# ====== Set Up
BROADCAST_IP = '<broadcast>' # will be used for PING or PROFILE

sock = socket(AF_INET, SOCK_DGRAM) # AF_INET means IPv4, SOCK_DGRAM means UDP
sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

PORT = 50999
sock.bind(('', PORT)) # bind to port 50999

# ====== Server Proper
print('===== >> LSNP is active << =====\n')
while True:
    try:
        data, addr = sock.recvfrom(65535) # 65535 is max packet size for UDP
        message = data.decode('utf-8', errors='ignore') # converts bytes to String

        # IP Address Log
        log_IP(addr[0], message)
        store_IP(addr[0])

        extracted_msg_id = extract_message_id(message)
        if extracted_msg_id:
            ack = f"TYPE: ACK\nSTATUS: RECEIVED\nMESSAGE_ID: {extracted_msg_id}\n\n"
            sock.sendto(ack.encode(), addr)

    except Exception as e:
        print("Error:", e)