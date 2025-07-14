# ====== Import Modules
import secrets
import dictionary
import time
from message_parser import MessageParser, MessageType

# Initialize message parser
message_parser = MessageParser(verbose_mode=dictionary.verbose_mode)

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

# ====== Message Processing with New Parser
def process_message(raw_message: str, sender_ip: str) -> None:
    """
    Process incoming message using the new message parser
    """
    # Update parser verbose mode if it changed
    message_parser.verbose_mode = dictionary.verbose_mode
    
    # Parse the message
    parsed_message = message_parser.parse_message(raw_message, sender_ip)
    
    # Handle PROFILE messages for peer discovery
    if parsed_message.message_type == MessageType.PROFILE:
        handle_profile_message(parsed_message)
    
    # Print the formatted message
    formatted_output = message_parser.format_message_output(parsed_message, dictionary.peer_profiles)
    print(formatted_output)
    
    # Debug output for invalid messages
    if not parsed_message.is_valid:
        print(f">> [WARNING] Invalid message received from {sender_ip}\n")
        if dictionary.verbose_mode:
            print(parsed_message.to_debug_string())

def handle_profile_message(message):
    user_id = message.fields.get("USER_ID")
    display_name = message.fields.get("DISPLAY_NAME")
    status = message.fields.get("STATUS", "")
    
    if user_id and display_name:
        # Validate IP matches USER_ID
        try:
            claimed_ip = user_id.split('@')[1]
            if claimed_ip != message.sender_ip:
                print(f">> [WARNING] IP mismatch: USER_ID claims {claimed_ip} but sent from {message.sender_ip}")
                return
        except IndexError:
            print(f">> [WARNING] Invalid USER_ID format: {user_id}")
            return
        
        # Check if this is a new peer or existing peer
        if user_id in dictionary.peer_profiles:
            old_display_name, old_ip, old_status = dictionary.peer_profiles[user_id]
            
            # Note: old_ip should always equal message.sender_ip for valid messages
            name_changed = display_name != old_display_name
            status_changed = status != old_status
            
            if not name_changed and not status_changed:
                print(f">> [LOG] {display_name} ({user_id}) sent duplicate profile\n")
            else:
                changes = []
                if name_changed:
                    changes.append(f"name: '{old_display_name}' → '{display_name}'")
                if status_changed:
                    changes.append(f"status: '{old_status}' → '{status}'")
                
                change_desc = ", ".join(changes)
                print(f">> [LOG] {display_name} ({user_id}) updated profile ({change_desc})\n")
        else:
            print(f">> [LOG] New peer {display_name} ({user_id}) joined from IP {message.sender_ip}\n")
        
        # Update the peer profiles dictionary
        dictionary.peer_profiles[user_id] = (display_name, message.sender_ip, status)

# ====== Legacy functions (kept for backward compatibility)
def parse_profile_message(message):
    """Legacy function - kept for backward compatibility"""
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
    for user_id, (name, ip, status) in peer_profiles.items():
        print(f"{name} ({user_id}) @ {ip}: {status}")
    print("-------------------\n")

def print_saved_ip(peers_IP):
    print("--- Known IPs ---")
    for ip in peers_IP.keys():
        print(f"{ip}")
    print("-------------------\n")

# ====== Enhanced Functions for Message Management
def list_all_profiles():
    """List all stored profile messages"""
    profiles = message_parser.get_messages_by_type(MessageType.PROFILE)
    if not profiles:
        print("No profile messages found.\n")
        return
    
    print("\n--- All Profile Messages ---")
    for profile in profiles:
        display_name = profile.fields.get("DISPLAY_NAME", "Unknown")
        user_id = profile.fields.get("USER_ID", "Unknown")
        status = profile.fields.get("STATUS", "")
        timestamp = profile.timestamp
        print(f"[{time.ctime(timestamp)}] {display_name} ({user_id}): {status}")
    print("---------------------------\n")

def list_all_posts():
    """List all stored posts"""
    posts = message_parser.get_messages_by_type(MessageType.POST)
    if not posts:
        print("No posts found.\n")
        return
    
    print("\n--- All Posts ---")
    for post in posts:
        display_name = post.get_display_name(dictionary.peer_profiles)
        content = post.fields.get("CONTENT", "")
        timestamp = post.timestamp
        print(f"[{time.ctime(timestamp)}] {display_name}: {content}")
    print("-----------------\n")

def list_posts_by_user(user_id: str):
    """List all posts by a specific user"""
    posts = message_parser.get_posts_by_user(user_id)
    if not posts:
        print(f"No posts found for user {user_id}\n")
        return
    
    display_name = posts[0].get_display_name(dictionary.peer_profiles)
    print(f"\n--- Posts by {display_name} ---")
    for post in posts:
        content = post.fields.get("CONTENT", "")
        timestamp = post.timestamp
        print(f"[{time.ctime(timestamp)}] {content}")
    print("-" * (len(display_name) + 15) + "\n")

def list_dms_by_user(user_id: str):
    """List all DMs from a specific user"""
    dms = message_parser.get_dms_by_user(user_id)
    if not dms:
        print(f"No DMs found from user {user_id}\n")
        return
    
    display_name = dms[0].get_display_name(dictionary.peer_profiles)
    print(f"\n--- DMs from {display_name} ---")
    for dm in dms:
        content = dm.fields.get("CONTENT", "")
        timestamp = dm.timestamp
        print(f"[{time.ctime(timestamp)}] {content}")
    print("-" * (len(display_name) + 15) + "\n")

def get_message_statistics():
    """Get statistics about stored messages"""
    message_parser.print_all_messages_summary()

# ====== Legacy printing functions (kept for backward compatibility)
def print_message(message):
    print("\n============ >> PRINTING MESSAGE << ============\n")
    
    if dictionary.verbose_mode:
        vprint(message)
    else:
        nvprint(message)
    print("============= >> END OF MESSAGE << =============\n")

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
    print(f"\t{display_name}: {status}\n")

def print_post(message):
    user_id = None
    content = None
    lines = message.strip().split('\n')
    for line in lines:
        if line.startswith("USER_ID:"):
            user_id = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()
    
    if not user_id or not content:
        print("[POST] Invalid message format.")
        return
    
    display_name = user_id
    if user_id in dictionary.peer_profiles:
        display_name = dictionary.peer_profiles[user_id][0]
    
    print("[POST]")
    print(f"\tFrom: {display_name}")
    print(f"\tContent: {content}")
    print()

def print_dm(message):
    lines = message.strip().split('\n')
    from_id = None
    content = None
    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT:"):
            content = line.split(":", 1)[1].strip()
    
    if from_id in dictionary.peer_profiles:
        display_name = dictionary.peer_profiles[from_id][0]
    else:
        display_name = from_id
    print("[DM]")
    print(f"\t{display_name}: {content}")
    print()

def print_follow(message):
    lines = message.strip().split('\n')
    from_id = None
    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
            break
    if from_id:
        print("[FOLLOW]")
        print(f"\tUser {from_id} has followed you\n")

def print_unfollow(message):
    lines = message.strip().split('\n')
    from_id = None
    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
            break
    if from_id:
        print("[UNFOLLOW]")
        print(f"\tUser {from_id} has unfollowed you\n")

def print_file_offer(message):
    lines = message.strip().split('\n')
    from_id = None
    for line in lines:
        if line.startswith("FROM:"):
            from_id = line.split(":", 1)[1].strip()
            break
    if from_id:
        print("[FILE_OFFER]")
        print(f"\tUser {from_id} is sending you a file. Do you accept?\n")