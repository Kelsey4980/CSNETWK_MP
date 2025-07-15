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

    def start(self):
        """Start the peer"""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        #threading.Thread(target=self._discovery_loop, daemon=True).start()

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

                # Skip message from self: same IP and same user ID
                if addr[0] == self.local_ip and sender_user_id == self.user_id:
                    continue

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