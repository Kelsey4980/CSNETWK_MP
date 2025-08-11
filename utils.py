"""
    SUBMITTED BY:
        CHING, Justin
        CHUA, Hanielle
        KELSEY, Gabrielle
        TOLENTINO, Hephzi

    CSNETWK S15
"""

import secrets
import time
from typing import Optional, Dict, Set, Tuple
import base64, tempfile, os
import mimetypes

class DisplayManager:
    """
    Handles all display and logging functionality for LSNP Peer
    Separates presentation logic from core networking logic
    """
    
    def print_startup_banner(self, display_name: str, user_id: str, port: int):
        """Print startup banner"""
        print(f'===== >> LSNP Peer Active :: {display_name} ({user_id}) :: Port {port} << =====\n')
    
    def print_startup_complete(self):
        """Print startup completion message"""
        print("Peer started successfully.\nType 'help' for available commands.\n")
        print("------------\n")
    
    def log_received_message(self, ip_address: str):
        """Log received message"""
        print(f">> [LOG] Received (RECV) message from IP: {ip_address}") # Removed the extra newline
    
    def log_new_ip(self, ip_address: str):
        """Log new IP discovery"""
        print(f">> [LOG] New IP ({ip_address}) saved!") # Removed the extra newline
    
    def log_new_peer(self, display_name: str, user_id: str, ip: str):
        """Log new peer discovery"""
        print(f">> [LOG] New peer {display_name} ({user_id}) joined from IP {ip}") # Removed the extra newline
    
    def log_peer_update(self, user_id: str, display_name: str, old_display_name: str, 
                        status: str, old_status: str, verbose: bool):
        """Log peer profile updates"""
        name_changed = display_name != old_display_name
        status_changed = status != old_status
        
        if not name_changed and not status_changed:
            if verbose:
                print(f">> [LOG] {display_name} ({user_id}) sent duplicate profile") # Removed the extra newline
        else:
            changes = []
            if name_changed:
                changes.append(f"name: '{old_display_name}' → '{display_name}'")
            if status_changed:
                changes.append(f"status: '{old_status}' → '{status}'")
            
            change_desc = ", ".join(changes)
            print(f">> [LOG] {display_name} ({user_id}) updated profile ({change_desc})") # Removed the extra newline
    
    def log_warning(self, message: str):
        """Log warning message"""
        print(f">> [WARNING] {message}") # Removed the extra newline
    
    def log_debug(self, message: str):
        """Log debug message"""
        print(f">> [DEBUG] {message}")
    
    # Removed print_message_header and print_message_footer from here
    # They will be directly printed in lsnp_peer.py based on verbose mode
    def print_message_header(self):
        """Print message received header"""
        print("\n============ >> START OF MESSAGE << ============")
    
    def print_message_footer(self):
        """Print message received footer"""
        print("============= >> END OF MESSAGE << =============\n")
    
    def print_known_peers(self, known_peers: Dict[str, Tuple[str, str, str, float]]):
        """Print all known peers"""
        if not known_peers:
            print("\n--- No Known Peers ---")
            return

        print("\n--- Known Peers ---")
        for user_id, (display_name, _, _, ip, status, last_seen) in known_peers.items():
            last_seen_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_seen))
            status_text = f": {status}" if status else ""
            print(f"{display_name} ({user_id}) @ {ip}{status_text} | Last seen: {last_seen_str}")
        print("-------------------")

    def print_known_ips(self, known_ips: Set[str]):
        """Print all known IP addresses"""
        if not known_ips:
            print("\n--- No Known IPs ---")
            return
        
        print("\n--- Known IPs ---")
        for ip in sorted(known_ips):
            print(f"{ip}")
        print("-------------------")
    
    def print_peer_info(self, user_id: str, display_name: str, local_ip: str, 
                        status: str, known_peers_count: int, known_ips_count: int, verbose: bool):
        """Print peer information"""
        print(f"\n--- Peer Information ---")
        print(f"User ID: {user_id}")
        print(f"Display Name: {display_name}")
        print(f"Local IP: {local_ip}")
        print(f"Status: {status}")
        print(f"Known Peers: {known_peers_count}")
        print(f"Known IPs: {known_ips_count}")
        print(f"Verbose Mode: {'ON' if verbose else 'OFF'}")
        print("------------------------")
    
    def print_statistics(self, stats: Dict[str, int], known_peers_count: int, known_ips_count: int):
        """Print message statistics"""
        print("\n--- Message Statistics ---")
        print(f"Messages processed: {stats['messages_processed']}")
        print(f"Messages sent: {stats['messages_sent']}")
        print(f"Invalid messages: {stats['invalid_messages']}")
        print(f"Known peers: {known_peers_count}")
        print(f"Known IPs: {known_ips_count}")
        print("-------------------------\n")
    
    def print_help(self):
        """Print available commands"""
        print("\n=== LSNP Peer Commands ===")
        print("Network Commands:")
        print("  peers          - Show known peers")
        print("  ips            - Show saved IP addresses")
        print("  ping           - Broadcast ping")
        print("  profile        - Broadcast profile")
        print()
        print("Messaging Commands:")
        print("  post <msg>              - Send a post to all peers")
        print("  dm <user_id> <msg>      - Send direct message")
        print("  follow <user_id>        - Follow user")
        print("  unfollow <user_id>      - Unfollow user")
        print("  like <post_timestamp>   - Like a post of a followed user")
        print("  unlike <post_timestamp> - Revoke a like from a post of a followed user")
        print()
        print("Game Commands:")
        print("  tictactoe_invite <user_id> <symbol>    - Initiate a game of TicTacToe")
        print("  tictactoe_move <game_id> <position> <symbol>    - Send a game move")
        print("  tictactoe_result <game_id> <symbol>    - Announce the result of the game")
        print()
        print("Status Commands:")
        print("  status [msg] - View or set status message")
        print("  info         - Show peer information")
        print("  stats        - Show message statistics")
        print("  following    - List peers followed")
        print("  followers    - List peers following you")
        print("  ack_status   - Show pending ACKs") 
        print()
        print("File Transfer Commands:")
        print("  file_offer <user_id> <filepath> [description] - Offer file to user")
        print("  accept_file <file_id>                         - Accept file offer (auto-sends)")
        print("  reject_file <file_id>                         - Reject file offer")
        print("  file_transfers                                - List file transfers")
        print("  list_files                                    - List files in default directory")
        print()
        print("Group Commands:")
        print("  group_create <group_id> <group_name> <member1,member2,...>     - Create group")
        print("  group_message <group_id>|<group_creator> <content>             - Send group message")
        print("  group_update <group_id> -add <members> -remove <members>       - Update group")
        print("  group                                                          - List groups")
        print()
        print("System Commands:")
        print("  verbose      - Toggle verbose mode")
        print("  help         - Show this help")
        print("  exit/quit    - Exit the peer")
        print("==========================\n")

    def print_following_list(self, following):
        """List all users we're following"""
        if len(following) == 0:
            print("You're not following anyone yet")
            return
            
        print("You're following:")
        for user_id in following:
            print(f"  - {user_id}")

    def print_followers_list(self, followers):
        """List all users following us"""
        if len(followers) == 0:
            print("You don't have any followers yet")
            return

        print("Your followers:")
        for user_id in followers:
            print(f"  - {user_id}")

    def print_groups(self, groups):
        """List all groups"""
        if len(groups) == 0:
            print("You don't have any groups yet")
            return
        
        print("Your Groups:")
        for group_key, group_data in groups.items():
            print(f"Group Key: {group_key}")
            print(f"  ID     : {group_data['id']}")
            print(f"  Name   : {group_data['name']}")
            print(f"  Creator: {group_data['creator']}")
            print(f"  Members:")
            for member in group_data["members"]:
                print(f"    - {member}")

    def print_posts(self, post_self, post_others):
        """List all posts"""

        print("Your posts:")
        for post in post_self.items():
            print(f"Content: {post['content']}")
            print(f"Likes: {post['likes']}")

        print("\nPosts from others:")
        for post in post_others.items():
            print(f"Content: {post['content']}")
            print(f"From: {post['user_id']}")
            print(f"Likes: {post['likes']}")

    def load_avatar(self, path: str):
        with open(path, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode("utf-8")
            mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            return encoded, mime_type # avatar_data and avatar_type, respectively

    def show_avatar(self, avatar_data, avatar_type):
        img_bytes = base64.b64decode(avatar_data) # decode base64 to bytes

        ext = avatar_type.split("/")[-1] # gets file extension
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}").name # temporary file for image viewer to open

        with open(temp_path, "wb") as f: # puts the data into the file
            f.write(img_bytes)

        os.startfile(temp_path) # open in image viewer

# Create global display manager instance
display_manager = DisplayManager()