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
    """
    Decentralized LSNP Peer implementation
    Self-contained with internal peer management
    """
    PORT = 50999
    BROADCAST_IP = '255.255.255.255'
    
    def __init__(self, username=None, display_name=None, verbose=False):
        # Socket setup
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        
        try:
            self.sock.bind(('', self.PORT))
        except OSError as e:
            print(f"Error binding to port {self.PORT}: {e}")
            sys.exit(1)
        
        # Peer identity
        self.local_ip = self._get_local_ip()
        self.username = username or f"user_{self.local_ip.split('.')[-1]}"
        self.user_id = f"{self.username}@{self.local_ip}"
        self.display_name = display_name or self.username
        self.status = "Online"
        
        # Internal state management
        # user_id -> (IP, display_name, status, last_seen)
        self.known_peers = {} 
        self.known_ips = set()  # Set of all IPs we've seen
        self.running = False
        self.verbose = verbose
        
        # Message handling
        self.message_builder = MessageBuilder(self.user_id, self.display_name)
        self.message_parser = MessageParser(verbose_mode=self.verbose)
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'messages_sent': 0,
            'invalid_messages': 0
        }
        
        display_manager.print_startup_banner(self.display_name, self.user_id, self.PORT)
    
    def _get_local_ip(self):
        """Get the local IP address"""
        try:
            with socket(AF_INET, SOCK_DGRAM) as temp_sock:
                temp_sock.connect(("8.8.8.8", 80))
                return temp_sock.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def _log_ip(self, ip_address):
        """Log and store IP address - logging itself is now conditional on verbose"""
        if self.verbose:
            display_manager.log_received_message(ip_address)
        
        if ip_address not in self.known_ips:
            self.known_ips.add(ip_address)
            if self.verbose:
                display_manager.log_new_ip(ip_address)
    
    def _update_peer_info(self, user_id, display_name, ip, status=""):
        """Update peer information and log updates conditionally."""
        current_time = time.time()

        # Skip if it's our own user_id
        if user_id == self.user_id:
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
    
    def _get_peer_profiles_dict(self):
        """Convert internal peer storage to expected format for message parser"""
        return {
            user_id: (display_name, ip, status)
            for user_id, (display_name, ip, status, _) in self.known_peers.items()
        }

    
    def _clean_stale_peers(self):
        """Remove peers not seen for 5 minutes"""
        current_time = time.time()
        stale_users = [
            user_id for user_id, (_, _, _, last_seen) in self.known_peers.items()
            if current_time - last_seen > 300
        ]

        for user_id in stale_users:
            display_name, ip, _, _ = self.known_peers[user_id]
            del self.known_peers[user_id]
            if self.verbose:
                display_manager.log_debug(f"Removed stale peer: {display_name} ({user_id}) at {ip}")
    
    def start(self):
        """Start the peer"""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._discovery_loop, daemon=True).start()
        self.broadcast_profile()
        # Moved print_startup_complete to main function to ensure it's after threads start
    
    def _listen_loop(self):
        """Main listening loop"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')

                # Parse early to check if it's from self
                parsed_message = self.message_parser.parse_message(message, addr[0])
                if parsed_message is None:
                    self.stats['invalid_messages'] += 1
                    continue

                # Extract sender user_id from FROM or USER_ID
                sender_user_id = parsed_message.fields.get("FROM") or parsed_message.fields.get("USER_ID")

                # Skip message from self: same IP and same user ID
                if addr[0] == self.local_ip and sender_user_id == self.user_id:
                    continue

                self._log_ip(addr[0])

                # Process and ACK
                parsed_message = self._process_message(message, addr[0])
                if parsed_message is None:
                    continue

                msg_type = parsed_message.message_type
                msg_id = parsed_message.fields.get("MESSAGE_ID")

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


    def _discovery_loop(self):
        """Discovery loop - broadcasts profile and cleans up stale peers"""
        send_profile = True  # flip-flop toggle

        while self.running:
            try:
                if send_profile:
                    self.broadcast_profile()
                else:
                    self.send_ping()
                
                self._clean_stale_peers()
                send_profile = not send_profile  # flip for next iteration

            except Exception as e:
                if self.running:
                    print(f"Error in discovery loop: {e}")

            time.sleep(300)  # Alternate every minute
    
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
    
    def send_message_to_peer(self, ip, message):
        """Send a message to a specific peer"""
        try:
            self.sock.sendto(message.encode(), (ip, self.PORT))
            self.stats['messages_sent'] += 1
            if self.verbose: # Log message sent only in verbose
                display_manager.log_debug(f"Sent message to {ip}")
        except Exception as e:
            print(f"Error sending message to {ip}: {e}")
    
    def send_post(self, content):
        """Send a POST message to all known peers"""
        if not content.strip():
            print("Post content cannot be empty.")
            return

        msg = self.message_builder.build_post(content)

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
    
    def send_follow(self, target_user_id):
        """Send a FOLLOW message to a specific user"""
        target_ip = self._find_peer_ip(target_user_id)
        
        if target_ip:
            msg = self.message_builder.build_follow(target_user_id)
            self.send_message_to_peer(target_ip, msg)
            print(f"Follow request sent to {target_user_id}")
        else:
            print(f"User {target_user_id} not found.")
    
    def _find_peer_ip(self, user_id):
        """Find IP address for a given user ID"""
        peer = self.known_peers.get(user_id)
        return peer[1] if peer else None
    
    def send_ping(self, target_ip=None):
        """Send a PING message"""
        msg = self.message_builder.build_ping()
        
        try:
            if target_ip:
                self.send_message_to_peer(target_ip, msg)
                print(f"Ping sent to {target_ip}")
            else:
                self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
                self.stats['messages_sent'] += 1
                print("Ping broadcast sent")
            if self.verbose: # Log ping sent only in verbose
                display_manager.log_debug(f"Sent PING to {target_ip if target_ip else 'broadcast'}")
        except Exception as e:
            print(f"Error sending ping: {e}")
    
    def handle_command(self, cmd):
        """Handle user commands"""
        parts = cmd.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        if cmd == "peers":
            display_manager.print_known_peers(self.known_peers)
        elif cmd == "ips":
            display_manager.print_known_ips(self.known_ips)
        elif cmd == "post":
            content = ' '.join(parts[1:]) if len(parts) > 1 else ""
            self.send_post(content)
        elif cmd == "dm":
            if len(parts) > 2:
                target_user = parts[1]
                content = ' '.join(parts[2:])
                self.send_dm(target_user, content)
            else:
                print("Usage: dm <user_id> <message>")
        elif cmd == "follow":
            if len(parts) > 1:
                self.send_follow(parts[1])
            else:
                print("Usage: follow <user_id>")
        elif cmd == "ping":
            target_ip = parts[1] if len(parts) > 1 else None
            self.send_ping(target_ip)
        elif cmd == "broadcast":
            self.broadcast_profile()
            print("Profile broadcast sent")
        elif cmd == "status":
            if len(parts) > 1:
                self.status = ' '.join(parts[1:])
                self.broadcast_profile()
                print(f"Status updated to: {self.status}")
            else:
                print(f"Current status: {self.status}")
        elif cmd == "info":
            display_manager.print_peer_info(self.user_id, self.display_name, self.local_ip, 
                                            self.status, len(self.known_peers), len(self.known_ips), self.verbose)
        elif cmd == "verbose":
            self.verbose = not self.verbose
            self.message_parser.verbose_mode = self.verbose # Update parser's verbose mode
            print(f"Verbose mode: {'ON' if self.verbose else 'OFF'}")
        elif cmd == "stats":
            display_manager.print_statistics(self.stats, len(self.known_peers), len(self.known_ips))
        elif cmd in ["exit", "quit"]:
            self.stop()
            sys.exit(0)
        elif cmd == "help":
            display_manager.print_help()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")
    
    def stop(self):
        """Stop the peer"""
        self.running = False
        self.sock.close()
        print("Peer stopped.")

def main():
    """Main function - parse arguments and start peer"""
    username = None
    display_name = None
    verbose = False
    
    # Parse command line arguments
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