# ====== Import Modules
import secrets
import dictionary

# ====== Functions
def generate_message_id(): # message ID generation
    return secrets.token_hex(8)

def extract_message_id(message): # extracts message ID
    for line in message.strip().split('\n'):
        if line.startswith("MESSAGE_ID:"):
            return line.split(':', 1)[1].strip()
    return None

def extract_message_type(message):
    for line in message.strip().split('\n'):
        if line.startswith("TYPE:"):
            return line.split(":", 1)[1].strip()
    return None

# ====== IP Log
def log_IP(ip_address):
    print(f">> [LOG] Received (RECV) message from IP: {ip_address}\n")
    store_IP(ip_address)

def store_IP(ip_address):
    if ip_address not in dictionary.peers_IP:
        dictionary.peers_IP[ip_address] = True
        print(f">> [LOG] New IP ({ip_address}) saved!\n")

# ====== mDNS Discovery
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

def print_saved_ip(peers_IP):
    print("--- Known IPs ---")
    for ip in peers_IP.items():
        print(f"{ip}")
    print("-------------------\n")

# ====== Printing
def print_message(message):
    print("\n============ >> PRINTING MESSAGE << ============\n\n")
    
    if (dictionary.verbose_mode):
        vprint(message)
    else:
        nvprint(message)

    print("============= >> END OF MESSAGE << =============\n\n")

def vprint(message):
    print(f"{message}")

def nvprint(message):
    incoming_type = extract_message_type(message)

    if incoming_type == "PROFILE":
        print_profile(message)
    elif incoming_type == "POST":
        print_post(message)
    elif incoming_type == "DM":
        print_dm(message)
    elif incoming_type == "FOLLOW":
        print_follow(message)
    elif incoming_type == "UNFOLLOW":
        print_unfollow(message)
    elif incoming_type == "FILE_OFFER":
        print_file_offer(message)

# ====== Individual printing for non-verbose
def print_profile(message):
    lines = message.strip().split('\n')
    status = None
    display_name = None 

    for line in lines:
        if line.startswith("DISPLAY_NAME:"):
            display_name = line.split(":", 1)[1].strip()
        elif line.startswith("STATUS:"):
            status = line.split(":", 1)[1].strip()

    print(f"[PROFILE]")
    print(f"\t{display_name}: {status}\n\n")

def print_post(message):
    user_id = None
    content = None

    # Parse lines
    lines = message.strip().split('\n')
    for line in lines:
        if line.startswith("USER_ID:"):
            user_id = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()

    # Default fallback if no content or user_id
    if not user_id or not content:
        print("[POST] Invalid message format.")
        return

    # Check if we have display name
    display_name = user_id
    if user_id in dictionary.peer_profiles:
        display_name = dictionary.peer_profiles[user_id][0]
    
    print("[POST]")
    print(f"\tFrom: {display_name}")
    print(f"\tContent: {content}")
    print("\n")

def print_dm(message):
    lines = message.strip().split('\n')
    from_id = None
    content = None

    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()

    # Check if we know the sender's display name
    if from_id in dictionary.peer_profiles:
        display_name = dictionary.peer_profiles[from_id][0]
    else:
        display_name = from_id

    print("[DM]")
    print(f"\t{display_name}: {content}")
    print("\n")

def print_follow(message):
    lines = message.strip().split('\n')
    from_id = None

    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
            break

    if from_id:
        print("[FOLLOW]")
        print(f"\tUser {from_id} has followed you\n\n")

def print_unfollow(message):
    lines = message.strip().split('\n')
    from_id = None

    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
            break

    if from_id:
        print("[UNFOLLOW]")
        print(f"\tUser {from_id} has unfollowed you\n\n")

def print_file_offer(message):
    lines = message.strip().split('\n')
    from_id = None

    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
            break

    if from_id:
        print("[FILE_OFFER]")
        print(f"\tUser {from_id} is sending you a file. Do you accept?\n\n")