import time
from enum import Enum
from typing import Dict, Optional, List, Tuple
from dictionary import MessageType

class ParsedMessage:
    """Represents a parsed LSNP message"""
    
    def __init__(self, raw_message: str, sender_ip: str):
        self.raw_message = raw_message
        self.sender_ip = sender_ip
        self.timestamp = time.time()
        self.message_type = MessageType.UNKNOWN
        self.fields = {}
        self.is_valid = False
        self.validation_errors = []
    
    def get_display_name(self, peer_profiles: Dict[str, Tuple[str, str, str]]) -> str:
        """
        Get display name for message sender.
        peer_profiles: {user_id: (display_name, ip, status)}
        """
        user_id = self.fields.get("USER_ID") or self.fields.get("FROM")
        
        if user_id:
            # Check if the user_id exists in our known peer_profiles
            if user_id in peer_profiles:
                return peer_profiles[user_id][0] # Return display_name
            else:
                # If user_id is not in known_peers, try to extract a username from it
                # and use the DISPLAY_NAME field if present, otherwise just the username part
                username_part = user_id.split('@')[0] if '@' in user_id else user_id
                return self.fields.get("DISPLAY_NAME", username_part)
        
        # Fallback if no user_id or FROM field
        return self.fields.get("DISPLAY_NAME", f"Unknown@{self.sender_ip}")
    
    def to_debug_string(self) -> str:
        """Convert to debug string for troubleshooting"""
        debug_lines = [
            f"=== DEBUG MESSAGE INFO ===",
            f"Sender IP: {self.sender_ip}",
            f"Timestamp: {time.ctime(self.timestamp)}",
            f"Message Type: {self.message_type.value}",
            f"Valid: {self.is_valid}",
            f"Validation Errors: {self.validation_errors}",
            f"Fields: {self.fields}",
            f"Raw Message:",
            self.raw_message,
            f"=========================="
        ]
        return "\n".join(debug_lines)

