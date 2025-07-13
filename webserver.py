# this is copied code from lab 5. i just put it here first for base

# ====== Import Modules
from socket import *
from utils import *
import sys  # In order to terminate the program
import threading
import dictionary

from dictionary import peers_IP, peer_profiles
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

# ====== Set Up
BROADCAST_IP = '<broadcast>' # will be used for PING or PROFILE

sock = socket(AF_INET, SOCK_DGRAM) # AF_INET means IPv4, SOCK_DGRAM means UDP
sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

PORT = 50999
sock.bind(('', PORT)) # bind to port 50999

# ====== Verbose Mode Support
if "--verbose" in sys.argv:
    dictionary.verbose_mode = True

# ====== Server Proper
print('===== >> LSNP is active << =====\n\n')

def server_loop():
    while True:
        try:
            data, addr = sock.recvfrom(65535) # 65535 is max packet size for UDP
            message = data.decode('utf-8', errors='ignore') # converts bytes to String

            # IP Address Log
            log_IP(addr[0])
            
            # Process message using new parser
            print("\n============ >> PROCESSING MESSAGE << ============\n")
            process_message(message, addr[0])
            print("============= >> END OF MESSAGE << =============\n")
            
            # Send ACK if message has MESSAGE_ID
            extracted_msg_id = extract_message_id(message)
            if extracted_msg_id:
                ack = f"TYPE: ACK\nSTATUS: RECEIVED\nMESSAGE_ID: {extracted_msg_id}\n\n"
                sock.sendto(ack.encode(), addr)

        except Exception as e:
            print(f"Error in server loop: {e}")
            sys.exit(1)

# start the server in a thread
threading.Thread(target=server_loop, daemon=True).start()

# ====== Enhanced Command Interface
def print_help():
    """Print available commands"""
    print("\n--- Available Commands ---")
    print("peers          - List known peers")
    print("ips            - List known IP addresses")
    print("posts          - List all posts")
    print("posts <user>   - List posts by specific user")
    print("dms <user>     - List DMs from specific user")
    print("stats          - Show message statistics")
    print("verbose        - Toggle verbose mode")
    print("help           - Show this help message")
    print("exit/quit      - Exit the program")
    print("-------------------------\n")

def handle_command(cmd: str):
    """Handle user commands"""
    cmd = cmd.strip().lower()
    parts = cmd.split()
    
    if not parts:
        return
    
    command = parts[0]
    
    if command == "peers":
        print_known_peers(peer_profiles)
        
    elif command == "ips":
        print_saved_ip(peers_IP)
        
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
            print("Usage: dms <user_id>")
            
    elif command == "stats":
        get_message_statistics()
        
    elif command == "verbose":
        dictionary.verbose_mode = not dictionary.verbose_mode
        print(f"Verbose mode: {'ON' if dictionary.verbose_mode else 'OFF'}")
        
    elif command == "help":
        print_help()
        
    elif command in ["exit", "quit"]:
        print("Exiting...")
        sys.exit(0)
        
    else:
        print(f"Unknown command: {command}")
        print("Type 'help' for available commands")

# ====== Main Input Loop
session = PromptSession()

print("LSNP Server is running. Type 'help' for available commands.")
print_help()

with patch_stdout():
    while True:
        try:
            cmd = session.prompt("> ")
            handle_command(cmd)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            print("\nExiting...")
            break