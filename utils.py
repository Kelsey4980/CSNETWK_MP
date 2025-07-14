# ====== Import Modules
import secrets
import dictionary
import time
from message_parser import MessageParser, MessageType

class UtilsManager:
    """
    Manager class for LSNP utilities with encapsulated message parser
    """
    def __init__(self):
        self.message_parser = MessageParser(verbose_mode=dictionary.verbose_mode)
    
    def get_parser(self):
        """Get the message parser instance"""
        return self.message_parser
    
    def update_verbose_mode(self):
        """Update parser verbose mode to match dictionary setting"""
        self.message_parser.verbose_mode = dictionary.verbose_mode
    
    # ====== Message Processing
    def process_message(self, raw_message: str, sender_ip: str) -> None:
        """Process incoming message using the message parser"""
        self.update_verbose_mode()
        
        # Parse the message
        parsed_message = self.message_parser.parse_message(raw_message, sender_ip)
        
        # Handle PROFILE messages for peer discovery
        if parsed_message.message_type == MessageType.PROFILE:
            self._handle_profile_message(parsed_message)
        
        # Only print formatted output for valid messages or if verbose mode is on
        if parsed_message.is_valid or dictionary.verbose_mode:
            formatted_output = self.message_parser.format_message_output(parsed_message, dictionary.peer_profiles)
            if formatted_output.strip():
                print(formatted_output)
        
        # Debug output for invalid messages
        if not parsed_message.is_valid:
            print(f">> [WARNING] Invalid message received from {sender_ip}")
            if dictionary.verbose_mode:
                print(parsed_message.to_debug_string())
    
    def _handle_profile_message(self, message):
        """Handle PROFILE messages according to RFC specifications"""
        user_id = message.fields.get("USER_ID")
        print(f"[DEBUG] PROFILE handler was called for {user_id} from {message.sender_ip}")
        
        display_name = message.fields.get("DISPLAY_NAME")
        status = message.fields.get("STATUS", "")
        
        # Check if required fields are present
        if not user_id or not display_name:
            if dictionary.verbose_mode:
                print(f">> [WARNING] Invalid PROFILE message: missing USER_ID or DISPLAY_NAME from {message.sender_ip}")
            return
        
        # Validate IP matches USER_ID
        try:
            claimed_ip = user_id.split('@')[1]
            if claimed_ip != message.sender_ip:
                print(f">> [WARNING] IP mismatch: USER_ID claims {claimed_ip} but sent from {message.sender_ip} (will not be saved as a peer)\n")
                return
        except IndexError:
            print(f">> [WARNING] Invalid USER_ID format: {user_id} (will not be saved as a peer)\n")
            return
        
        # Update peer profiles
        if user_id in dictionary.peer_profiles:
            old_display_name, old_ip, old_status = dictionary.peer_profiles[user_id]
            
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
        
        dictionary.peer_profiles[user_id] = (display_name, message.sender_ip, status)
    
    # ====== Message History and Statistics
    def list_all_profiles(self):
        """List all stored profile messages"""
        profiles = self.message_parser.get_messages_by_type(MessageType.PROFILE)
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
    
    def list_all_posts(self):
        """List all stored posts"""
        posts = self.message_parser.get_messages_by_type(MessageType.POST)
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
    
    def list_posts_by_user(self, user_id: str):
        """List all posts by a specific user"""
        posts = self.message_parser.get_posts_by_user(user_id)
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
    
    def list_dms_by_user(self, user_id: str):
        """List all DMs from a specific user"""
        dms = self.message_parser.get_dms_by_user(user_id)
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
    
    def get_message_statistics(self):
        """Get statistics about stored messages"""
        self.message_parser.print_all_messages_summary()

# Create global instance
utils_manager = UtilsManager()

# ====== Utility Functions
def generate_message_id():
    """Generate a unique message ID"""
    return secrets.token_hex(8)

def extract_message_id(message):
    """Extract message ID from message"""
    for line in message.strip().split('\n'):
        if line.startswith("MESSAGE_ID:"):
            return line.split(':', 1)[1].strip()
    return None

def extract_message_type(message):
    """Extract message type from message"""
    for line in message.strip().split('\n'):
        if line.startswith("TYPE:"):
            return line.split(":", 1)[1].strip()
    return None

def get_message_parser():
    """Get the global message parser instance"""
    return utils_manager.get_parser()

# ====== IP Management
def log_IP(ip_address):
    """Log and store IP address"""
    print(f">> [LOG] Received (RECV) message from IP: {ip_address}\n")
    store_IP(ip_address)

def store_IP(ip_address):
    """Store IP address in known peers"""
    if ip_address not in dictionary.peers_IP:
        dictionary.peers_IP[ip_address] = True
        print(f">> [LOG] New IP ({ip_address}) saved!\n")

# ====== Message Processing Interface
def process_message(raw_message: str, sender_ip: str) -> None:
    """Process incoming message - delegates to utils_manager"""
    utils_manager.process_message(raw_message, sender_ip)

# ====== Message History Interface
def list_all_profiles():
    """List all stored profile messages"""
    utils_manager.list_all_profiles()

def list_all_posts():
    """List all stored posts"""
    utils_manager.list_all_posts()

def list_posts_by_user(user_id: str):
    """List all posts by a specific user"""
    utils_manager.list_posts_by_user(user_id)

def list_dms_by_user(user_id: str):
    """List all DMs from a specific user"""
    utils_manager.list_dms_by_user(user_id)

def get_message_statistics():
    """Get statistics about stored messages"""
    utils_manager.get_message_statistics()

# ====== Display Functions
def print_known_peers(peer_profiles):
    """Print all known peers"""
    print("\n--- Known Peers ---")
    for user_id, (name, ip, status) in peer_profiles.items():
        print(f"{name} ({user_id}) @ {ip}: {status}")
    print("-------------------\n")

def print_saved_ip(peers_IP):
    """Print all saved IP addresses"""
    print("\n--- Known IPs ---")
    for ip in peers_IP.keys():
        print(f"{ip}")
    print("-------------------\n")

# ====== Legacy Functions (for backward compatibility)
def handle_profile_message(message):
    """Legacy function - kept for backward compatibility"""
    utils_manager._handle_profile_message(message)

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