class MessageParser:
    """LSNP Message Parser - Core message types processing"""
    
    def __init__(self, verbose_mode: bool = False):
        self.verbose_mode = verbose_mode # This will be updated by LSNPPeer's verbose toggle
        self.processed_count = 0
        self.invalid_count = 0
    
    def get_processed_count(self) -> int:
        """Get count of processed messages"""
        return self.processed_count
    
    def get_invalid_count(self) -> int:
        """Get count of invalid messages"""
        return self.invalid_count
    
    def parse_message(self, raw_message: str, sender_ip: str = None) -> Optional[ParsedMessage]:
        """Parse a raw LSNP message into a ParsedMessage object"""
        self.processed_count += 1
        
        message = ParsedMessage(raw_message, sender_ip)
        
        # Use the current self.verbose_mode for parsing logs
        if self.verbose_mode:
            print(f">> [DEBUG - Parser] Attempting to parse raw message from {sender_ip}:")
            print("----------------------------------------")
            print(raw_message.strip())
            print("----------------------------------------")
        
        try:
            # Parse message fields
            self._parse_fields(message)
            
            # Determine message type
            self._determine_message_type(message)
            
            # Check for fundamental parsing failure
            if message.message_type == MessageType.UNKNOWN and "TYPE" not in message.fields:
                if self.verbose_mode:
                    print(f">> [WARNING - Parser] Message has no recognizable TYPE field. Returning None.")
                self.invalid_count += 1
                return None
            
            # Validate message based on its determined type
            self._validate_message(message)
            
        except Exception as e:
            message.validation_errors.append(f"Critical parsing error: {str(e)}")
            message.is_valid = False
            self.invalid_count += 1
            if self.verbose_mode:
                print(f">> [ERROR - Parser] Exception during parsing: {e}. Returning None.")
                print(message.to_debug_string())
            return None 
        
        return message

    def _parse_fields(self, message: ParsedMessage):
        """Parse message fields from raw message"""
        lines = message.raw_message.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                message.fields[key.strip()] = value.strip()
            elif self.verbose_mode and line.strip(): # Only print debug for non-colon lines in verbose mode
                print(f">> [DEBUG - Parser] Skipping non-colon line: '{line.strip()}'")
    
    def _determine_message_type(self, message: ParsedMessage):
        """Determine message type from parsed fields"""
        msg_type_str = message.fields.get("TYPE", "").strip().upper()
        
        if not msg_type_str:
            message.message_type = MessageType.UNKNOWN
            message.validation_errors.append("Missing TYPE field in message header")
            return
        
        try:
            message.message_type = MessageType[msg_type_str]
        except KeyError:
            message.message_type = MessageType.UNKNOWN
            message.validation_errors.append(f"Unknown message type string: {msg_type_str}")
    
    def _validate_message(self, message: ParsedMessage):
        """Validate message according to LSNP RFC specifications"""
        message.is_valid = True

        # Type-specific validation
        if message.message_type == MessageType.PROFILE:
            if not all(k in message.fields for k in ["USER_ID", "DISPLAY_NAME", "STATUS"]):
                message.validation_errors.append("PROFILE message missing USER_ID, DISPLAY_NAME, or STATUS")
                message.is_valid = False

        elif message.message_type == MessageType.POST:
            if not all(k in message.fields for k in ["USER_ID", "CONTENT", "TTL", "MESSAGE_ID", "TOKEN"]):
                message.validation_errors.append("POST message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.DM:
            if not all(k in message.fields for k in ["FROM", "TO", "CONTENT", "TIMESTAMP", "MESSAGE_ID", "TOKEN"]):
                message.validation_errors.append("DM message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.FOLLOW or message.message_type == MessageType.UNFOLLOW:
            if not all(k in message.fields for k in ["FROM", "TO", "MESSAGE_ID", "TIMESTAMP", "TOKEN"]):
                message.validation_errors.append(f"{message.message_type.value} message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.LIKE:
            if not all(k in message.fields for k in ["FROM", "TO", "POST_TIMESTAMP", "ACTION", "TIMESTAMP", "TOKEN"]):
                message.validation_errors.append("LIKE message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.UNLIKE:
            if not all(k in message.fields for k in ["FROM", "TO", "POST_TIMESTAMP", "ACTION", "TIMESTAMP", "TOKEN"]):
                message.validation_errors.append("UNLIKE message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.PING:
            if "USER_ID" not in message.fields:
                message.validation_errors.append("PING message missing USER_ID")
                message.is_valid = False

        elif message.message_type == MessageType.ACK:
            if "MESSAGE_ID" not in message.fields:
                message.validation_errors.append("ACK message missing MESSAGE_ID")
                message.is_valid = False

        elif message.message_type == MessageType.GROUP_CREATE:
            if not all(k in message.fields for k in ["FROM", "GROUP_ID", "GROUP_NAME", "MEMBERS", "TIMESTAMP", "TOKEN"]):
                message.validation_errors.append("GROUP_CRREATE message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.GROUP_MESSAGE:
            if not all(k in message.fields for k in ["FROM", "GROUP_ID", "CONTENT", "TIMESTAMP", "TOKEN"]):
                message.validation_errors.append("GROUP_MESSAGE message missing required fields")
                message.is_valid = False

        elif message.message_type == MessageType.GROUP_UPDATE:
            required_fields = ["FROM", "GROUP_ID", "TIMESTAMP", "TOKEN"]
    
            if not all(k in message.fields for k in required_fields):
                message.validation_errors.append("GROUP_UPDATE message missing required fields")
                message.is_valid = False

            if "ADD" not in message.fields and "REMOVE" not in message.fields:
                message.validation_errors.append("GROUP_UPDATE must include ADD and/or REMOVE")
                message.is_valid = False

        elif message.message_type == MessageType.REVOKE:
            if not all(k in message.fields for k in ["TOKEN"]):
                message.validation_errors.append("REVOKE message missing required fields")
                message.is_valid = False
            
        else:
            # Unknown or unsupported type
            message.validation_errors.append("Unsupported or unknown message type")
            message.is_valid = False

        if not message.is_valid and self.verbose_mode:
            print(f">> [DEBUG - Parser] Message type {message.message_type.value} validation failed: {message.validation_errors}")


    def format_message_output(self, message: ParsedMessage, peer_profiles: Dict, current_verbose_mode: bool) -> str:
        """
        Format the parsed message for display based on verbose mode.
        peer_profiles: {user_id: (display_name, ip, status)}
        current_verbose_mode: The verbose setting from LSNPPeer
        """
        timestamp_str = time.strftime('[%H:%M:%S]', time.localtime(message.timestamp))
        
        if current_verbose_mode:
            # In verbose mode, include timestamp, sender IP, and message type in each log entry.
            # And then all fields.
            output_lines = [
                f"{timestamp_str} {message.message_type.value} from IP: {message.sender_ip}"
            ]
            for key, value in message.fields.items():
                output_lines.append(f"  {key}: {value}")
            return "\n".join(output_lines)
        else: # Non-verbose mode
            msg_type = message.message_type
            
            if msg_type == MessageType.PROFILE:
                display_name = message.fields.get("DISPLAY_NAME")
                status = message.fields.get("STATUS", "N/A")
                if not display_name:
                    user_id = message.fields.get("USER_ID", "Unknown")
                    display_name = user_id.split('@')[0] if '@' in user_id else user_id
                return f"{timestamp_str} {display_name}: {status}"
            
            elif msg_type == MessageType.POST:
                # post: Show only the display_name (user_id if display name is not recorded) and content.
                sender_user_id = message.fields.get("FROM")
                display_name = message.get_display_name(peer_profiles)
                content = message.fields.get("CONTENT", "")
                return f"{timestamp_str} POST from {display_name}: {content}"
            
            elif msg_type == MessageType.DM:
                # dm: Show only the display_name (user_id if display name is not recorded) and content
                sender_user_id = message.fields.get("FROM")
                display_name = message.get_display_name(peer_profiles)
                content = message.fields.get("CONTENT", "")
                return f"{timestamp_str} DM from {display_name}: {content}"
            
            elif msg_type == MessageType.PING:
                # ping: do not display anything
                return ""
            
            elif msg_type == MessageType.ACK:
                # ack: do not display anything (handled by verbose log in LSNPPeer)
                return ""
            
            elif msg_type == MessageType.FOLLOW:
                # final: “User alice has followed you”
                follower_user_id = message.fields.get("FROM")
                follower_display_name = message.get_display_name(peer_profiles)

                return f"{timestamp_str} User {follower_display_name} has followed you"
            
            elif msg_type == MessageType.UNFOLLOW:
                # final: “User alice has unfollowed you”
                follower_user_id = message.fields.get("FROM")
                follower_display_name = message.get_display_name(peer_profiles)

                return f"{timestamp_str} User {follower_display_name} has unfollowed you"
            
            elif msg_type == MessageType.GROUP_CREATE:
                # final: "You’ve been added to Trip Buddies"
                group_name = message.fields.get("GROUP_NAME")

                return f"{timestamp_str} You've been added to {group_name}"
            
            elif msg_type == MessageType.GROUP_MESSAGE:
                # final: "bob@192.168.1.12 sent “Just uploaded the photos!”
                sender = message.fields.get("FROM")
                content = message.fields.get("CONTENT")

                return f"{timestamp_str} {sender} send \"{content}\""
            
            elif msg_type == MessageType.GROUP_UPDATE:
                # final: The group “Trip Buddies” member list was updated.
                group_name = message.fields.get("GROUP_NAME")

                return f"{timestamp_str} The group \"{group_name}\" member list was updated."
            
            elif msg_type == MessageType.REVOKE:
                # final: do not display anything (handled by verbose log in LSNPPeer)
                return ""
            
            else:
                # Default for unknown or unhandled types in non-verbose, or messages not meant for display
                return ""