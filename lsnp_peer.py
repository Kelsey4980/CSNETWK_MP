# ====== Import Modules
from socket import *
import sys
import threading
import dictionary
import time
from message_builder import MessageBuilder
from dictionary import peers_IP, peer_profiles
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

# Import utils manager and functions
from utils import (
    utils_manager,
    generate_message_id,
    extract_message_id,
    log_IP,
    process_message,
    print_known_peers,
    print_saved_ip,
    list_all_profiles,
    list_all_posts,
    list_posts_by_user,
    list_dms_by_user,
    get_message_statistics
)

class LSNPPeer:
    """
    Decentralized LSNP Peer implementation
    Each peer can send and receive messages without a central server
    """
    
    # Use fixed ports for communication and discovery
    COMM_PORT = 51000
    DISCOVERY_PORT = 50999
    
    def __init__(self, username=None, display_name=None):
        # Set up discovery socket
        self.discovery_sock = socket(AF_INET, SOCK_DGRAM)
        self.discovery_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.discovery_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

        try:
            self.discovery_sock.bind(('', self.DISCOVERY_PORT))
        except OSError as e:
            print(f"Error binding discovery socket on port {self.DISCOVERY_PORT}: {e}")
            sys.exit(1)

        # Set up main socket for communication
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        
        try:
            self.sock.bind(('', self.COMM_PORT))
        except OSError as e:
            print(f"Error binding communication socket on port {self.COMM_PORT}: {e}")
            print("Another peer may be running on this machine. Please close it and try again.")
            sys.exit(1)
            
        # Get local IP first
        self.local_ip = self._get_local_ip()
        
        # Create user_id dynamically as username@ip_address
        self.username = username if username else f"user_{self.local_ip.split('.')[-1]}"
        self.user_id = f"{self.username}@{self.local_ip}"
        self.display_name = display_name if display_name else self.username
        self.status = "Online"
        
        # Message builder for sending messages
        self.message_builder = MessageBuilder(self.user_id, self.display_name)
        
        # Networking constants
        self.BROADCAST_IP = '<broadcast>'
        
        # Peer discovery - port is now constant, so no need to store it
        self.known_peers = {}  # IP -> (user_id, display_name, last_seen)
        self.running = False
        
        print(f'===== >> LSNP Peer Active :: {self.display_name} ({self.user_id}) :: Port {self.COMM_PORT} << =====\n')
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to a remote address to determine local IP
            with socket(AF_INET, SOCK_DGRAM) as temp_sock:
                temp_sock.connect(("8.8.8.8", 80))
                local_ip = temp_sock.getsockname()[0]
            print(f"[DEBUG] Local IP resolved to {local_ip}")
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def start(self):
        """Start the peer (listening and discovery)"""
        self.running = True
        
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._listen_discovery_loop, daemon=True).start()
        threading.Thread(target=self._discovery_loop, daemon=True).start()
        
        self.broadcast_profile()
        
        print(f"Peer started successfully on port {self.COMM_PORT}")
        print(f"Discovery running on port {self.DISCOVERY_PORT}")
        print("Type 'help' for available commands.\n")

    def _listen_loop(self):
        """Main listening loop for regular messages"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')
                
                # Skip messages from self
                if addr[0] == self.local_ip and addr[1] == self.COMM_PORT:
                    continue
                
                log_IP(addr[0])
                
                print("\n============ >> PROCESSING MESSAGE << ============\n")
                utils_manager.process_message(message, addr[0])
                print("============= >> END OF MESSAGE << =============\n\n")
                
                # Send ACK if message has MESSAGE_ID
                extracted_msg_id = extract_message_id(message)
                if extracted_msg_id:
                    ack = self.message_builder.build_ack(extracted_msg_id, "RECEIVED")
                    # Send ACK back to the communication port
                    self.sock.sendto(ack.encode(), (addr[0], self.COMM_PORT))
                    
            except Exception as e:
                if self.running:
                    print(f"Error in listen loop: {e}")
    
    def _listen_discovery_loop(self):
        """Listen for broadcasted profile messages on discovery port"""
        while self.running:
            try:
                data, addr = self.discovery_sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')

                sender_user_id = None
                try:
                    for line in message.split('\n'):
                        if line.startswith("USER_ID:"):
                            sender_user_id = line.split(': ')[1].strip()
                            break
                except IndexError:
                    continue # Ignore messages that can't be parsed

                if sender_user_id == self.user_id:
                    continue # Skip our own broadcast

                log_IP(addr[0])

                print("\n========== >> DISCOVERY MESSAGE << ==========\n")
                utils_manager.process_message(message, addr[0])
                print("=========== >> END OF DISCOVERY << ==========\n\n")

                self._update_peer_discovery(addr[0])

            except Exception as e:
                if self.running:
                    print(f"Error in discovery listen loop: {e}")
    
    def _update_peer_discovery(self, peer_ip):
        """Update peer discovery information"""
        print(f"[DEBUG] Attempting to match peer IP: {peer_ip}")
        print(f"[DEBUG] peer_profiles: {peer_profiles}")

        for user_id, (display_name, ip, status) in peer_profiles.items():
            if ip == peer_ip:
                self.known_peers[peer_ip] = (user_id, display_name, time.time())
                break
    
    def _discovery_loop(self):
        """Periodic peer discovery and maintenance"""
        while self.running:
            try:
                self.broadcast_profile()
                
                # Clean up old peers (not seen for 5 minutes)
                current_time = time.time()
                stale_peers = [
                    ip for ip, (_, _, last_seen) in self.known_peers.items()
                    if current_time - last_seen > 300  # 5 minutes
                ]
                
                for ip in stale_peers:
                    del self.known_peers[ip]
                    print(f"Removed stale peer: {ip}")
                
                time.sleep(60)  # Discovery every 60 seconds
                
            except Exception as e:
                if self.running:
                    print(f"Error in discovery loop: {e}")
    
    def broadcast_profile(self):
        """Broadcast profile to discover and announce to other peers"""
        try:
            profile_msg = self.message_builder.build_profile(self.status)
            self.discovery_sock.sendto(profile_msg.encode(), (self.BROADCAST_IP, self.DISCOVERY_PORT))
        except Exception as e:
            print(f"Error broadcasting profile: {e}")
    
    def send_message_to_peer(self, target_ip, message):
        """Send message to a specific peer on the fixed communication port"""
        try:
            self.sock.sendto(message.encode(), (target_ip, self.COMM_PORT))
            print(f"Message sent to {target_ip}:{self.COMM_PORT}")
        except Exception as e:
            print(f"Error sending message to {target_ip}: {e}")
    
    def send_post(self, content):
        """Send a post message to all known peers"""
        try:
            post_msg = self.message_builder.build_post(content)
            
            # Send to all known peers
            if self.known_peers:
                for peer_ip in self.known_peers.keys():
                    self.send_message_to_peer(peer_ip, post_msg)
            else:
                # If no known peers, broadcast to main port
                self.sock.sendto(post_msg.encode(), (self.BROADCAST_IP, self.COMM_PORT))
            
            print(f"Post sent: {content}")
            
        except Exception as e:
            print(f"Error sending post: {e}")
    
    def send_dm(self, target_user_id, content):
        """Send a direct message to a specific user"""
        target_ip = None
        for user_id, (_, ip, _) in peer_profiles.items():
            if user_id == target_user_id:
                target_ip = ip
                break
        
        if not target_ip:
            print(f"User {target_user_id} not found or is offline.")
            return
        
        try:
            dm_msg = self.message_builder.build_dm(target_user_id, content)
            self.send_message_to_peer(target_ip, dm_msg)
            print(f"DM sent to {target_user_id}: {content}")
        except Exception as e:
            print(f"Error sending DM: {e}")
    
    def send_follow(self, target_user_id):
        """Send follow request to a user"""
        target_ip = None
        for user_id, (_, ip, _) in peer_profiles.items():
            if user_id == target_user_id:
                target_ip = ip
                break
        
        if not target_ip:
            print(f"User {target_user_id} not found in known peers")
            return
        
        try:
            follow_msg = self.message_builder.build_follow(target_user_id)
            self.send_message_to_peer(target_ip, follow_msg)
            print(f"Follow request sent to {target_user_id}")
        except Exception as e:
            print(f"Error sending follow: {e}")

    def send_ping(self, target_ip=None):
        """Send ping to discover peers"""
        try:
            ping_msg = self.message_builder.build_ping()
            if target_ip:
                # Ping a specific peer on the communication port
                self.send_message_to_peer(target_ip, ping_msg)
            else:
                # Broadcast ping on discovery port to find everyone
                self.discovery_sock.sendto(ping_msg.encode(), (self.BROADCAST_IP, self.DISCOVERY_PORT))
            print("Ping sent")
        except Exception as e:
            print(f"Error sending ping: {e}")
            
    
    def handle_command(self, cmd: str):
        """Handle user commands"""
        cmd = cmd.strip()
        parts = cmd.split()
        
        if not parts:
            return
        
        command = parts[0].lower()
        
        if command == "peers":
            print_known_peers(peer_profiles)
            
        elif command == "ips":
            print_saved_ip(peers_IP)
        
        elif command == "profiles": 
            list_all_profiles()
            
        elif command == "posts":
            if len(parts) > 1:
                user_id = parts[1]
                list_posts_by_user(user_id)
            else:
                list_all_posts()
                
        elif command == "dms":
            if len(parts) > 1:
                user_id = parts[1]
                list_dms_by_user(user_id)
            else:
                print("Usage: dms <user_id>\n")
                
        elif command == "stats":
            get_message_statistics()
            
        elif command == "verbose":
            dictionary.verbose_mode = not dictionary.verbose_mode
            utils_manager.update_verbose_mode()  # Update the parser's verbose mode
            print(f"Verbose mode: {'ON' if dictionary.verbose_mode else 'OFF'}\n")
        
        elif command == "post":
            if len(parts) > 1:
                content = ' '.join(parts[1:])
                self.send_post(content)
            else:
                print("Usage: post <content>\n")
        
        elif command == "dm":
            if len(parts) > 2:
                target_user = parts[1]
                content = ' '.join(parts[2:])
                self.send_dm(target_user, content)
            else:
                print("Usage: dm <user_id> <content>\n")
        
        elif command == "follow":
            if len(parts) > 1:
                target_user = parts[1]
                self.send_follow(target_user)
            else:
                print("Usage: follow <user_id>\n")
        
        elif command == "ping":
            if len(parts) > 1:
                target_ip = parts[1]
                self.send_ping(target_ip)
            else:
                self.send_ping()
        
        elif command == "broadcast":
            self.broadcast_profile()
            print("Profile broadcast sent")
        
        elif command == "status":
            if len(parts) > 1:
                self.status = ' '.join(parts[1:])
                self.broadcast_profile()
                print(f"Status updated to: {self.status}")
            else:
                print(f"Current status: {self.status}")
        
        elif command == "discovered":
            print(f"\n--- Discovered Peers ({len(self.known_peers)}) ---")
            for ip, (user_id, display_name, port, last_seen) in self.known_peers.items():
                last_seen_str = time.strftime("%H:%M:%S", time.localtime(last_seen))
                print(f"  {ip}:{port} - {display_name} ({user_id}) - Last seen: {last_seen_str}")
            print("----------------------------\n")
        
        elif command == "info":
            print(f"Peer Info:")
            print(f"  User ID: {self.user_id}")
            print(f"  Display Name: {self.display_name}")
            print(f"  Local IP: {self.local_ip}")
            print(f"  Communication Port: {self.port}")
            print(f"  Discovery Port: {self.DISCOVERY_PORT}")
            print(f"  Status: {self.status}")
            print(f"  Known Peers: {len(self.known_peers)}")
            
        elif command == "help":
            self.print_help()
            
        elif command in ["exit", "quit"]:
            print("Shutting down peer...")
            self.stop()
            sys.exit(0)
            
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands\n")
    
    def print_help(self):
        """Print available commands"""
        print("\n--- Available Commands ---")
        print("peers          - List known peers")
        print("ips            - List known IP addresses")
        print("profiles       - List all profiles")
        print("posts          - List all posts")
        print("posts <user>   - List posts by specific user")
        print("dms <user>     - List DMs from specific user")
        print("stats          - Show message statistics")
        print("verbose        - Toggle verbose mode")
        print("post <content> - Send a post")
        print("dm <user> <msg>- Send direct message")
        print("follow <user>  - Follow a user")
        print("ping [ip]      - Send ping (broadcast if no IP)")
        print("broadcast      - Broadcast profile")
        print("status [msg]   - Set/show status")
        print("discovered     - Show discovered peers")
        print("info           - Show peer information")
        print("help           - Show this help message")
        print("exit/quit      - Exit the program")
        print("-------------------------\n")
    
    def stop(self):
        self.running = False
        try:
            self.sock.close()
            self.discovery_sock.close()
        except:
            pass
        print("Peer stopped.")

def main():
    """Main function to start the peer"""
    # Parse command line arguments for username and display name
    username = None
    display_name = None

    if "--username" in sys.argv:
        try:
            user_idx = sys.argv.index("--username")
            username = sys.argv[user_idx + 1]
        except IndexError:
            print("Invalid username specified")
            sys.exit(1)
    
    if "--name" in sys.argv:
        try:
            name_idx = sys.argv.index("--name")
            display_name = sys.argv[name_idx + 1]
        except IndexError:
            print("Invalid display name specified")
            sys.exit(1)
    
    if "--verbose" in sys.argv:
        dictionary.verbose_mode = True
    
    # Create and start peer (no port argument needed)
    peer = LSNPPeer(username=username, display_name=display_name)
    peer.start()
    
    session = PromptSession()
    
    with patch_stdout():
        while True:
            try:
                cmd = session.prompt("> ")
                peer.handle_command(cmd)
            except (KeyboardInterrupt, EOFError):
                print("\nShutting down...")
                peer.stop()
                break

if __name__ == "__main__":
    main()