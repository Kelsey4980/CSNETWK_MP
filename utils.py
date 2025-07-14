# ====== Import Modules
import secrets
import dictionary
import time
from message_parser import MessageParser, MessageType, ParsedMessage
from typing import Optional

class UtilsManager:
    """
    Manager class for LSNP utilities with encapsulated message parser
    Focused on real-time message processing without storage
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
    def process_message(self, raw_message: str, sender_ip: str) -> Optional[ParsedMessage]:
        """Process incoming message using the message parser"""
        self.update_verbose_mode()

        # Parse the message
        parsed_message = self.message_parser.parse_message(raw_message, sender_ip)
        
        # --- NEW: Check if parsing failed immediately ---
        if parsed_message is None:
            # If the parser returned None, it means it was fundamentally unparseable.
            # We don't try to process it further in this function.
            # The calling peer will handle the "could not parse" error.
            if dictionary.verbose_mode:
                print(f">> [DEBUG - Utils] Message from {sender_ip} was not parsed successfully by MessageParser. Returning None.")
            return None
        # --- END NEW ---

        # Handle PROFILE messages for peer discovery
        # Now we can safely access parsed_message.message_type because it's not None
        if parsed_message.message_type == MessageType.PROFILE:
            self._handle_profile_message(parsed_message)
        
        # Only print formatted output for valid messages or if verbose mode is on
        if parsed_message.is_valid or dictionary.verbose_mode:
            formatted_output = self.message_parser.format_message_output(parsed_message, dictionary.peer_profiles)
            if formatted_output.strip():
                print(formatted_output)
        
        # Debug output for invalid messages (if is_valid is False but it wasn't None)
        # This condition is now redundant IF parse_message truly returns None for all invalid cases.
        # However, it's safer to keep it if there are "soft" invalidations where ParsedMessage object is still returned.
        # Based on your latest message_parser.py, it will return None for invalid, so this `if not parsed_message.is_valid`
        # block will likely not be hit anymore if the message *was* ParsedMessage and also invalid.
        # But for robustness, it doesn't hurt.
        if not parsed_message.is_valid and dictionary.verbose_mode: # Only print this if verbose
            print(f">> [WARNING] Invalid message received from {sender_ip} (validation failed after parsing).")
            print(parsed_message.to_debug_string())
        
        return parsed_message # Return the ParsedMessage object
    
    def _handle_profile_message(self, message):
        """Handle PROFILE messages according to RFC specifications"""
        user_id = message.fields.get("USER_ID")
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
def process_message(raw_message: str, sender_ip: str) -> Optional[ParsedMessage]:
    """Process incoming message - delegates to utils_manager"""
    return utils_manager.process_message(raw_message, sender_ip) # Ensure it returns what utils_manager.process_message returns

# ====== Statistics Functions (Real-time counters)
def get_message_statistics():
    """Get statistics about message processing"""
    parser = utils_manager.get_parser()
    
    print("\n--- Message Statistics ---")
    print(f"Messages processed this session: {parser.get_processed_count()}")
    print(f"Invalid messages received: {parser.get_invalid_count()}")
    print(f"Known peers: {len(dictionary.peer_profiles)}")
    print(f"Known IPs: {len(dictionary.peers_IP)}")
    print("-------------------------\n")

# ====== Display Functions
def print_known_peers(peer_profiles):
    """Print all known peers"""
    if not peer_profiles:
        print("\n--- No Known Peers ---\n")
        return
        
    print("\n--- Known Peers ---")
    for user_id, (name, ip, status) in peer_profiles.items():
        status_text = f": {status}" if status else ""
        print(f"{name} ({user_id}) @ {ip}{status_text}")
    print("-------------------\n")

def print_saved_ip(peers_IP):
    """Print all saved IP addresses"""
    if not peers_IP:
        print("\n--- No Known IPs ---\n")
        return
        
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