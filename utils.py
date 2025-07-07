# ====== Import Modules
import secrets
import dictionary

# ====== Variables
peers_IP = dictionary.peers_IP

# ====== Functions
def generate_message_id(): # message ID generation
    return secrets.token_hex(8)

def extract_message_id(message): # extracts message ID
    for line in message.strip().split('\n'):
        if line.startswith("MESSAGE_ID:"):
            return line.split(':', 1)[1].strip()
    return None

def log_IP(ip_address, message):
    print(f"Received message from IP: {ip_address}\n")
    print(f"[RECV from {ip_address}]:\n{message}")

def store_IP(ip_address):
    if ip_address not in peers_IP:
        peers_IP[ip_address] = True

    print(f">> [LOG] Active IPs: {peers_IP}\n\n")