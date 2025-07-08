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

# ------ mDNS Discovery
def parse_profile_message(message):
    lines = message.strip().split('\n')
    msg_type = None
    user_id = None
    display_name = None

    for line in lines:
        if line.startswith("TYPE:"):
            msg_type = line.split(":", 1)[1].strip()
        elif line.startswith("USER_ID:"):
            user_id = line.split(":", 1)[1].strip()
        elif line.startswith("DISPLAY_NAME:"):
            display_name = line.split(":", 1)[1].strip()

    if msg_type == "PROFILE" and user_id and display_name:
        return user_id, display_name
    return None, None

def print_known_peers(peer_profiles):
    print("\n--- Known Peers ---")
    for user_id, (name, ip) in peer_profiles.items():
        print(f"{name} ({user_id}) @ {ip}")
    print("-------------------\n")