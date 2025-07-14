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
    get_message_statistics
)

class LSNPPeer:
    """
    Decentralized LSNP Peer implementation
    Each peer can send and receive messages using only port 50999 as per RFC
    No message storage - messages are processed and displayed immediately
    """

    PORT = 50999  # Per RFC
    BROADCAST_IP = '255.255.255.255'  # Will be used as (BROADCAST_IP, PORT)

    def __init__(self, username=None, display_name=None):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

        try:
            self.sock.bind(('', self.PORT))
        except OSError as e:
            print(f"Error binding to port {self.PORT}: {e}")
            sys.exit(1)

        self.local_ip = self._get_local_ip()
        self.username = username or f"user_{self.local_ip.split('.')[-1]}"
        self.user_id = f"{self.username}@{self.local_ip}"
        self.display_name = display_name or self.username
        self.status = "Online"
        self.message_builder = MessageBuilder(self.user_id, self.display_name)

        self.known_peers = {}  # IP -> (user_id, display_name, last_seen)
        self.running = False

        print(f'===== >> LSNP Peer Active :: {self.display_name} ({self.user_id}) :: Port {self.PORT} << =====\n')

    def _get_local_ip(self):
        """Get the local IP address"""
        try:
            with socket(AF_INET, SOCK_DGRAM) as temp_sock:
                temp_sock.connect(("8.8.8.8", 80))
                return temp_sock.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def start(self):
        """Start the peer - begins listening and discovery"""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        threading.Thread(target=self._discovery_loop, daemon=True).start()
        self.broadcast_profile()
        print("Peer started successfully.\nType 'help' for available commands.\n")

    def _listen_loop(self):
        """Main listening loop - processes incoming messages"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                message = data.decode('utf-8', errors='ignore')

                # Skip messages from self
                if addr[0] == self.local_ip and self.user_id in message:
                    continue

                # Log the IP and process the message
                log_IP(addr[0])
                print("\n============ >> MESSAGE RECEIVED << ============\n")
                
                # Process message (this will parse and display it)
                parsed_message = process_message(message, addr[0])
                
                print("============= >> END OF MESSAGE << =============\n")

                if parsed_message is None:
                    print(f"Error: Could not parse message from {addr[0]}. Skipping ACK.")
                    self._update_peer_discovery(addr[0]) # Still update discovery even if message is bad
                    continue # Skip to the next iteration of the loop

                # Send ACK only if the message is NOT an ACK itself and has a message ID
                msg_type = parsed_message.message_type # Use the parsed message type
                msg_id = parsed_message.fields.get("MESSAGE_ID") # Get message ID from parsed fields

                # Define message types that *do not* require an ACK
                # Add other control messages as needed (e.g., PING, PONG, PROFILE)
                no_ack_types = [
                    dictionary.MessageType.ACK.value, 
                    dictionary.MessageType.PING.value,
                    dictionary.MessageType.PROFILE.value
                    # dictionary.MessageType.REVOKE.value, # If REVOKE doesn't need ACK
                ]

                # Check if msg_id exists AND the message type is NOT in the no_ack_types list
                if msg_id and msg_type.value not in no_ack_types:
                    ack = self.message_builder.build_ack(msg_id, "RECEIVED")
                    self.sock.sendto(ack.encode(), (addr[0], self.PORT))
                    print(f"[DEBUG] Sent ACK for message ID: {msg_id}")

                # Update peer discovery
                self._update_peer_discovery(addr[0])

            except Exception as e:
                if self.running:
                    print(f"Error in listener: {e}")

    def _discovery_loop(self):
        """Discovery loop - broadcasts profile and cleans up stale peers"""
        while self.running:
            try:
                # Broadcast profile periodically
                self.broadcast_profile()
                
                # Clean up stale peers (not seen for 5 minutes)
                current_time = time.time()
                stale = [ip for ip, (_, _, last_seen) in self.known_peers.items() 
                        if current_time - last_seen > 300]
                
                for ip in stale:
                    del self.known_peers[ip]
                    print(f"Removed stale peer: {ip}")
                
                time.sleep(60)  # Broadcast every minute
                
            except Exception as e:
                if self.running:
                    print(f"Error in discovery loop: {e}")

    def _update_peer_discovery(self, peer_ip):
        """Update known peers based on received messages"""
        # Look up peer in global peer_profiles
        for user_id, (display_name, ip, status) in peer_profiles.items():
            if ip == peer_ip:
                self.known_peers[peer_ip] = (user_id, display_name, time.time())
                break

    def broadcast_profile(self):
        """Broadcast profile to all peers"""
        try:
            msg = self.message_builder.build_profile(self.status)
            self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
        except Exception as e:
            print(f"Error broadcasting profile: {e}")

    def send_message_to_peer(self, ip, message):
        """Send a message to a specific peer"""
        try:
            self.sock.sendto(message.encode(), (ip, self.PORT))
        except Exception as e:
            print(f"Error sending message to {ip}: {e}")

    def send_post(self, content):
        """Send a POST message to all known peers"""
        if not content.strip():
            print("Post content cannot be empty.")
            return
            
        msg = self.message_builder.build_post(content)
        
        # Send to all known peers, or broadcast if no peers known
        targets = self.known_peers if self.known_peers else {self.BROADCAST_IP: ("broadcast", "", time.time())}
        
        for ip in targets:
            self.send_message_to_peer(ip, msg)
            
        print(f"Post sent: {content}")

    def send_dm(self, target_user_id, content):
        """Send a DM to a specific user"""
        if not content.strip():
            print("DM content cannot be empty.")
            return
            
        # Find target user's IP
        target_ip = None
        for user_id, (display_name, ip, status) in peer_profiles.items():
            if user_id == target_user_id:
                target_ip = ip
                break
        
        if target_ip:
            msg = self.message_builder.build_dm(target_user_id, content)
            self.send_message_to_peer(target_ip, msg)
            print(f"DM sent to {target_user_id}: {content}")
        else:
            print(f"User {target_user_id} not found.")

    def send_follow(self, target_user_id):
        """Send a FOLLOW message to a specific user"""
        # Find target user's IP
        target_ip = None
        for user_id, (display_name, ip, status) in peer_profiles.items():
            if user_id == target_user_id:
                target_ip = ip
                break
        
        if target_ip:
            msg = self.message_builder.build_follow(target_user_id)
            self.send_message_to_peer(target_ip, msg)
            print(f"Follow request sent to {target_user_id}")
        else:
            print(f"User {target_user_id} not found.")

    def send_ping(self, target_ip=None):
        """Send a PING message"""
        msg = self.message_builder.build_ping()
        
        try:
            if target_ip:
                self.send_message_to_peer(target_ip, msg)
                print(f"Ping sent to {target_ip}")
            else:
                self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
                print("Ping broadcast sent")
        except Exception as e:
            print(f"Error sending ping: {e}")

    def handle_command(self, cmd):
        """Handle user commands"""
        parts = cmd.strip().split()
        if not parts:
            return
            
        cmd = parts[0].lower()

        if cmd == "peers":
            print_known_peers(peer_profiles)
            
        elif cmd == "ips":
            print_saved_ip(peers_IP)
            
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
                
        elif cmd == "discovered":
            if not self.known_peers:
                print("No peers discovered yet.")
            else:
                print("\n--- Discovered Peers ---")
                for ip, (uid, name, seen) in self.known_peers.items():
                    last_seen = time.strftime('%H:%M:%S', time.localtime(seen))
                    print(f"{ip} - {name} ({uid}) - Last seen: {last_seen}")
                print("------------------------")
                
        elif cmd == "info":
            print(f"\n--- Peer Information ---")
            print(f"User ID: {self.user_id}")
            print(f"Display Name: {self.display_name}")
            print(f"Local IP: {self.local_ip}")
            print(f"Status: {self.status}")
            print(f"Known Peers: {len(self.known_peers)}")
            print(f"Saved IPs: {len(peers_IP)}")
            print("------------------------")
            
        elif cmd == "verbose":
            dictionary.verbose_mode = not dictionary.verbose_mode
            utils_manager.update_verbose_mode()
            print(f"Verbose mode: {'ON' if dictionary.verbose_mode else 'OFF'}")
            
        elif cmd == "stats":
            get_message_statistics()
            
        elif cmd in ["exit", "quit"]:
            self.stop()
            sys.exit(0)
            
        elif cmd == "help":
            self.print_help()
            
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def print_help(self):
        """Print available commands"""
        print("\n=== LSNP Peer Commands ===")
        print("Network Commands:")
        print("  peers        - Show known peers")
        print("  ips          - Show saved IP addresses")
        print("  discovered   - Show discovered peers with timestamps")
        print("  ping [ip]    - Send ping (broadcast if no IP specified)")
        print("  broadcast    - Broadcast profile")
        print()
        print("Messaging Commands:")
        print("  post <msg>   - Send a post to all peers")
        print("  dm <user_id> <msg> - Send direct message")
        print("  follow <user_id>   - Send follow request")
        print()
        print("Status Commands:")
        print("  status [msg] - View or set status message")
        print("  info         - Show peer information")
        print("  stats        - Show message statistics")
        print()
        print("System Commands:")
        print("  verbose      - Toggle verbose mode")
        print("  help         - Show this help")
        print("  exit/quit    - Exit the peer")
        print("==========================\n")

    def stop(self):
        """Stop the peer"""
        self.running = False
        self.sock.close()
        print("Peer stopped.")

def main():
    """Main function - parse arguments and start peer"""
    username = None
    display_name = None
    
    # Parse command line arguments
    if "--username" in sys.argv:
        try:
            username = sys.argv[sys.argv.index("--username") + 1]
        except IndexError:
            print("Error: --username requires a value")
            sys.exit(1)
            
    if "--name" in sys.argv:
        try:
            display_name = sys.argv[sys.argv.index("--name") + 1]
        except IndexError:
            print("Error: --name requires a value")
            sys.exit(1)
            
    if "--verbose" in sys.argv:
        dictionary.verbose_mode = True

    # Create and start peer
    peer = LSNPPeer(username=username, display_name=display_name)
    peer.start()

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