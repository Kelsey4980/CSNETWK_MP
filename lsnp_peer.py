import sys
import time
import threading
from socket import socket, AF_INET, SOCK_DGRAM

# Import the new modular components
from peer_network import PeerNetwork
from peer_cli import PeerCLI, parse_args

# Import existing project utilities
import dictionary
from message_builder import MessageBuilder
from utils import utils_manager, extract_message_id
from dictionary import peer_profiles

class LSNPPeer:
    """
    Application logic layer for a decentralized peer. This class coordinates
    network operations and user commands but does not handle them directly.
    """

    def __init__(self, port, username, display_name):
        self.local_ip = self._get_local_ip()
        self.port = port if port is not None else self._find_available_port()
        self.username = username or "user"
        self.display_name = display_name or f"User_{self.port}"
        self.user_id = f"{self.username}@{self.local_ip}"
        self.status = "Online"
        
        self.known_peers = {}  # IP -> (user_id, display_name, port, last_seen)
        self.message_builder = MessageBuilder(self.user_id, self.display_name)
        
        # The peer now uses the network layer instead of managing sockets directly
        self.network = PeerNetwork(self.local_ip, self.port)
        self._running = False

    def start(self):
        """Start the peer's network services and periodic tasks."""
        self._running = True
        # Start listening, providing callback methods to the network layer
        self.network.start_listening(
            on_comm_message=self._handle_comm_message,
            on_discovery_message=self._handle_discovery_message
        )
        
        # Start periodic discovery and cleanup in a separate thread
        discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        discovery_thread.start()

        print(f'===== >> LSNP Peer Active :: {self.display_name} ({self.user_id}) :: Port {self.port} << =====\n')
        self.broadcast_profile()

    def _handle_comm_message(self, data, addr):
        """Callback for handling messages on the communication port."""
        if addr[0] == self.local_ip and addr[1] == self.port:
            return  # Ignore self-sent messages
        
        message = data.decode('utf-8', errors='ignore')
        print("\n============ >> PROCESSING MESSAGE << ============\n")
        utils_manager.process_message(message, addr[0])
        print("============= >> END OF MESSAGE << =============\n\n")

        # Acknowledge the message if it has an ID
        msg_id = extract_message_id(message)
        if msg_id:
            ack = self.message_builder.build_ack(msg_id, "RECEIVED")
            self.network.send_message(ack, addr[0], addr[1])

    def _handle_discovery_message(self, data, addr):
        """Callback for handling messages on the discovery port."""
        message = data.decode('utf-8', errors='ignore')
        
        sender_user_id = None
        try:
            # Manually parse USER_ID to avoid processing our own broadcasts
            for line in message.split('\n'):
                if line.startswith("USER_ID:"):
                    sender_user_id = line.split(': ')[1].strip()
                    break
        except IndexError:
            return # Ignore malformed messages
        
        if sender_user_id == self.user_id:
            return # Ignore our own broadcasts

        # If the message is from localhost, but the user isn't us,
        # it's another local peer's localhost-specific broadcast.
        # We can safely ignore it because we'll get their main network broadcast.
        if addr[0] == '127.0.0.1':
            return # Silently ignore
        
        print("\n========== >> DISCOVERY MESSAGE << ==========\n")
        utils_manager.process_message(message, addr[0])
        print("=========== >> END OF DISCOVERY << ==========\n\n")
        self._update_peer_discovery(addr[0], addr[1])

    def _discovery_loop(self):
        """Periodically broadcasts profile and cleans up stale peers."""
        while self._running:
            time.sleep(30) # Wait 30 seconds between cycles
            self.broadcast_profile()
            self._cleanup_stale_peers()
            
    def broadcast_profile(self):
        """Builds and broadcasts this peer's profile on the discovery network."""
        profile_msg = self.message_builder.build_profile(self.status)
        self.network.broadcast_discovery(profile_msg)
        print("Profile broadcast sent.")

    def send_post(self, content):
        """Sends a post to all known peers."""
        post_msg = self.message_builder.build_post(content)
        if not self.known_peers:
            print("No known peers to send post to. Broadcast to find some.")
            return

        print(f"Sending post to {len(self.known_peers)} peer(s)...")
        for ip, peer_info in self.known_peers.items():
            target_port = peer_info[2]
            self.network.send_message(post_msg, ip, target_port)
        print(f"Post sent: {content}")

    def send_dm(self, target_username, content):
        """Sends a direct message to a specific user."""
        target_ip = None
        target_port = None
        
        # Find the target peer's IP and port from their username
        for ip, (user_id, _, port, _) in self.known_peers.items():
            username = user_id.split('@')[0]
            if username == target_username:
                target_ip = ip
                target_port = port
                break
        
        if not target_ip:
            print(f"User '{target_username}' not found in discovered peers.")
            return
            
        dm_msg = self.message_builder.build_dm(target_username, content)
        self.network.send_message(dm_msg, target_ip, target_port)
        print(f"DM sent to {target_username}.")

    def send_ping(self, target_ip=None):
        """Sends a ping message. Broadcasts if no target IP is given."""
        ping_msg = self.message_builder.build_ping()
        if target_ip:
            # Assume default communication port if not a known peer
            port = self.known_peers.get(target_ip, (None, None, self.port, None))[2]
            self.network.send_message(ping_msg, target_ip, port)
        else:
            self.network.broadcast_discovery(ping_msg)
        print("Ping sent.")

    def set_status(self, new_status):
        """Updates the peer's status and broadcasts the change."""
        self.status = new_status
        print(f"Status updated to: {self.status}")
        self.broadcast_profile() # Announce the new status immediately
        
    def stop(self):
        """Stops the peer and its network services gracefully."""
        if self._running:
            self._running = False
            self.network.stop()
            print("Peer stopped.")
            sys.exit(0)

    def is_running(self):
        """Checks if the peer's main loops should be active."""
        return self._running
        
    def _get_local_ip(self):
        """Determines the local IP address of the machine."""
        try:
            with socket(AF_INET, SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                print(f"[DEBUG] Local IP resolved to {ip}")
                return ip
        except Exception:
            print("[DEBUG] Could not determine local IP. Falling back to 127.0.0.1")
            return "127.0.0.1"

    def _find_available_port(self, start_port=51000, max_attempts=100):
        """Finds an available UDP port to bind to."""
        for port in range(start_port, start_port + max_attempts):
            if port == self.network.DISCOVERY_PORT:
                continue
            try:
                with socket(AF_INET, SOCK_DGRAM) as test_sock:
                    test_sock.bind(('', port))
                return port
            except OSError:
                continue
        raise RuntimeError("Could not find an available communication port.")

    def _update_peer_discovery(self, peer_ip, peer_port):
        """Updates the known_peers dictionary with information from a profile message."""
        # Find the full user_id from the globally accessible peer_profiles
        user_id = None
        display_name = "Unknown"
        for uid, (d_name, ip, status) in peer_profiles.items():
            if ip == peer_ip:
                user_id = uid
                display_name = d_name
                break
        
        if user_id:
            self.known_peers[peer_ip] = (user_id, display_name, self.port, time.time())
            print(f"[DEBUG] Discovered or updated peer: {display_name} ({user_id})")
        
    def _cleanup_stale_peers(self):
        """Removes peers that haven't been seen for 5 minutes."""
        current_time = time.time()
        stale_peers = [
            ip for ip, (_, _, _, last_seen) in self.known_peers.items()
            if current_time - last_seen > 300  # 5 minutes
        ]
        
        for ip in stale_peers:
            del self.known_peers[ip]
            print(f"Removed stale peer: {ip}")
        
    def print_discovered_peers(self):
        """Prints a formatted list of all discovered peers."""
        print(f"\n--- Discovered Peers ({len(self.known_peers)}) ---")
        if not self.known_peers:
            print("No peers discovered yet.")
        else:
            for ip, (user_id, display_name, port, last_seen) in self.known_peers.items():
                last_seen_str = time.strftime("%H:%M:%S", time.localtime(last_seen))
                print(f"  {display_name} ({user_id}) at {ip}:{port} - Last seen: {last_seen_str}")
        print("----------------------------\n")

    def print_info(self):
        """Prints detailed information about this peer."""
        print("\n--- Peer Information ---")
        print(f"  User ID: {self.user_id}")
        print(f"  Display Name: {self.display_name}")
        print(f"  Local IP: {self.local_ip}")
        print(f"  Communication Port: {self.port}")
        print(f"  Discovery Port: {self.network.DISCOVERY_PORT}")
        print(f"  Status: {self.status}")
        print(f"  Discovered Peers: {len(self.known_peers)}")
        print("------------------------\n")


# Main execution block that starts the application
if __name__ == "__main__":
    # 1. Parse command-line arguments
    args = parse_args()

    # 2. Create the main peer application instance
    peer = LSNPPeer(
        port=args.get("port"),
        username=args.get("username"),
        display_name=args.get("display_name")
    )

    # 3. Start the peer's networking and background tasks
    peer.start()
    
    # 4. Create the Command-Line Interface and pass it control of the peer
    cli = PeerCLI(peer)

    # 5. Run the user-facing command loop
    cli.run()
