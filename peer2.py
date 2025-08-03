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
import dictionary  # Only for MessageType
from utils import display_manager

class LSNPPeer:
    # ====== CLASS CONSTANTS ======
    PORT = 50999
    BROADCAST_IP = '255.255.255.255'
    DISCOVERY_INTERVAL = 300
    
    # ====== INITIALIZATION ======
    def __init__(self, username=None, display_name=None, avatar_path=None, verbose=False):
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
        self.avatar_path = avatar_path
        self.display_name = display_name or self.username
        self.status = "Online"
        
        # Internal state management ✅
        # user_id -> (display_name, ip, status, last_seen)
        self.known_peers = {}
        self.known_ips = set()
        self.following = set()
        self.followers = set()
        self.posts = {} # posts you sent, used for storing likes
        self.received_posts = {} # posts you received, used for sending likes/unlikes
        self.groups = {} # group stored
        self.running = False
        self.verbose = verbose
        
        # Message handling ✅
        if self.avatar_path:
            avatar_data, avatar_type = display_manager.load_avatar(avatar_path) # for pfp
        else:
            avatar_data = None
            avatar_type = None

        self.message_builder = MessageBuilder(self.user_id, self.display_name, avatar_data, avatar_type)
        self.message_parser = MessageParser(verbose_mode=self.verbose)
        
        # Statistics ✅
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

    # ====== LIFECYCLE MANAGEMENT ======
    def start(self):
        """Start the peer"""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        self.broadcast_profile()

    def stop(self):
        """Stop the peer"""
        self.running = False
        self.sock.close()
        print("Peer left.")

    # ====== CORE LISTENING & PROCESSING ======
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
    
    def _process_message(self, raw_message, sender_ip):
        """Process incoming message"""
        self.stats['messages_processed'] += 1
        
        # Parse the message
        parsed_message = self.message_parser.parse_message(raw_message, sender_ip)
        
        if parsed_message is None:
            self.stats['invalid_messages'] += 1
            # Debug log for parser failure is already handled by message_parser if verbose
            return None
        
        # Handle different message types for peer discovery
        # Insert handlers for other message types here (e.g., for storage logic)
        if parsed_message.message_type == MessageType.PROFILE:
            self._handle_profile_message(parsed_message)
        elif parsed_message.message_type == MessageType.PING:
            self._handle_ping_message(parsed_message)
        elif parsed_message.message_type == MessageType.DM:
            self._handle_dm_message(parsed_message)
        elif parsed_message.message_type == MessageType.FOLLOW:
            self._handle_follow_message(parsed_message)
        elif parsed_message.message_type == MessageType.UNFOLLOW:
            self._handle_unfollow_message(parsed_message)
        elif parsed_message.message_type == MessageType.POST:
            self._handle_post_message(parsed_message)
        elif parsed_message.message_type == MessageType.LIKE:
            self._handle_likes(parsed_message)
        elif parsed_message.message_type == MessageType.UNLIKE:
            self._handle_unlikes(parsed_message)
        elif parsed_message.message_type == MessageType.GROUP_CREATE:
            self._handle_group_create(parsed_message)
        elif parsed_message.message_type == MessageType.GROUP_UPDATE:
            self._handle_group_update(parsed_message)


        # Update last seen for any message with user identification
        user_id = parsed_message.fields.get("FROM") or parsed_message.fields.get("USER_ID")
        if user_id:
            # Just update the timestamp for any message from a known peer
            self._update_peer_last_seen(user_id, sender_ip)
        
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

    # ====== PEER DISCOVERY & MANAGEMENT ======
    def _discovery_loop(self):
        """Discovery loop - broadcasts profile and pings, marks stale peers"""
        send_profile = True  # flip-flop toggle

        while self.running:
            try:
                if send_profile:
                    self.broadcast_profile()
                else:
                    self.broadcast_ping()  # Always broadcast ping in discovery
                
                self._mark_stale_peers()
                send_profile = not send_profile  # flip for next iteration

            except Exception as e:
                if self.running:
                    print(f"Error in discovery loop: {e}")

            time.sleep(self.DISCOVERY_INTERVAL)  # Alternate every 5 minutes

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

    def broadcast_ping(self):
        """Broadcast a PING message to all peers for discovery"""
        try:
            msg = self.message_builder.build_ping()
            self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
            self.stats['messages_sent'] += 1
            if self.verbose:
                display_manager.log_debug("Broadcasted discovery ping")
        except Exception as e:
            print(f"Error broadcasting ping: {e}")

    # TODO: Implement IF NEEDED
    def _mark_stale_peers(self):
        """Mark peers as stale if they haven't been seen recently"""
        """We can either just mark by updating status or remove from list"""
        # Note: This method is referenced but not implemented
        pass

    # ====== MESSAGE HANDLING ======
    def _handle_profile_message(self, parsed_message):
        """Handle PROFILE messages for peer discovery"""
        user_id = parsed_message.fields.get("USER_ID")
        display_name = parsed_message.fields.get("DISPLAY_NAME")
        status = parsed_message.fields.get("STATUS", "")
        avatar_data = parsed_message.fields.get("AVATAR_DATA", "")
        avatar_type = parsed_message.fields.get("AVATAR_TYPE", "")
        
        # Use shared validation
        if not self._validate_user_id_and_ip(user_id, parsed_message.sender_ip):
            return

        # Update peer info
        self._update_peer_info(user_id, display_name, avatar_data, avatar_type, parsed_message.sender_ip, status)

        # Log the IP address
        self._log_ip(parsed_message.sender_ip)
    
    def _handle_ping_message(self, parsed_message):
        """Handle PING messages for peer discovery"""
        user_id = parsed_message.fields.get("USER_ID")
        
        # Use shared validation
        if not self._validate_user_id_and_ip(user_id, parsed_message.sender_ip):
            return
        
        # Update peer ping info (preserves existing display_name and status)
        self._update_peer_ping(user_id, parsed_message.sender_ip)

        # Log the IP address
        self._log_ip(parsed_message.sender_ip)
    
    def _handle_dm_message(self, parsed_message):
        sender_id = (parsed_message.fields.get("FROM"))
        sender_ip = self._find_peer_ip(sender_id)
        sender_username = sender_id.split('@')[0]

        avatar_data = None
        avatar_type = None
        if sender_id in self.known_peers:
            _, avatar_data, avatar_type, _, _, _ = self.known_peers[sender_id]

        # Update peer info
        self._update_peer_info(sender_id, sender_username, avatar_data, avatar_type, sender_ip)
        # Log the IP address
        self._log_ip(sender_ip)
            
    def _handle_follow_message(self, parsed_message):
        """Accept a FOLLOW message from a specific user"""
        follower_to_add = parsed_message.fields.get("FROM")
        if follower_to_add:
            self.followers.add(follower_to_add)
            if not self._validate_user_id_and_ip(follower_to_add, parsed_message.sender_ip):
                return

            # Update peer ping info (preserves existing display_name and status)
            self._update_peer_ping(follower_to_add, parsed_message.sender_ip)

            # Log the IP address
            self._log_ip(parsed_message.sender_ip)
            if self.verbose:
                display_manager.log_debug(f"You have been followed by {follower_to_add}. They have been added to your "
                                          "followers list")
        else:
            if self.verbose:
                display_manager.log_warning(f"Invalid follow message from {parsed_message.sender_ip}")

    def _handle_unfollow_message(self, parsed_message):
        """Accept an UNFOLLOW message from a specific user"""
        follower_to_remove = parsed_message.fields.get("FROM")
        if follower_to_remove:
            self.followers.remove(follower_to_remove)
            if self.verbose:
                display_manager.log_debug(f"You have been unfollowed by {follower_to_remove}. They have been removed from your "
                                          "followers list")
        else:
            if self.verbose:
                display_manager.log_warning(f"Invalid unfollow message from {parsed_message.sender_ip}")

    # TODO: Check if correct. also might need to add the verbose stuff
    def _handle_post_message(self, parsed_message):
        '''Accept a POST message from a specific user'''
        current_time_with_ttl = parsed_message.fields.get("TOKEN").split("|")[1]  # gets 2nd part of token
        ttl = parsed_message.fields.get("TTL")
        current_time = float(current_time_with_ttl) - float(ttl)  # subtracts ttl from post time

        user_id = parsed_message.fields.get("USER_ID")
        content = parsed_message.fields.get("CONTENT")

        self.received_posts[current_time] = {
            "user_id": user_id,
            "content": content,
            "liking": False
        }

    # TODO: Check if correct. also might need to add the verbose stuff
    def _handle_likes(self, parsed_message):
        '''Accept a LIKE message from a specific user'''
        user_id = parsed_message.fields.get("FROM")
        post_timestamp = float(parsed_message.fields.get("POST_TIMESTAMP"))

        if user_id in self.followers:
            self.posts[post_timestamp]["likers"].add(user_id)
        else:
            print(f"User {user_id} is not following you.")

    # TODO: Check if correct. also might need to add the verbose stuff
    def _handle_unlikes(self, parsed_message):
        '''Accept an UNLIKE message from a specific user'''
        user_id = parsed_message.fields.get("FROM")
        post_timestamp = float(parsed_message.fields.get("POST_TIMESTAMP"))

        if user_id in self.followers:

            if user_id in self.posts[post_timestamp]["likers"]:
                self.posts[post_timestamp]["likers"].remove(user_id)
            else:
                print(f"User {user_id} has not liked this post.")

        else:
            print(f"User {user_id} is not following you.")

    # TODO: Check if correct. also might need to add the verbose stuff
    def _handle_group_create(self, parsed_message):
        """Accept a GROUP_CREATE message"""
        group_members = parsed_message.fields.get("MEMBERS")
        target_users = group_members.split(",")
        group_name = parsed_message.fields.get("GROUP_NAME")
        group_id = parsed_message.fields.get("GROUP_ID")
        group_creator = parsed_message.fields.get("FROM")

        # create a key for storage
        group_key = f"{group_id}|{group_creator}"

        if self.user_id in target_users:
            # if the group ID already exists in receipient's groups
            duplicate_id_found = any(group_data["id"] == group_id for group_data in self.groups.values())
            if duplicate_id_found:
                if self.verbose:
                    display_manager.log_warning(f"{group_creator} added you to a group with a duplicate group ID ({group_id})")
                
            # store the group details
            self.groups[group_key] = {
                "id": group_id,
                "name": group_name,
                "members": target_users,
                "creator": group_creator
            }

            # also updates the known peers
            self._save_group_peers(parsed_message)

            if self.verbose:
                display_manager.log_debug(f"You are added to the group '{group_name}'({group_id}) by {group_creator}")
        else:
            if self.verbose:
                display_manager.log_warning(f"You received a GROUP_CREATE for '{group_name}' ({group_id}) by {group_creator}, but you're not listed as a member")

    # TODO: Check if correct. also might need to add the verbose stuff
    def _handle_group_update(self, parsed_message):
        """Acept a GROUP_UPDATE message"""
        members_to_add = parsed_message.fields.get("ADD")
        members_to_remove = parsed_message.fields.get("REMOVE")
        group_id = parsed_message.fields.get("GROUP_ID")
        group_creator = parsed_message.fields.get("FROM") # assumes that the sender is also the creator

        group_key = f"{group_id}|{group_creator}"

        if group_key in self.groups:
            self._update_group(group_key, members_to_add, members_to_remove)
            group_name = self.groups[group_key]["name"]

            if self.verbose:
                display_manager.log_debug(f"'{group_name}' ({group_id}) updated its members")
        else:
            if self.verbose:
                display_manager.log_warning(f"You received a GROUP_UPDATE from {group_creator} to a group ({group_id}) you are not in")

    # ====== PEER INFORMATION MANAGEMENT ======
    def _validate_user_id_and_ip(self, user_id, sender_ip):
        """Shared validation logic for USER_ID format and IP matching"""
        if not user_id:
            if self.verbose:
                display_manager.log_warning(f"Missing USER_ID from {sender_ip}")
            return False
        
        # Validate IP matches USER_ID
        try:
            claimed_ip = user_id.split('@')[1]
            if claimed_ip != sender_ip:
                if self.verbose:
                    display_manager.log_warning(f"IP mismatch: USER_ID claims {claimed_ip} but sent from {sender_ip}")
                # [TO UPDATE] This portion is commented for testing purposes. Currently we are using VPN only, hence the IPs will
                # always be different.
                # return False
        except IndexError:
            if self.verbose:
                display_manager.log_warning(f"Invalid USER_ID format: {user_id}")
            return False
        
        return True

    def _update_peer_info(self, user_id, display_name, avatar_data, avatar_type, ip, status=""):
        """Update peer information and log updates conditionally."""
        current_time = time.time()

        # Skip if it's our own user_id
        if user_id == self.user_id:
            return

        if user_id in self.known_peers:
            old_display_name, _, _,old_ip, old_status, _ = self.known_peers[user_id]

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

        self.known_peers[user_id] = (display_name, avatar_data, avatar_type, ip, status, current_time)

    def _update_peer_ping(self, user_id, ip):
        """Update peer last seen time for PING messages, preserving existing info."""
        current_time = time.time()
        
        # Skip if it's our own user_id
        if user_id == self.user_id:
            return
        
        if user_id in self.known_peers:
            # Preserve existing display_name and status, update IP and timestamp
            old_display_name, old_ip, old_status, _ = self.known_peers[user_id]
            self.known_peers[user_id] = (old_display_name, ip, old_status, current_time)
            
            if self.verbose and ip != old_ip:
                display_manager.log_warning(f"IP changed for {user_id}: {old_ip} -> {ip}")
        else:
            # New peer with only USER_ID - store with minimal info
            # Use user_id part as temporary display name
            temp_display_name = user_id
            self.known_peers[user_id] = (temp_display_name, ip, "", current_time)
            
            if self.verbose:
                display_manager.log_new_peer(f"{temp_display_name} (ping only)", user_id, ip)

    def _update_peer_last_seen(self, user_id, ip):
        """Update just the last seen time for any message from a peer."""
        current_time = time.time()
        
        # Skip if it's our own user_id
        if user_id == self.user_id:
            return
        
        if user_id in self.known_peers:
            # Preserve existing info, just update timestamp and potentially IP
            old_display_name, old_ip, old_status, _ = self.known_peers[user_id]
            self.known_peers[user_id] = (old_display_name, ip, old_status, current_time)

    def _update_group(self, group_key, members_to_add, members_to_remove):
        # update locally for the sender
            group = self.groups.get(group_key)
            current_members = set(group["members"])

            # add
            for member in members_to_add:
                if member and member not in current_members:
                    current_members.add(member)
            # remove
            for member in members_to_remove:
                current_members.discard(member)

            # update
            self.groups[group_key]["members"] = list(current_members)

    def _log_ip(self, ip_address):
        """Log and store IP address - logging itself is now conditional on verbose"""
        if self.verbose:
            display_manager.log_received_message(ip_address)
        
        if ip_address not in self.known_ips:
            self.known_ips.add(ip_address)
            if self.verbose:
                display_manager.log_new_ip(ip_address)

    def _get_peer_profiles_dict(self):
        """Convert internal peer storage to expected format for message parser"""
        return {
            user_id: (display_name, ip, status)
            for user_id, (display_name, ip, status, _) in self.known_peers.items()
        }

    def _find_peer_ip(self, user_id):
        """Find IP address for a given user ID"""
        if "@" not in user_id:
            return user_id
        
        peer = self.known_peers.get(user_id)
        return peer[1] if peer else None
    
    def _save_group_peers(self, parsed_message):
        group_name = parsed_message.fields.get("GROUP_NAME")
        group_id = parsed_message.fields.get("GROUP_ID")

        # save sender
        sender_id = (parsed_message.fields.get("FROM"))
        sender_ip = self._find_peer_ip(sender_id)
        sender_username = sender_id.split('@')[0]

        self._update_peer_info(sender_id, sender_username, sender_ip)
        self._log_ip(sender_ip)

        # save groups
        group_members = parsed_message.fields.get("MEMBERS")
        target_users = group_members.split(",")

        for user in target_users:
            username = user.split("@")[0]
            ip_add = self._find_peer_ip(user)

            self._update_peer_info(user, username, ip_add)
            self._log_ip(ip_add)

        if self.verbose:
            display_manager.log_debug(f"Known peers updated with the members of '{group_name}' ({group_id})")

    # ====== MESSAGE SENDING ======
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

    def send_post(self, content, ttl_seconds: int = None):
        """Send a POST message to all known peers"""
        if not content.strip():
            print("Post content cannot be empty.")
            return

        msg = self.message_builder.build_post(content, ttl_seconds)
        parsed_msg = self.message_parser.parse_message(msg)
        current_time_with_ttl = parsed_msg.fields.get("TOKEN").split("|")[1] # gets 2nd part of token
        current_time = float(current_time_with_ttl) - float(ttl_seconds) # subtracts ttl from post time

        # TODO: check if correct
        peers_to_send_to = [uid for uid in self.followers if uid != self.user_id]
        if peers_to_send_to:
            for uid in peers_to_send_to:
                self.send_message_to_peer(uid, msg)
        else:  # If no other peers, broadcast
            self.sock.sendto(msg.encode(), (self.BROADCAST_IP, self.PORT))
            self.stats['messages_sent'] += 1
            if self.verbose:
                display_manager.log_debug(f"Broadcasted POST: {content}")

        self.posts[current_time] = {
            "content": content,
            "likers": set() # set of user_ids that liked this post
        }

        print(f"Post sent: {content}")

    def send_dm(self, target_user_id, content):
        """Send a DM to a specific user"""
        if not content.strip():
            print("DM content cannot be empty.")
            return
        
        # Quick check if user_id is a known peer
        target_ip = self._find_peer_ip(target_user_id)
        
        if target_ip:
            msg = self.message_builder.build_dm(target_user_id, content)
            self.send_message_to_peer(target_user_id, msg)
            print(f"DM sent to {target_user_id}: {content}")
        else:
            print(f"User {target_user_id} not found.")

    def send_follow(self, target_user_id):
        """Send a FOLLOW message to a specific user"""
        if target_user_id in self.following:
            print(f"You are already following {target_user_id}")
            return
        
        # Quick check if user_id is a known peer
        target_ip = self._find_peer_ip(target_user_id)

        if target_ip:
            msg = self.message_builder.build_follow(target_user_id)
            self.send_message_to_peer(target_user_id, msg)
            self.following.add(target_user_id)  # Add to following set
            print(f"You are now following {target_user_id}")
        else:
            print(f"User {target_user_id} not found.")

    def send_unfollow(self, target_user_id):
        """Send an UNFOLLOW message to a specific user"""
        target_ip = self._find_peer_ip(target_user_id)

        if target_ip:
            if target_user_id in self.following:
                msg = self.message_builder.build_unfollow(target_user_id)
                self.send_message_to_peer(target_user_id, msg)
                self.following.remove(target_user_id)
                print(f"You have unfollowed {target_user_id}")
                return
            else:
                print(f"You are not following {target_user_id}")
        else:
            print(f"User {target_user_id} not found.")

    # TODO: Check if correct
    def send_like(self, post_timestamp):
        """Send a LIKE to a followed user's post"""
        if post_timestamp in self.received_posts.keys():
            user_id = self.received_posts[post_timestamp]["user_id"]

            if user_id in self.following:
                if not self.received_posts[post_timestamp]["liking"]:
                    msg = self.message_builder.build_like(user_id, post_timestamp)
                    self.send_message_to_peer(user_id, msg)

                    self.received_posts[post_timestamp]["liking"] = True # turns like state to true

                    print(f"You liked post made at {post_timestamp} from {user_id}")
                else:
                    print(f"You have already liked post made at {post_timestamp} from {user_id}")

            else:
                print(f"You are not following {user_id}")

        else:
            print(f"Post with timestamp {post_timestamp} not found.")

    # TODO: Check if correct
    def send_unlike(self, post_timestamp):
        """Send an UNLIKE to a followed user's post"""
        if post_timestamp in self.received_posts.keys():
            user_id = self.received_posts[post_timestamp]["user_id"]

            if self.received_posts[post_timestamp]["liking"]:
                msg = self.message_builder.build_unlike(user_id, post_timestamp)
                self.send_message_to_peer(user_id, msg)

                self.received_posts[post_timestamp]["liking"] = False
            else:
                print(f"You have not liked post made at {post_timestamp} from {user_id}")

        else:
            print(f"Post with timestamp {post_timestamp} not found.")

    # TODO: Check if correct
    def send_group_create(self, group_id, group_name, group_members):
        """Send a GROUP_CREATE to the members specified"""
        current_time = time.time()
        target_users = group_members.split(",")
        target_ips = [user.split("@")[1] for user in target_users]

        group_key = f"{group_id}|{self.user_id}"

        # [PROBLEM] :: this only checks if the ID is in the creator's list of groups
        if group_key not in self.groups:
            # target users must be known
            if (target_users in self.known_peers) and (target_ips in self.known_ips):
                msg = self.message_builder.build_group_create(group_id, group_name, group_members, current_time)

                # see if they are included in the list
                self.groups[group_key] = {
                    "id": group_id,
                    "name": group_name,
                    "members": group_members,
                    "creator": self.user_id
                }

                # send to all users listed
                for user_id in target_users:
                    self.send_message_to_peer(user_id, msg)

                # print
                print(f"New group created {group_key} -- '{group_name}' ({group_id})")
                print(f"Members:")
                for user_id in target_users:
                    print(f"\t{user_id}\n")
            else:
                print("Group not created. Please make sure members are known.")
        else:
            print(f"You created a group with a group ID {group_id} that already exists.")

    # TODO: Check if correct
    def send_group_message(self, group_key, content):
        current_time = time.time()
        group_creator, group_id = group_key.split("|", 1)

        matching_key = None
        for key, group in self.groups.items():
            if group["id"] == group_id and group["creator"] == group_creator:
                matching_key = key
                break

        if matching_key:
            group = self.groups[matching_key]
            target_users = group["members"]
            msg = self.message_builder.build_group_message(group_id, content, current_time)

            for user_id in target_users:
                self.send_message_to_peer(user_id, msg)

            print(f"Message sent to: {target_users}")
        else:
            print("Group not found.")

    # TODO: Check if correct
    def send_group_update(self, group_id, add_members, remove_members):
        current_time = time.time()
        members_to_add = add_members.split(",")
        members_to_remove = remove_members.split(",")

        if group_id in self.groups:
            target_users = (self.groups.get(group_id))["members"]
            msg = self.message_builder.build_group_update(group_id, add_members, remove_members, current_time)

            # send to all users listed
            for user_id in target_users:
                self.send_message_to_peer(user_id, msg)

            # update local group
            self._update_group(group_id, members_to_add, members_to_remove)

            print(f"{group_id} updated.")
        else:
            print("Group not found.")

    # ====== COMMAND HANDLING ======
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
        # TODO: make ttl_seconds changeable (basically idk where the user should change it)
        # this may also be moved to ms2_draft
        elif cmd == "post":
            content = ' '.join(parts[1:]) if len(parts) > 1 else ""
            self.send_post(content) # ttl_seconds as second argument
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
        # TODO: Check if working/correct
        elif cmd == "unfollow":
            if len(parts) > 1:
                self.send_unfollow(parts[1])
            else:
                print("Usage: unfollow <user_id>")
        # TODO: Check if working/correct
        elif cmd == "like":
            if len(parts) > 1:
                post_timestamp = float(parts[1])
                self.send_like(post_timestamp)
            else:
                print("Usage: like <post_timestamp>")
        # TODO: Check if working/correct
        elif cmd == "unlike":
            if len(parts) > 1:
                post_timestamp = float(parts[1])
                self.send_unlike(post_timestamp)
            else:
                print("Usage: unlike <post_timestamp>")
        # ✅
        elif cmd == "ping":
            self.broadcast_ping()
            print("Ping broadcast sent")
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
        elif cmd == "followers":
            display_manager.print_followers_list(self.followers)
        # TODO: Check if working/correct
        elif cmd == "group_create":
            if len(parts) > 3:
                group_id = parts[1]  
                members_raw = parts[-1]
                group_name = " ".join(parts[2:-1])

                self.send_group_create(group_id, group_name, members_raw)
            else:
                print("Usage: group_create <group_id> <group name> <member1,member2,...>")
        # TODO: Check if working/correct
        elif cmd == "group_message":
            if len(parts) > 2:
                group_key = parts[1]  
                content = parts[2:]

                self.send_group_message(group_key, content)
            else:
                print("Usage: group_message <group_id>|<group_creator> <content>")
        # TODO: Check if working/correct
        elif cmd == "group_update":
            if len(parts) > 3:
                group_id = parts[1]  
                add = ""
                remove = ""

                if "-add" in parts:
                    add_index = parts.index("-add")
                    if add_index + 1 < len(parts):
                        add = parts[add_index + 1]

                if "-remove" in parts:
                    remove_index = parts.index("-remove")
                    if remove_index + 1 < len(parts):
                        remove = parts[remove_index + 1]

                self.send_group_update(group_id, add, remove)
            else:
                print("Usage: group_update <group_id> -add <add_member1,add_member2> -remove <remove_member1,remove_member2>")
        elif cmd == "group":
            display_manager.print_groups(self.groups)
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

# ====== MAIN FUNCTION ======            
def main():
    """Main function - parse arguments and start peer"""
    username = None
    display_name = None
    avatar_path = None
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
        elif args[i] == "--avatar" and i + 1 < len(args):
            avatar_path = args[i + 1]
            i += 2
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)
    
    # Create and start peer
    peer = LSNPPeer(username=username, display_name=display_name, avatar_path=avatar_path, verbose=verbose)
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