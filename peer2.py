# ====== Import Modules
from socket import *
import sys
import threading
import time
import secrets
from message_builder import MessageBuilder
from message_parser import MessageParser, MessageType
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import dictionary  # Only for verbose_mode and MessageType
from utils import display_manager, generate_message_id

class LSNPPeer:
    # ===== SET UP
    PORT = 50999
    BROADCAST_IP = '255.255.255.255'
    
    # ✅
    def __init__(self, username=None, display_name=None, verbose=False):
        # Socket setup ✅
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        
        try:
            self.sock.bind(('', self.PORT))
        except OSError as e:
            print(f"Error binding to port {self.PORT}: {e}")
            sys.exit(1)
        
        # Peer identity ✅
        self.local_ip = self._get_local_ip()
        self.username = username or f"user_{self.local_ip.split('.')[-1]}"
        self.user_id = f"{self.username}@{self.local_ip}"
        self.display_name = display_name or self.username
        self.status = "Online"
        
        # Internal state management ✅
        # user_id -> (IP, display_name, status, last_seen)
        self.known_peers = {}
        self.known_ips = set()
        self.following = set()
        self.followers = set()
        self.dms = {}
        self.running = False
        self.verbose = verbose
        
        # Message handling ✅
        self.message_builder = MessageBuilder(self.user_id, self.display_name)
        self.message_parser = MessageParser(verbose_mode=self.verbose)
        
        # Statistics ✅
        self.stats = {
            'messages_processed': 0,
            'messages_sent': 0,
            'invalid_messages': 0
        }
        
        display_manager.print_startup_banner(self.display_name, self.user_id, self.PORT)

    # ✅
    def _get_local_ip(self):
        """Get the local IP address"""
        try:
            with socket(AF_INET, SOCK_DGRAM) as temp_sock:
                temp_sock.connect(("8.8.8.8", 80))
                return temp_sock.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    # ✅
    def start(self):
        """Start the peer"""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        self.broadcast_profile()

    # ✅
    def stop(self):
        """Stop the peer"""
        self.running = False
        self.sock.close()
        print("Peer left.")

    # ✅
    def _listen_loop(self):
        """Main listening loop"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')

                # Parse early to check if it's from self ✅
                parsed_message = self.message_parser.parse_message(message, addr[0])
                if parsed_message is None:
                    self.stats['invalid_messages'] += 1
                    continue

                # Extract sender user_id from FROM or USER_ID ✅
                sender_user_id = parsed_message.fields.get("FROM") or parsed_message.fields.get("USER_ID")

                # Skip message from self: same IP and same user ID ✅
                # if addr[0] == self.local_ip and sender_user_id == self.user_id:
                if sender_user_id == self.user_id:
                    continue

                # Process and ACK 
                parsed_message = self._process_message(message, addr[0])
                if parsed_message is None:
                    continue

                msg_type = parsed_message.message_type
                msg_id = parsed_message.fields.get("MESSAGE_ID")

                # log the peers who made a broadcast
                print(parsed_message.fields)
                self._handle_log(parsed_message)

                no_ack_types = {
                    MessageType.ACK,
                    MessageType.PING,
                    MessageType.PROFILE 
                }

                if msg_id and msg_type not in no_ack_types:
                    ack = self.message_builder.build_ack(msg_id, "RECEIVED")
                    self.sock.sendto(ack.encode(), (addr[0], self.PORT))
                    if self.verbose:
                        display_manager.log_debug(f"Sent ACK for message ID: {msg_id}")

            except Exception as e:
                if self.running:
                    print(f"Error in listener: {e}")

    # TO DO: logging for verbose
    def _handle_log(self, parsed_message):
        msg_type = parsed_message.message_type
        if msg_type != MessageType.PROFILE:
            return

        msg_user_id = parsed_message.fields.get("USER_ID")
        msg_display_name = parsed_message.fields.get("DISPLAY_NAME")
        msg_status = parsed_message.fields.get("STATUS")
        msg_ip = msg_user_id.split("@", 1)[1]

        self._log_peer(msg_display_name, msg_user_id, msg_ip, msg_status)
        self._log_ip(msg_ip)

    # TO DO: logging for verbose
    def _log_peer(self, msg_display_name, msg_user_id, msg_ip, msg_status,):
        """Logs the peers that entered the server"""
        current_time = time.time

        if msg_user_id != self.user_id:
            self.known_peers[msg_user_id] = (msg_display_name, msg_ip, msg_status, current_time)

    # TO DO: logging for verbose
    def _log_ip(self, ip_address):
        """Log and store IP address - logging itself is now conditional on verbose"""
        if self.verbose:
            display_manager.log_received_message(ip_address)
        
        if ip_address not in self.known_ips:
            self.known_ips.add(ip_address)
            if self.verbose:
                display_manager.log_new_ip(ip_address)

    # ✅
    def _update_peer_info(self, user_id, display_name, ip, status=""):
        """Update peer information and log updates conditionally."""
        current_time = time.time()

        # Skip if it's our own user_id
        if user_id != self.user_id:
            self.known_peers[user_id] = (display_name, ip, status, current_time)
            return

        if user_id in self.known_peers:
            old_display_name, old_ip, old_status, _ = self.known_peers[user_id]

            name_changed = display_name != old_display_name
            status_changed = status != old_status
            ip_changed = ip != old_ip

            if name_changed or status_changed or ip_changed:
                if self.verbose:
                    display_manager.log_peer_update(
                        user_id, display_name, old_display_name, status, old_status, self.verbose
                    )
            elif self.verbose:
                display_manager.log_peer_update(
                    user_id, display_name, old_display_name, status, old_status, self.verbose
                )
        else:
            if self.verbose:
                display_manager.log_new_peer(display_name, user_id, ip)

        self.known_peers[user_id] = (display_name, ip, status, current_time)

    # ✅
    def _handle_profile_message(self, parsed_message):
        """Handle PROFILE messages for peer discovery"""
        user_id = parsed_message.fields.get("USER_ID")
        display_name = parsed_message.fields.get("DISPLAY_NAME")
        status = parsed_message.fields.get("STATUS", "")
        
        if not user_id or not display_name:
            if self.verbose:
                display_manager.log_warning(f"Invalid PROFILE message: missing USER_ID or DISPLAY_NAME from {parsed_message.sender_ip}")
            return
        
        # Validate IP matches USER_ID
        try:
            claimed_ip = user_id.split('@')[1]
            if claimed_ip != parsed_message.sender_ip:
                if self.verbose: # Log IP mismatch only in verbose
                    display_manager.log_warning(f"IP mismatch: USER_ID claims {claimed_ip} but sent from {parsed_message.sender_ip}")
                return
        except IndexError:
            if self.verbose: # Log invalid USER_ID format only in verbose
                display_manager.log_warning(f"Invalid USER_ID format: {user_id}")
            return
        
        self._update_peer_info(user_id, display_name, parsed_message.sender_ip, status)

    # ✅
    def _get_peer_profiles_dict(self):
        """Convert internal peer storage to expected format for message parser"""
        return {
            user_id: (display_name, ip, status)
            for user_id, (display_name, ip, status, _) in self.known_peers.items()
        }
    
    # ✅
    def _process_message(self, raw_message, sender_ip):
        """Process incoming message"""
        self.stats['messages_processed'] += 1
        
        # Parse the message
        parsed_message = self.message_parser.parse_message(raw_message, sender_ip)
        
        if parsed_message is None:
            self.stats['invalid_messages'] += 1
            # Debug log for parser failure is already handled by message_parser if verbose
            return None
        
        # Handle PROFILE messages for peer discovery (updates known_peers)
        if parsed_message.message_type == MessageType.PROFILE:
            self._handle_profile_message(parsed_message)
        
        # Display formatted output for valid messages
        formatted_output = self.message_parser.format_message_output(
            parsed_message, self._get_peer_profiles_dict(), self.verbose
        )

        if formatted_output.strip(): # Only print if there's actual content to display
            # Print general message header/footer only in verbose mode
            if self.verbose:
                display_manager.print_message_header()
                print(formatted_output)
                display_manager.print_message_footer()
            else:
                # In non-verbose, print direct messages (POST, DM, FOLLOW) without borders
                # The format_message_output should return empty string for silent types (ACK, PING, PROFILE)
                print(formatted_output)

        # Debug output for invalid messages
        if not parsed_message.is_valid and self.verbose:
            display_manager.log_warning(f"Invalid message received from {sender_ip} (validation failed after parsing).")
            print(parsed_message.to_debug_string())
        
        return parsed_message
    
    # ✅
    def broadcast_profile(self):
        """Broadcast profile to all peers"""
        try:
            msg = self.message_builder.build_profile(self.status)
            self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
            self.stats['messages_sent'] += 1
            if self.verbose: # Log broadcast profile only in verbose
                display_manager.log_debug(f"Broadcasted profile: {self.user_id}")
        except Exception as e:
            print(f"Error broadcasting profile: {e}")

    # ✅
    def _find_peer_ip(self, user_id):
        """Find IP address for a given user ID"""
        if "@" not in user_id:
            return user_id
        
        peer = self.known_peers.get(user_id)
        return peer[1] if peer else None
    
    # ✅
    def send_message_to_peer(self, user_id, message):
        """Send a message to a specific peer using their user_id"""
        # Look up the peer's IP address using the user_id
        target_ip = self._find_peer_ip(user_id)

        if target_ip:
            try:
                self.sock.sendto(message.encode(), (target_ip, self.PORT))
                self.stats['messages_sent'] += 1
                if self.verbose:  # Log message sent only in verbose mode
                    display_manager.log_debug(f"Sent message to {user_id} ({target_ip})")
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")
        else:
            print(f"User {user_id} not found in known peers.")

    # ✅
    def send_post(self, content):
        """Send a POST message to all known peers"""
        if not content.strip():
            print("Post content cannot be empty.")
            return

        msg = self.message_builder.build_post(content)

        # TO UPDATE for MS2 :: must be in followers
        peers_to_send_to = [uid for uid in self.known_peers if uid != self.user_id]
        if peers_to_send_to:
            for uid in peers_to_send_to:
                _, ip, _, _ = self.known_peers[uid]
                self.send_message_to_peer(ip, msg)
        else:  # If no other peers, broadcast
            self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
            self.stats['messages_sent'] += 1
            if self.verbose:
                display_manager.log_debug(f"Broadcasted POST: {content}")

        print(f"Post sent: {content}")

    # ✅
    def send_dm(self, target_user_id, content):
        """Send a DM to a specific user"""
        if not content.strip():
            print("DM content cannot be empty.")
            return
        
        # Find target user's IP
        target_ip = self._find_peer_ip(target_user_id)
        
        if target_ip:
            msg = self.message_builder.build_dm(target_user_id, content)
            self.send_message_to_peer(target_ip, msg)
            print(f"DM sent to {target_user_id}: {content}")
        else:
            print(f"User {target_user_id} not found.")

    # ✅ || TO UPDATE for MS2 :: make sure to update followers and following
    def send_follow(self, target_user_id):
        """Send a FOLLOW message to a specific user"""
        if target_user_id in self.following:
            print(f"You are already following {target_user_id}")
            return
        
        target_ip = self._find_peer_ip(target_user_id)

        if target_ip:
            msg = self.message_builder.build_follow(target_user_id)
            self.send_message_to_peer(target_ip, msg)
            self.following.add(target_user_id)  # Add to following set
            print(f"You are now following {target_user_id}")
        else:
            print(f"User {target_user_id} not found.")

    def send_ping(self, target_user_id=None):
        """Send a PING message to a specific user by user_id or broadcast if no user_id is provided"""
        if target_user_id:
            # Send ping to specific user by user_id
            msg = self.message_builder.build_ping()
            self.send_message_to_peer(target_user_id, msg)
            print(f"Ping sent to {target_user_id}")
        else:
            # If no user_id is provided, broadcast the ping
            msg = self.message_builder.build_ping()
            self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
            self.stats['messages_sent'] += 1
            print("Ping broadcast sent")

        if self.verbose:  # Log ping sent only in verbose mode
            display_manager.log_debug(f"Sent PING to {target_user_id if target_user_id else 'broadcast'}")

    def handle_command(self, cmd):
        """Handle user commands"""
        parts = cmd.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        # ✅
        if cmd == "peers":
            display_manager.print_known_peers(self.known_peers)
        # ✅
        elif cmd == "ips":
            display_manager.print_known_ips(self.known_ips)
        # ✅
        elif cmd == "post":
            content = ' '.join(parts[1:]) if len(parts) > 1 else ""
            self.send_post(content)
        # ✅
        elif cmd == "dm":
            if len(parts) > 2:
                target_user = parts[1]
                content = ' '.join(parts[2:])
                self.send_dm(target_user, content)
            else:
                print("Usage: dm <user_id> <message>")
        # ✅ 
        elif cmd == "follow":
            if len(parts) > 1:
                self.send_follow(parts[1])
            else:
                print("Usage: follow <user_id>")
        # ✅
        elif cmd == "ping":
            target_uid = parts[1] if len(parts) > 1 else None
            self.send_ping(target_uid)
        # ✅
        elif cmd == "broadcast":
            self.broadcast_profile()
            print("Profile broadcast sent")
        # ✅
        elif cmd == "status":
            if len(parts) > 1:
                self.status = ' '.join(parts[1:])
                self.broadcast_profile()
                print(f"Status updated to: {self.status}")
            else:
                print(f"Current status: {self.status}")
        # ✅
        elif cmd == "info":
            display_manager.print_peer_info(self.user_id, self.display_name, self.local_ip, 
                                            self.status, len(self.known_peers), len(self.known_ips), self.verbose)
        # ✅
        elif cmd == "following":
            display_manager.print_following_list(self.following)
        # ✅
        elif cmd == "verbose":
            self.verbose = not self.verbose
            self.message_parser.verbose_mode = self.verbose # Update parser's verbose mode
            print(f"Verbose mode: {'ON' if self.verbose else 'OFF'}")
        # ✅
        elif cmd == "stats":
            display_manager.print_statistics(self.stats, len(self.known_peers), len(self.known_ips))
        # ✅
        elif cmd in ["exit", "quit"]:
            self.stop()
            sys.exit(0)
        elif cmd == "help":
            display_manager.print_help()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            
def main():
    """Main function - parse arguments and start peer"""
    username = None
    display_name = None
    verbose = False
    
    # Parse command line arguments
    # run should be: python <file_name>.py --username <username> ---name <name>
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--username" and i + 1 < len(args):
            username = args[i + 1]
            i += 2
        elif args[i] == "--name" and i + 1 < len(args):
            display_name = args[i + 1]
            i += 2
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)
    
    # Create and start peer
    peer = LSNPPeer(username=username, display_name=display_name, verbose=verbose)
    peer.start() # Start threads and broadcast initial profile
    display_manager.print_startup_complete() # Print startup complete message AFTER peer starts
    
    # Interactive command loop
    session = PromptSession()
    with patch_stdout():
        while True:
            try:
                cmd = session.prompt("> ")
                peer.handle_command(cmd)
            except (KeyboardInterrupt, EOFError):
                peer.stop()
                break

if __name__ == "__main__":
    main()