# ====== Import Modules
from socket import *
import sys
import threading
import time
import secrets
import base64
import os
import queue
from datetime import datetime
from typing import Dict, Any

from message_builder import MessageBuilder
from message_parser import MessageParser, MessageType
from backend_security import BackendSecurity
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

import dictionary  # Only for MessageType
from utils import display_manager

class LSNPPeer:
    # ====== CLASS CONSTANTS ======
    PORT = 50999
    BROADCAST_IP = '255.255.255.255'
    DISCOVERY_INTERVAL = 300
    DEFAULT_FILES_DIR = "files"
    
    # ====== INITIALIZATION ======
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
        # user_id -> (display_name, ip, status, last_seen)
        self.known_peers = {}
        self.known_ips = set()
        self.following = set()
        self.followers = set()
        self.posts = {} # posts you sent, used for storing likes
        self.received_posts = {} # posts you received, used for sending likes/unlikes
        self.groups = {} # group stored
        self.all_messages = [] # stores ALL messages
        self.revoked_tokens_others = [] # revoked tokens from others
        self.revoked_tokens_self = [] # revoked tokens from self
        self.running = False
        self.verbose = verbose

        # -- File Sending
        self.file_transfers = {}  # file_id -> file_info
        self.file_chunks = {}     # file_id -> {chunk_index: data}
        self.pending_file_offers = {}  # file_id -> offer_info

        # Create default files directory if it doesn't exist
        self._ensure_files_directory()

        # -- ACK & Retries
        self.pending_acks = {}  # message_id -> {'message': msg, 'target_ip': ip, 'retries': count, 'timestamp': time}
        self.ack_timeout = 2.0  # 2 seconds timeout
        self.max_retries = 3
        self.ack_lock = threading.Lock()
        
        # Start the ACK timeout checker thread
        threading.Thread(target=self._ack_timeout_checker, daemon=True).start()
        
        # Message handling ✅
        self.message_builder = MessageBuilder(self.user_id, self.display_name)
        self.message_parser = MessageParser(verbose_mode=self.verbose)
        self.backend_security = BackendSecurity(self.revoked_tokens_self, self.revoked_tokens_others) # [TO UPDATE] not yet used
        
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
        threading.Thread(target=self._discovery_loop, daemon=True).start()

    def stop(self):
        """Stop the peer"""
        self.running = False

        # Clear pending ACKs
        with self.ack_lock:
            self.pending_acks.clear()

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

                msg_type = parsed_message.message_type
                msg_id = parsed_message.fields.get("MESSAGE_ID")

                # Process message (this handles ACKs internally now)
                parsed_message = self._process_message(message, addr[0])
                if parsed_message is None:
                    continue
                
                # Send ACK for messages that need it (right now it is just ACK because not sure about PING and PROFILE)
                no_ack_types = {MessageType.ACK, MessageType.FILE_OFFER}
                
                if msg_id and msg_type not in no_ack_types:
                    ack = self.message_builder.build_ack(msg_id, "RECEIVED")
                    self.sock.sendto(ack.encode(), (addr[0], self.PORT))

                    self.all_messages.append(parsed_message)
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

        # Handle different message types
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
        elif parsed_message.message_type == MessageType.FILE_OFFER:
            self._handle_file_offer_message(parsed_message)
        elif parsed_message.message_type == MessageType.FILE_CHUNK:
            self._handle_file_chunk_message(parsed_message)
        elif parsed_message.message_type == MessageType.FILE_RECEIVED:
            self._handle_file_received_message(parsed_message)
        elif parsed_message.message_type == MessageType.ACK:
            self._handle_ack_message(parsed_message)
            return parsed_message

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
        
        # Use shared validation
        if not self._validate_user_id_and_ip(user_id, parsed_message.sender_ip):
            return

        # Update peer info
        self._update_peer_info(user_id, display_name, parsed_message.sender_ip, status)

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

        # Update peer info
        self._update_peer_info(sender_id, sender_username, sender_ip)
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

        print("received post", user_id, content)

        self.received_posts[current_time] = {
            "user_id": user_id,
            "content": content,
            "liking": False
        }

        print("list of posts", self.received_posts)

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
        """Accept a GROUP_UPDATE message"""
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

    def _handle_revoke_message(self, parsed_message):
        """Accept a REVOKE message"""
        token = parsed_message.fields.get("TOKEN")

         # check if token is already revoked
        if token in self.revoked_tokens_others:
            if self.verbose:
                display_manager.log_debug(f"Received REVOKE for an already revoked token: {token}")
            return

        # add to revoked_tokens_others list
        self.revoked_tokens_others.append(token)

        if self.verbose:
            display_manager.log_debug(f"Token revoked by peer: {token}")
    
    def _handle_file_offer_message(self, parsed_message):
        """Handle FILE_OFFER messages with automatic acceptance/rejection"""
        sender_id = parsed_message.fields.get("FROM")
        file_id = parsed_message.fields.get("FILEID")
        filename = parsed_message.fields.get("FILENAME")
        filesize = parsed_message.fields.get("FILESIZE")
        filetype = parsed_message.fields.get("FILETYPE")
        description = parsed_message.fields.get("DESCRIPTION", "")
        
        # Validate sender
        if not self._validate_user_id_and_ip(sender_id, parsed_message.sender_ip):
            return
        
        # Store pending file offer
        self.pending_file_offers[file_id] = {
            "sender": sender_id,
            "filename": filename,
            "filesize": int(filesize),
            "filetype": filetype,
            "description": description,
            "timestamp": time.time(),
            "accepted": None  # None = pending, True = accepted, False = rejected
        }
        
        # Update peer info
        sender_username = sender_id.split('@')[0]
        self._update_peer_info(sender_id, sender_username, parsed_message.sender_ip)
        self._log_ip(parsed_message.sender_ip)
        
        if self.verbose:
            display_manager.log_debug(f"File offer received from {sender_id}: {filename} ({filesize} bytes)")

    def _handle_file_chunk_message(self, parsed_message):
        """Handle FILE_CHUNK messages - only accept if file was explicitly accepted"""
        sender_id = parsed_message.fields.get("FROM")
        file_id = parsed_message.fields.get("FILEID")

        # Check if we have explicitly rejected this file
        if file_id in self.pending_file_offers:
            offer_info = self.pending_file_offers[file_id]
            if offer_info["accepted"] is False:  # Explicitly rejected
                if self.verbose:
                    display_manager.log_warning(f"Ignoring chunk for rejected file {file_id}")
                return  # Ignore silently
            elif offer_info["accepted"] is not True:  # Still pending
                if self.verbose:
                    display_manager.log_warning(f"Received chunk for file {file_id} that hasn't been accepted yet")
                return

        chunk_index = int(parsed_message.fields.get("CHUNK_INDEX"))
        total_chunks = int(parsed_message.fields.get("TOTAL_CHUNKS"))
        chunk_size = int(parsed_message.fields.get("CHUNK_SIZE"))
        data = parsed_message.fields.get("DATA")
        
        # Check if we have explicitly accepted this file
        if file_id in self.pending_file_offers:
            offer_info = self.pending_file_offers[file_id]
            if offer_info["accepted"] is not True:  # None (pending) or False (rejected)
                if self.verbose:
                    display_manager.log_warning(f"Received chunk for file {file_id} that hasn't been accepted yet")
                return
        elif file_id not in self.file_transfers:
            if self.verbose:
                display_manager.log_warning(f"Received chunk for unknown file: {file_id}")
            return
        
        # Initialize file transfer if first chunk and file is accepted
        if file_id not in self.file_transfers:
            offer_info = self.pending_file_offers.get(file_id)
            if offer_info and offer_info["accepted"]:
                self.file_transfers[file_id] = {
                    "sender": sender_id,
                    "filename": offer_info["filename"],
                    "filesize": offer_info["filesize"],
                    "filetype": offer_info["filetype"],
                    "total_chunks": total_chunks,
                    "received_chunks": 0,
                    "start_time": time.time()
                }
                self.file_chunks[file_id] = {}
        
        # Store chunk
        if file_id not in self.file_chunks:
            self.file_chunks[file_id] = {}
        
        self.file_chunks[file_id][chunk_index] = data
        self.file_transfers[file_id]["received_chunks"] = len(self.file_chunks[file_id])
        
        if self.verbose:
            received = self.file_transfers[file_id]["received_chunks"]
            display_manager.log_debug(f"Received chunk {chunk_index + 1}/{total_chunks} for file {file_id} ({received}/{total_chunks} total)")
        
        # Check if all chunks received
        if len(self.file_chunks[file_id]) == total_chunks:
            self._complete_file_transfer(file_id)


    def _handle_file_received_message(self, parsed_message):
        """Handle FILE_RECEIVED messages"""
        sender_id = parsed_message.fields.get("FROM")
        file_id = parsed_message.fields.get("FILEID")
        status = parsed_message.fields.get("STATUS")
        
        if self.verbose:
            display_manager.log_debug(f"File transfer confirmation from {sender_id}: {file_id} - {status}")
    
    def _handle_ack_message(self, parsed_message):
        """Handle received ACK messages and trigger automatic file sending"""
        msg_id = parsed_message.fields.get("MESSAGE_ID")
        status = parsed_message.fields.get("STATUS")
        
        if self.verbose:
            display_manager.log_debug(f"Received ACK with MESSAGE_ID={msg_id}, STATUS={status}")
        
        # First try to match by MESSAGE_ID (standard messages)
        if msg_id:
            with self.ack_lock:
                if msg_id in self.pending_acks:
                    if self.verbose:
                        display_manager.log_debug(f"Received ACK for message {msg_id} with status: {status}")
                    
                    # Check if this ACK is for a file offer
                    ack_info = self.pending_acks[msg_id]
                    message = ack_info['message']
                    
                    # Parse the original message to check if it was a file offer
                    try:
                        parsed_original = self.message_parser.parse_message(message, ack_info['target_ip'])
                        if parsed_original and parsed_original.message_type == MessageType.FILE_OFFER:
                            file_id = parsed_original.fields.get("FILEID")
                            if file_id and file_id in self.file_transfers:
                                # The ACK means the recipient is ready to receive the file
                                if self.verbose:
                                    display_manager.log_debug(f"File offer {file_id} was ACKed, starting automatic file transfer")
                                
                                # Start sending chunks in a separate thread to avoid blocking
                                threading.Thread(
                                    target=self._auto_send_file_chunks, 
                                    args=(file_id,), 
                                    daemon=True
                                ).start()
                    except Exception as e:
                        if self.verbose:
                            display_manager.log_warning(f"Error checking ACK for file offer: {e}")
                    
                    del self.pending_acks[msg_id]
                    return
                elif self.verbose:
                    display_manager.log_debug(f"Received ACK for unknown message {msg_id}")
        
        # If MESSAGE_ID didn't match, try to match by FILEID for file-related ACKs
        # The ACK might be using FILEID instead of MESSAGE_ID
        file_id_in_ack = msg_id  # The "MESSAGE_ID" field might actually contain a FILEID
        
        # Check if this looks like a file ID and we have a matching file transfer
        if file_id_in_ack and file_id_in_ack in self.file_transfers:
            if self.verbose:
                display_manager.log_debug(f"ACK matched file transfer by FILEID: {file_id_in_ack}")
            
            # This is likely an ACK for a file offer using FILEID
            if status in ["ACCEPTED", "RECEIVED"]:
                if self.verbose:
                    display_manager.log_debug(f"File {file_id_in_ack} was accepted, starting automatic file transfer")
                
                # Start sending chunks in a separate thread
                threading.Thread(
                    target=self._auto_send_file_chunks, 
                    args=(file_id_in_ack,), 
                    daemon=True
                ).start()
            elif self.verbose:
                display_manager.log_debug(f"File {file_id_in_ack} ACK status: {status}")
            return
        
        # Check pending file offers for FILEID match
        if file_id_in_ack and file_id_in_ack in self.pending_file_offers:
            offer_info = self.pending_file_offers[file_id_in_ack]
            if status == "ACCEPTED" and offer_info["accepted"] is True:
                if self.verbose:
                    display_manager.log_debug(f"File offer {file_id_in_ack} confirmed accepted via ACK")
                
                # Start file transfer if we have the file ready
                if file_id_in_ack in self.file_transfers:
                    threading.Thread(
                        target=self._auto_send_file_chunks, 
                        args=(file_id_in_ack,), 
                        daemon=True
                    ).start()
            return
        
        if self.verbose:
            display_manager.log_debug(f"Could not match ACK to any pending message or file transfer")

    # Fix for _handle_file_offer_message method
        """Handle FILE_OFFER messages with automatic acceptance/rejection"""
        sender_id = parsed_message.fields.get("FROM")
        file_id = parsed_message.fields.get("FILEID")
        filename = parsed_message.fields.get("FILENAME")
        filesize = parsed_message.fields.get("FILESIZE")
        filetype = parsed_message.fields.get("FILETYPE")
        description = parsed_message.fields.get("DESCRIPTION", "")
        message_id = parsed_message.fields.get("MESSAGE_ID")  # Store this!
        
        # Validate sender
        if not self._validate_user_id_and_ip(sender_id, parsed_message.sender_ip):
            return
        
        # Store pending file offer WITH message_id
        self.pending_file_offers[file_id] = {
            "sender": sender_id,
            "filename": filename,
            "filesize": int(filesize),
            "filetype": filetype,
            "description": description,
            "timestamp": time.time(),
            "accepted": None,  # None = pending, True = accepted, False = rejected
            "message_id": message_id  # Add this line!
        }
        
        # Update peer info
        sender_username = sender_id.split('@')[0]
        self._update_peer_info(sender_id, sender_username, parsed_message.sender_ip)
        self._log_ip(parsed_message.sender_ip)
        
        if self.verbose:
            display_manager.log_debug(f"File offer received from {sender_id}: {filename} ({filesize} bytes)")

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
                # [TO UPDATE] This portion is commented for testing purposes. Currently we are using VPN only, hence the IPs will always be different.
                # return False
        except IndexError:
            if self.verbose:
                display_manager.log_warning(f"Invalid USER_ID format: {user_id}")
            return False
        
        return True

    def _update_peer_info(self, user_id, display_name, ip, status=""):
        """Update peer information and log updates conditionally."""
        current_time = time.time()

        # Skip if it's our own user_id
        if user_id == self.user_id:
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
        ttl_sec = parsed_msg.fields.get("TTL")

        current_time = float(current_time_with_ttl) - float(ttl_sec) # subtracts ttl from post time

        # Store the post regardless of whether we have followers
        self.posts[current_time] = {
            "content": content,
            "likers": set() # set of user_ids that liked this post
        }

        # TODO: check if correct
        # Check if we have followers to send to
        peers_to_send_to = [uid for uid in self.followers if uid != self.user_id]
        if peers_to_send_to:
            # Send to all followers
            for uid in peers_to_send_to:
                self.send_message_to_peer(uid, msg)
            print(f"Post sent to {len(peers_to_send_to)} followers: {content}")
        else:
            # No followers - just store locally
            print(f"Post created (you have no followers): {content}")
            if self.verbose:
                display_manager.log_debug(f"Post stored locally only (no followers): {content}")

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
                print(f"You unliked post made at {post_timestamp} from {user_id}")
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

    # TODO: Check if correct
    def send_revoke(self, token):
        current_time = time.time()

        if token in self.revoked_tokens_self:
            print(f"Token {token} is already revoked by you.")
            return
        
        # check if the token to be revoked is a token from the sender
        try:
            user_part = token.split("|")[0] 
            user_id = user_part.split("@")[0]
        except (IndexError, ValueError):
            print(f"Invalid token format: {token}")
            return

        if user_id != self.user_id:
            print(f"Cannot revoke token {token} — it does not belong to you.")
            return

        # add token to self-revoked list
        self.revoked_tokens_self.append(token)
        msg = self.message_builder.build_revoke(token, current_time)

        # broadcast to all known peers
        # [TO UPDATE] clarify scope 
        for peer_id in self.known_peers:
            self.send_message_to_peer(peer_id, msg)

        print(f"Revoked token: {token}")
    
    def _send_message_with_ack(self, target_user_id, message, needs_ack=True):
        """Send a message and track it for ACK if needed"""
        target_ip = self._find_peer_ip(target_user_id)
        if not target_ip:
            print(f"User {target_user_id} not found.")
            return False
        
        try:
            self.sock.sendto(message.encode(), (target_ip, self.PORT))
            self.stats['messages_sent'] += 1
            
            if needs_ack:
                # Parse message to get MESSAGE_ID
                parsed = self.message_parser.parse_message(message)
                if parsed and parsed.fields.get("MESSAGE_ID"):
                    msg_id = parsed.fields.get("MESSAGE_ID")
                    with self.ack_lock:
                        self.pending_acks[msg_id] = {
                            'message': message,
                            'target_ip': target_ip,
                            'retries': 0,
                            'timestamp': time.time()
                        }
                    
                    if self.verbose:
                        display_manager.log_debug(f"Sent message {msg_id} to {target_user_id}, waiting for ACK")
            
            return True
        except Exception as e:
            print(f"Error sending message to {target_user_id}: {e}")
            return False

    def send_file_offer(self, target_user_id, filepath, description=""):
        """Send a file offer to a specific user"""
        # Resolve the file path
        resolved_path = self._resolve_file_path(filepath)
        
        if not resolved_path:
            print(f"File not found: {filepath}")
            if os.path.basename(filepath) == filepath:
                print(f"  Checked default directory: {os.path.join(self.DEFAULT_FILES_DIR, filepath)}")
            print(f"  Checked as given path: {filepath}")
            return
        
        filename = os.path.basename(resolved_path)
        filesize = os.path.getsize(resolved_path)
        filetype = self._guess_file_type(filename)
        
        # Check if user exists
        target_ip = self._find_peer_ip(target_user_id)
        if not target_ip:
            print(f"User {target_user_id} not found.")
            return
        
        msg = self.message_builder.build_file_offer(target_user_id, filename, filesize, filetype, description)
        
        # Extract file ID from the message for tracking
        parsed_msg = self.message_parser.parse_message(msg)
        file_id = parsed_msg.fields.get("FILEID")
        
        # Store file info for automatic sending (use resolved path)
        self.file_transfers[file_id] = {
            "filepath": resolved_path,
            "target_user": target_user_id,
            "filename": filename,
            "filesize": filesize,
            "sent_chunks": 0,
            "status": "offered"
        }
        
        # Send with ACK tracking - chunks will be sent automatically when ACK is received
        if self._send_message_with_ack(target_user_id, msg, needs_ack=True):
            print(f"File offer sent to {target_user_id}: {filename}")
            print(f"  Source: {resolved_path}")
            print(f"  File ID: {file_id}")
            print("File will be sent automatically once accepted.")
        else:
            # Clean up on send failure
            if file_id in self.file_transfers:
                del self.file_transfers[file_id]

    def send_file_chunks(self, file_id, chunk_size=1024):
        """Send file chunks for an accepted file transfer"""
        if file_id not in self.file_transfers:
            print(f"File transfer {file_id} not found")
            return
        
        transfer_info = self.file_transfers[file_id]
        filepath = transfer_info["filepath"]
        target_user_id = transfer_info["target_user"]
        
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            # Split into chunks
            chunks = []
            for i in range(0, len(file_data), chunk_size):
                chunk_data = file_data[i:i + chunk_size]
                encoded_chunk = base64.b64encode(chunk_data).decode('utf-8')
                chunks.append(encoded_chunk)
            
            total_chunks = len(chunks)
            successful_chunks = 0
            
            # Send each chunk with ACK tracking
            for i, chunk_data in enumerate(chunks):
                msg = self.message_builder.build_file_chunk(
                    target_user_id, file_id, i, total_chunks, len(chunk_data), chunk_data
                )
                
                if self._send_message_with_ack(target_user_id, msg, needs_ack=True):
                    successful_chunks += 1
                    if self.verbose:
                        display_manager.log_debug(f"Sent chunk {i + 1}/{total_chunks} for file {file_id}")
                    time.sleep(0.1)  # Small delay between chunks
                else:
                    print(f"Failed to send chunk {i + 1}/{total_chunks} for file {file_id}")
            
            if successful_chunks == total_chunks:
                print(f"Sent {total_chunks} chunks for file {file_id}")
                transfer_info["status"] = "sent"
            else:
                print(f"Warning: Only {successful_chunks}/{total_chunks} chunks sent successfully for file {file_id}")
                
        except Exception as e:
            print(f"Error sending file chunks: {e}")

    # ====== FILE MANAGEMENT (RECEIVING & SENDING) ======
    def _complete_file_transfer(self, file_id):
        """Complete file transfer by reassembling chunks"""
        transfer_info = self.file_transfers[file_id]
        chunks = self.file_chunks[file_id]
        
        # Reassemble file data
        file_data = b""
        for i in range(transfer_info["total_chunks"]):
            if i in chunks:
                chunk_data = base64.b64decode(chunks[i])
                file_data += chunk_data
            else:
                if self.verbose:
                    display_manager.log_warning(f"Missing chunk {i} for file {file_id}")
                return
        
        # Save file to default directory
        filename = transfer_info["filename"]
        save_path = self._get_save_path(filename)
        
        try:
            with open(save_path, 'wb') as f:
                f.write(file_data)
            
            print(f"File received: {filename}")
            print(f"  Saved to: {save_path}")
            
            # Send FILE_RECEIVED confirmation
            sender_id = transfer_info["sender"]
            msg = self.message_builder.build_file_received(sender_id, file_id, "COMPLETE")
            self.send_message_to_peer(sender_id, msg)
            
            if self.verbose:
                display_manager.log_debug(f"File saved as {save_path} ({len(file_data)} bytes)")
            
        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            if self.verbose:
                display_manager.log_warning(f"Failed to save file {filename}: {e}")
        
        # Clean up
        if file_id in self.file_transfers:
            del self.file_transfers[file_id]
        if file_id in self.file_chunks:
            del self.file_chunks[file_id]
        if file_id in self.pending_file_offers:
            del self.pending_file_offers[file_id]

    def _make_safe_filename(self, filename):
        """Make filename safe for saving"""
        # Remove dangerous characters
        safe_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        safe_filename = "".join(c for c in filename if c in safe_chars)
        
        # Prevent empty filename
        if not safe_filename:
            safe_filename = "received_file"
        
        # Add counter if file exists
        counter = 1
        original_name = safe_filename
        while os.path.exists(safe_filename):
            name, ext = os.path.splitext(original_name)
            safe_filename = f"{name}_{counter}{ext}"
            counter += 1
        
        return safe_filename

    def accept_file(self, file_id):
        """Accept a pending file offer"""
        if file_id not in self.pending_file_offers:
            print(f"No pending file offer with ID: {file_id}")
            return
        
        offer_info = self.pending_file_offers[file_id]
        
        # Check if already processed
        if offer_info["accepted"] is not None:
            status = "accepted" if offer_info["accepted"] else "rejected"
            print(f"File {file_id} already {status}")
            return
        
        # Mark as accepted
        offer_info["accepted"] = True
        print(f"Accepting file: {offer_info['filename']} from {offer_info['sender']}")
        
        # Move to active transfers
        self.file_transfers[file_id] = {
            "sender": offer_info["sender"],
            "filename": offer_info["filename"],
            "filesize": offer_info["filesize"],
            "filetype": offer_info["filetype"],
            "total_chunks": 0,  # Will be set when first chunk arrives
            "received_chunks": 0,
            "start_time": time.time()
        }
        
        # Send ACK using FILEID in the MESSAGE_ID field
        # This is a workaround since file messages don't have MESSAGE_ID
        sender_id = offer_info["sender"]
        ack = self.message_builder.build_ack(file_id, "ACCEPTED")
        self.send_message_to_peer(sender_id, ack)
        
        print(f"File {file_id} accepted. ACK sent to {sender_id}.")
        if self.verbose:
            display_manager.log_debug(f"File {file_id} accepted, ACK sent with FILEID to trigger transfer")


    def reject_file(self, file_id):
        """Reject a pending file offer"""
        if file_id not in self.pending_file_offers:
            print(f"No pending file offer with ID: {file_id}")
            return
        
        offer_info = self.pending_file_offers[file_id]
        
        # Check if already processed
        if offer_info["accepted"] is not None:
            status = "accepted" if offer_info["accepted"] else "rejected"
            print(f"File {file_id} already {status}")
            return
        
        # Mark as rejected
        offer_info["accepted"] = False
        print(f"Rejected file: {offer_info['filename']} from {offer_info['sender']}")
        
        # Remove from pending offers after marking as rejected
        del self.pending_file_offers[file_id]
        
        if self.verbose:
            display_manager.log_debug(f"File {file_id} rejected and removed from pending offers")

    def _guess_file_type(self, filename):
        """Guess MIME type from filename extension"""
        ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.zip': 'application/zip'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def list_file_transfers(self):
        """List pending file offers and active transfers"""
        print("\n--- File Transfers ---")
        
        if self.pending_file_offers:
            print("Pending Offers:")
            for file_id, offer in self.pending_file_offers.items():
                status_text = ""
                if offer["accepted"] is True:
                    status_text = " (ACCEPTED)"
                elif offer["accepted"] is False:
                    status_text = " (REJECTED)"
                else:
                    status_text = " (PENDING)"
                
                print(f"  {file_id}: {offer['filename']} ({offer['filesize']} bytes) from {offer['sender']}{status_text}")
        
        if self.file_transfers:
            print("Active Transfers:")
            for file_id, transfer in self.file_transfers.items():
                if "received_chunks" in transfer:
                    print(f"  {file_id}: {transfer['filename']} - {transfer['received_chunks']}/{transfer.get('total_chunks', '?')} chunks")
                else:
                    print(f"  {file_id}: {transfer['filename']} - {transfer['status']}")
        
        if not self.pending_file_offers and not self.file_transfers:
            print("No active file transfers")
        
        print("---------------------\n")
    
    def _ensure_files_directory(self):
        """Create the default files directory if it doesn't exist"""
        try:
            if not os.path.exists(self.DEFAULT_FILES_DIR):
                os.makedirs(self.DEFAULT_FILES_DIR)
                if self.verbose:
                    display_manager.log_debug(f"Created default files directory: {self.DEFAULT_FILES_DIR}")
        except Exception as e:
            if self.verbose:
                display_manager.log_warning(f"Could not create files directory: {e}")
    
    def _resolve_file_path(self, filepath):
        """
        Resolve file path with fallback logic:
        1. Check if it's just a filename -> look in default directory
        2. Check if it's a relative/absolute path that exists
        3. Return None if file not found anywhere
        """
        # If it's just a filename (no path separators), check default directory first
        if os.path.basename(filepath) == filepath:
            default_path = os.path.join(self.DEFAULT_FILES_DIR, filepath)
            if os.path.exists(default_path):
                return default_path
        
        # Check if the original path exists (relative or absolute)
        if os.path.exists(filepath):
            return filepath
        
        # File not found anywhere
        return None
    
    def _get_save_path(self, filename):
        """Get the path where received files should be saved"""
        return os.path.join(self.DEFAULT_FILES_DIR, self._make_safe_filename(filename))

    def list_files_directory(self):
        """List files in the default files directory"""
        if not os.path.exists(self.DEFAULT_FILES_DIR):
            print(f"Files directory '{self.DEFAULT_FILES_DIR}' does not exist")
            return
        
        try:
            files = os.listdir(self.DEFAULT_FILES_DIR)
            if not files:
                print(f"No files in '{self.DEFAULT_FILES_DIR}' directory")
                return
            
            print(f"\n--- Files in '{self.DEFAULT_FILES_DIR}' directory ---")
            for filename in sorted(files):
                filepath = os.path.join(self.DEFAULT_FILES_DIR, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    print(f"  {filename} ({size} bytes)")
            print("-------------------------------------\n")
            
        except Exception as e:
            print(f"Error listing files directory: {e}")
    
    def _auto_send_file_chunks(self, file_id, chunk_size=1024):
        """Automatically send file chunks after offer acceptance"""
        if file_id not in self.file_transfers:
            if self.verbose:
                display_manager.log_warning(f"Cannot auto-send chunks for unknown file transfer: {file_id}")
            return
        
        transfer_info = self.file_transfers[file_id]
        filepath = transfer_info["filepath"]
        target_user_id = transfer_info["target_user"]
        
        if self.verbose:
            display_manager.log_debug(f"Auto-sending file chunks for {file_id}")
        
        # Small delay to ensure the recipient is ready
        time.sleep(0.5)
        
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            # Split into chunks
            chunks = []
            for i in range(0, len(file_data), chunk_size):
                chunk_data = file_data[i:i + chunk_size]
                encoded_chunk = base64.b64encode(chunk_data).decode('utf-8')
                chunks.append(encoded_chunk)
            
            total_chunks = len(chunks)
            successful_chunks = 0
            
            print(f"Starting automatic file transfer: {transfer_info['filename']} ({total_chunks} chunks)")
            
            # Send each chunk with ACK tracking
            for i, chunk_data in enumerate(chunks):
                msg = self.message_builder.build_file_chunk(
                    target_user_id, file_id, i, total_chunks, len(chunk_data), chunk_data
                )
                
                if self._send_message_with_ack(target_user_id, msg, needs_ack=True):
                    successful_chunks += 1
                    if self.verbose:
                        display_manager.log_debug(f"Auto-sent chunk {i + 1}/{total_chunks} for file {file_id}")
                    time.sleep(0.1)  # Small delay between chunks
                else:
                    print(f"Failed to send chunk {i + 1}/{total_chunks} for file {file_id}")
            
            if successful_chunks == total_chunks:
                print(f"File transfer completed: {transfer_info['filename']} ({total_chunks} chunks sent)")
                transfer_info["status"] = "sent"
            else:
                print(f"Warning: Only {successful_chunks}/{total_chunks} chunks sent successfully for file {file_id}")
                
        except Exception as e:
            print(f"Error in automatic file transfer: {e}")
            if self.verbose:
                display_manager.log_warning(f"Auto file transfer failed for {file_id}: {e}")
    
    # ====== ACK TIMEOUT & RETRY ======
    def _ack_timeout_checker(self):
        """Check for ACK timeouts and handle retries"""
        while self.running:
            try:
                current_time = time.time()
                expired_messages = []
                
                with self.ack_lock:
                    for msg_id, ack_info in self.pending_acks.items():
                        if current_time - ack_info['timestamp'] > self.ack_timeout:
                            expired_messages.append(msg_id)
                
                for msg_id in expired_messages:
                    self._handle_ack_timeout(msg_id)
                
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                if self.running and self.verbose:
                    display_manager.log_warning(f"Error in ACK timeout checker: {e}")
    
    def _handle_ack_timeout(self, message_id):
        """Handle ACK timeout for a message"""
        with self.ack_lock:
            if message_id not in self.pending_acks:
                return
            
            ack_info = self.pending_acks[message_id]
            ack_info['retries'] += 1
            
            if ack_info['retries'] <= self.max_retries:
                # Retry sending the message
                try:
                    self.sock.sendto(ack_info['message'].encode(), (ack_info['target_ip'], self.PORT))
                    ack_info['timestamp'] = time.time()  # Update timestamp for new retry
                    
                    if self.verbose:
                        display_manager.log_debug(f"Retrying message {message_id} (attempt {ack_info['retries']}/{self.max_retries})")
                except Exception as e:
                    if self.verbose:
                        display_manager.log_warning(f"Failed to retry message {message_id}: {e}")
            else:
                # Max retries exceeded
                if self.verbose:
                    display_manager.log_warning(f"Max retries exceeded for message {message_id}")
                
                # Handle specific failure cases
                self._handle_message_failure(message_id, ack_info)
                
                # Remove from pending ACKs
                del self.pending_acks[message_id]

    def _handle_message_failure(self, message_id, ack_info):
        """Handle message failure after max retries"""
        message = ack_info['message']
        
        # Parse message to determine type and handle accordingly
        try:
            parsed = self.message_parser.parse_message(message)
            if parsed and parsed.message_type == MessageType.FILE_OFFER:
                file_id = parsed.fields.get("FILEID")
                if file_id and file_id in self.file_transfers:
                    print(f"Failed to send file offer for {self.file_transfers[file_id]['filename']} - no response from recipient")
                    # Clean up failed file transfer
                    del self.file_transfers[file_id]
            elif parsed and parsed.message_type == MessageType.FILE_CHUNK:
                file_id = parsed.fields.get("FILEID")
                chunk_index = parsed.fields.get("CHUNK_INDEX")
                if file_id and chunk_index is not None:
                    print(f"Failed to send file chunk {chunk_index} for file {file_id} - transfer may be incomplete")
        except Exception as e:
            if self.verbose:
                display_manager.log_warning(f"Error handling message failure: {e}")

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
        # TODO: Check if working/correct
        elif cmd == "group":
            display_manager.print_groups(self.groups)
        # TODO: Check if working/correct
        elif cmd == "revoke":
            if len(parts) > 1:
                token = parts[1]
                self.send_revoke(token)
            else:
                print("Usage: revoke <TOKEN>")
                
        elif cmd == "file_offer":
            if len(parts) > 2:
                target_user = parts[1]
                filepath = parts[2]
                description = ' '.join(parts[3:]) if len(parts) > 3 else ""
                self.send_file_offer(target_user, filepath, description)
            else:
                print("Usage: file_offer <user_id> <filepath> [description]")
        
        elif cmd == "accept_file":
            if len(parts) > 1:
                file_id = parts[1]
                self.accept_file(file_id)
                print(f"File {file_id} accepted. Transfer will begin automatically.")
            else:
                print("Usage: accept_file <file_id>")

        elif cmd == "reject_file":
            if len(parts) > 1:
                file_id = parts[1]
                self.reject_file(file_id)
            else:
                print("Usage: reject_file <file_id>")

        elif cmd == "file_transfers":
            self.list_file_transfers()
        
        elif cmd == "list_files":
            self.list_files_directory()
        
        elif cmd == "ack_status":
            with self.ack_lock:
                if self.pending_acks:
                    print(f"\nPending ACKs ({len(self.pending_acks)}):")
                    for msg_id, ack_info in self.pending_acks.items():
                        elapsed = time.time() - ack_info['timestamp']
                        print(f"  {msg_id}: {ack_info['retries']}/{self.max_retries} retries, {elapsed:.1f}s elapsed")
                else:
                    print("No pending ACKs")

        # ✅; ongoing, to be applied in all features
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
        # ✅
        elif cmd == "help":
            display_manager.print_help()
        # ✅
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

# ====== MAIN FUNCTION ======            
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