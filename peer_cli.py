import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
import dictionary
from utils import print_known_peers, print_saved_ip, list_all_profiles, list_all_posts, list_posts_by_user, list_dms_by_user, get_message_statistics

class PeerCLI:
    """Handles command-line input and user interaction."""

    def __init__(self, peer):
        self.peer = peer
        self.session = PromptSession()

    def handle_command(self, cmd: str):
        """Parses and handles user commands."""
        parts = cmd.strip().split()
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1:]

        command_map = {
            "peers": lambda: print_known_peers(dictionary.peer_profiles),
            "ips": lambda: print_saved_ip(dictionary.peers_IP),
            "profiles": list_all_profiles,
            "posts": lambda: list_posts_by_user(args[0]) if args else list_all_posts(),
            "dms": lambda: list_dms_by_user(args[0]) if args else print("Usage: dms <user_id>\n"),
            "stats": get_message_statistics,
            "post": lambda: self.peer.send_post(' '.join(args)) if args else print("Usage: post <content>\n"),
            "dm": lambda: self.peer.send_dm(args[0], ' '.join(args[1:])) if len(args) > 1 else print("Usage: dm <user_id> <message>\n"),
            "follow": lambda: self.peer.send_follow(args[0]) if args else print("Usage: follow <user_id>\n"),
            "ping": lambda: self.peer.send_ping(args[0] if args else None),
            "broadcast": self.peer.broadcast_profile,
            "status": lambda: self.peer.set_status(' '.join(args)) if args else print(f"Current status: {self.peer.status}"),
            "discovered": self.peer.print_discovered_peers,
            "info": self.peer.print_info,
            "help": self.print_help,
            "exit": self.peer.stop,
            "quit": self.peer.stop,
        }

        action = command_map.get(command)
        if action:
            action()
        else:
            print(f"Unknown command: {command}")

    def run(self):
        """Starts the main command loop for the user."""
        self.print_help()
        with patch_stdout():
            while self.peer.is_running():
                try:
                    cmd = self.session.prompt("> ")
                    self.handle_command(cmd)
                except (KeyboardInterrupt, EOFError):
                    print("\nShutting down...")
                    self.peer.stop()
                    break

    def print_help(self):
        """Prints the help message."""
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


def parse_args():
    """Parses command-line arguments."""
    args = {"port": None, "username": None, "display_name": None}
    # A more robust argument parser like argparse is recommended, but this works
    if "--port" in sys.argv:
        args["port"] = int(sys.argv[sys.argv.index("--port") + 1])
    if "--username" in sys.argv:
        args["username"] = sys.argv[sys.argv.index("--username") + 1]
    if "--name" in sys.argv:
        args["display_name"] = sys.argv[sys.argv.index("--name") + 1]
    if "--verbose" in sys.argv:
        dictionary.verbose_mode = True
    return args