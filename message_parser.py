"""
LSNP Message Parser and Handler
Handles parsing of all LSNP message types and provides debugging output
"""
import time
import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
from dictionary import MessageType

@dataclass
class LSNPMessage:
    """
    Base class for all LSNP messages
    Handles parsing and validation of message structure
    """
    message_type: MessageType
    raw_message: str
    fields: Dict[str, str]
    sender_ip: str = ""
    timestamp: float = 0.0
    is_valid: bool = True
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def validate_token(self) -> bool:
        """Validate token structure and expiration with better error handling"""
        if "TOKEN" not in self.fields:
            print(f"[DEBUG] Token check: No TOKEN field for {self.message_type.value}")
            return True  # Not all messages require tokens
        
        token = self.fields["TOKEN"]
        if not token:
            self.validation_errors.append("Empty token field")
            print(f"[DEBUG] Token check: Empty token for {self.message_type.value}")
            return False
            
        try:
            parts = token.split('|')
            if len(parts) != 3:
                self.validation_errors.append(f"Invalid token format: expected 3 parts, got {len(parts)}")
                print(f"[DEBUG] Token check: Invalid token format '{token}'")
                return False
            
            user_id, expiry_str, scope = parts
            
            # Validate user_id format
            if not user_id or '@' not in user_id:
                self.validation_errors.append("Invalid user_id format in token")
                print(f"[DEBUG] Token check: Invalid token format '{token}'")
                return False
            
            # Validate expiry is numeric
            if not expiry_str.isdigit():
                self.validation_errors.append("Token expiry must be numeric")
                print(f"[DEBUG] Token check: Expiry not numeric '{expiry_str}'")
                return False
                
            expiry = int(expiry_str)
            
            # Check if token is expired
            if time.time() > expiry:
                self.validation_errors.append("Token expired")
                print(f"[DEBUG] Token check: Token EXPIRED for {self.message_type.value}. Current time: {time.time()}, Expiry: {expiry}")
                return False
                
            # Validate scope according to RFC
            valid_scopes = ["chat", "file", "broadcast", "follow", "game", "group", "direct"]
            if scope not in valid_scopes:
                self.validation_errors.append(f"Invalid token scope: {scope}")
                print(f"[DEBUG] Token check: Invalid scope '{scope}'")
                return False
                
            return True
            
        except (ValueError, IndexError) as e:
            self.validation_errors.append(f"Token parsing error: {e}")
            return False
    
    def get_display_name(self, peer_profiles: Dict) -> str:
        """Get display name for user, fallback to USER_ID"""
        user_id = self.fields.get("USER_ID") or self.fields.get("FROM")
        if user_id and user_id in peer_profiles:
            return peer_profiles[user_id][0]
        return user_id or "Unknown User"
    
    def to_debug_string(self) -> str:
        """Generate detailed debug output"""
        debug_lines = [
            f"=== MESSAGE DEBUG INFO ===",
            f"Type: {self.message_type.value}",
            f"Sender IP: {self.sender_ip}",
            f"Timestamp: {time.ctime(self.timestamp)}",
            f"Valid: {self.is_valid}",
        ]
        
        if self.validation_errors:
            debug_lines.append(f"Validation Errors: {', '.join(self.validation_errors)}")
        
        debug_lines.append("Fields:")
        for key, value in self.fields.items():
            debug_lines.append(f"  {key}: {value}")
        
        debug_lines.append("=== END DEBUG INFO ===")
        return "\n".join(debug_lines)

class MessageParser:
    """
    Main parser class for LSNP messages
    Handles parsing, validation, and formatting of all message types
    """
    
    def __init__(self, verbose_mode: bool = False):
        self.verbose_mode = verbose_mode
        self.message_storage = {}  # Store messages with valid tokens
        
    def parse_message(self, raw_message: str, sender_ip: str = "") -> LSNPMessage:
        """
        Parse a raw LSNP message into a structured LSNPMessage object
        """
        fields = self._extract_fields(raw_message)
        
        # Determine message type
        message_type_str = fields.get("TYPE", "").upper()
        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            message_type = MessageType.PING  # Default fallback
            
        # Create message object
        message = LSNPMessage(
            message_type=message_type,
            raw_message=raw_message,
            fields=fields,
            sender_ip=sender_ip
        )
        
        # Validate message
        self._validate_message(message)
        
        # Store message if it has a valid token OR if it's a PROFILE message
        if (message.validate_token() and "MESSAGE_ID" in fields) or message.message_type == MessageType.PROFILE:
            # Use a fallback ID for PROFILE messages without MESSAGE_ID
            storage_id = fields.get("MESSAGE_ID", f"profile_{message.sender_ip}_{int(message.timestamp)}")
            
            if storage_id in self.message_storage:
                if self.verbose_mode:
                    print(f">> [INFO] Duplicate message detected for ID: {storage_id}. Overwriting existing entry.\n")
            
            self.message_storage[storage_id] = message
            
        return message
    
    def _extract_fields(self, raw_message: str) -> Dict[str, str]:
        """Extract key-value pairs from raw message with improved validation"""
        fields = {}
        lines = raw_message.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Validate field name format
                if not key or not key.replace('_', '').isalnum():
                    continue  # Skip invalid field names
                    
                fields[key] = value
            else:
                # Handle malformed lines
                if self.verbose_mode:
                    print(f"Warning: Malformed line {line_num}: {line}")
                    
        return fields
    
    def _validate_message(self, message: LSNPMessage):
        """Validate message structure based on type with detailed error reporting"""
        required_fields = self._get_required_fields(message.message_type)
        
        # Check for missing required fields
        missing_fields = []
        for field in required_fields:
            if field not in message.fields:
                missing_fields.append(field)
        
        if missing_fields:
            message.validation_errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            message.is_valid = False
        
        # Check for empty required fields
        empty_fields = []
        for field in required_fields:
            if field in message.fields and not message.fields[field]:
                empty_fields.append(field)
        
        if empty_fields:
            message.validation_errors.append(f"Empty required fields: {', '.join(empty_fields)}")
            message.is_valid = False
        
        # Type-specific validation
        if message.message_type == MessageType.POST:
            content = message.fields.get("CONTENT", "")
            if len(content) > 500:
                message.validation_errors.append("Post content exceeds 500 characters")
                message.is_valid = False
            
            # Validate TTL is numeric
            ttl = message.fields.get("TTL", "")
            if ttl and not ttl.isdigit():
                message.validation_errors.append("TTL must be numeric")
                message.is_valid = False
                
        elif message.message_type == MessageType.DM:
            # Validate DM specific fields
            if "TO" not in message.fields:
                message.validation_errors.append("DM missing TO field")
                message.is_valid = False
            
            # Validate TIMESTAMP is numeric
            timestamp = message.fields.get("TIMESTAMP", "")
            if timestamp and not timestamp.isdigit():
                message.validation_errors.append("TIMESTAMP must be numeric")
                message.is_valid = False
        
        elif message.message_type == MessageType.FILE_OFFER:
            # Validate file size is numeric
            filesize = message.fields.get("FILESIZE", "")
            if filesize and not filesize.isdigit():
                message.validation_errors.append("FILESIZE must be numeric")
                message.is_valid = False
        
        elif message.message_type == MessageType.FILE_CHUNK:
            # Validate chunk fields are numeric
            numeric_fields = ["CHUNK_INDEX", "TOTAL_CHUNKS", "CHUNK_SIZE"]
            for field in numeric_fields:
                value = message.fields.get(field, "")
                if value and not value.isdigit():
                    message.validation_errors.append(f"{field} must be numeric")
                    message.is_valid = False

    def _get_required_fields(self, message_type: MessageType) -> List[str]:
        """Get required fields for each message type based on RFC"""
        required_fields_map = {
            MessageType.PROFILE: ["TYPE", "USER_ID", "DISPLAY_NAME"],
            MessageType.POST: ["TYPE", "USER_ID", "CONTENT", "TTL", "MESSAGE_ID", "TOKEN"],
            MessageType.DM: ["TYPE", "FROM", "TO", "CONTENT", "TIMESTAMP", "MESSAGE_ID", "TOKEN"],
            MessageType.PING: ["TYPE", "USER_ID"],
            MessageType.ACK: ["TYPE", "MESSAGE_ID", "STATUS"],
            MessageType.FOLLOW: ["TYPE", "MESSAGE_ID", "FROM", "TO", "TIMESTAMP", "TOKEN"],
            MessageType.UNFOLLOW: ["TYPE", "MESSAGE_ID", "FROM", "TO", "TIMESTAMP", "TOKEN"],
            MessageType.FILE_OFFER: ["TYPE", "FROM", "TO", "FILENAME", "FILESIZE", "FILETYPE", "FILEID", "TIMESTAMP", "TOKEN"],
            MessageType.FILE_CHUNK: ["TYPE", "FROM", "TO", "FILEID", "CHUNK_INDEX", "TOTAL_CHUNKS", "CHUNK_SIZE", "TOKEN", "DATA"],
            MessageType.FILE_RECEIVED: ["TYPE", "FROM", "TO", "FILEID", "STATUS", "TIMESTAMP"],
            MessageType.REVOKE: ["TYPE", "TOKEN"],
            MessageType.LIKE: ["TYPE", "FROM", "TO", "POST_TIMESTAMP", "ACTION", "TIMESTAMP", "TOKEN"],
            MessageType.GROUP_CREATE: ["TYPE", "FROM", "GROUP_ID", "GROUP_NAME", "MEMBERS", "TIMESTAMP", "TOKEN"],
            MessageType.GROUP_UPDATE: ["TYPE", "FROM", "GROUP_ID", "TIMESTAMP", "TOKEN"],
            MessageType.GROUP_MESSAGE: ["TYPE", "FROM", "GROUP_ID", "CONTENT", "TIMESTAMP", "TOKEN"],
            MessageType.TICTACTOE_INVITE: ["TYPE", "FROM", "TO", "GAMEID", "MESSAGE_ID", "SYMBOL", "TIMESTAMP", "TOKEN"],
            MessageType.TICTACTOE_MOVE: ["TYPE", "FROM", "TO", "GAMEID", "MESSAGE_ID", "POSITION", "SYMBOL", "TURN", "TOKEN"],
            MessageType.TICTACTOE_RESULT: ["TYPE", "FROM", "TO", "GAMEID", "MESSAGE_ID", "RESULT", "SYMBOL", "TIMESTAMP"],
        }
        
        return required_fields_map.get(message_type, ["TYPE"])
    
    def format_message_output(self, message: LSNPMessage, peer_profiles: Dict) -> str:
        """
        Format message for display based on verbose mode
        """
        if self.verbose_mode:
            return self._format_verbose_output(message)
        else:
            return self._format_non_verbose_output(message, peer_profiles)
    
    def _format_verbose_output(self, message: LSNPMessage) -> str:
        """Format message for verbose output (shows all fields)"""
        return f"[VERBOSE] {message.message_type.value}\n{message.raw_message}"
    
    def _format_non_verbose_output(self, message: LSNPMessage, peer_profiles: Dict) -> str:
        """Format message for non-verbose output (user-friendly) according to RFC"""
        display_name = message.get_display_name(peer_profiles)
        
        if message.message_type == MessageType.PROFILE:
            status = message.fields.get("STATUS", "")
            return f"[PROFILE]\n\t{display_name}: {status}\n"
            
        elif message.message_type == MessageType.POST:
            content = message.fields.get("CONTENT", "")
            return f"[POST]\n\tFrom: {display_name}\n\tContent: {content}\n"
            
        elif message.message_type == MessageType.DM:
            content = message.fields.get("CONTENT", "")
            return f"[DM]\n\t{display_name}: {content}\n"
            
        elif message.message_type == MessageType.FOLLOW:
            from_user = message.fields.get("FROM", "")
            return f"[FOLLOW]\n\tUser {from_user} has followed you\n"
            
        elif message.message_type == MessageType.UNFOLLOW:
            from_user = message.fields.get("FROM", "")
            return f"[UNFOLLOW]\n\tUser {from_user} has unfollowed you\n"
            
        elif message.message_type == MessageType.LIKE:
            from_user = message.fields.get("FROM", "")
            post_timestamp = message.fields.get("POST_TIMESTAMP", "")
            return f"[LIKE]\n\t{from_user} likes your post [post {post_timestamp} message]\n"
            
        elif message.message_type == MessageType.FILE_OFFER:
            from_user = message.fields.get("FROM", "")
            return f"[FILE_OFFER]\n\tUser {from_user} is sending you a file do you accept?\n"
            
        elif message.message_type == MessageType.FILE_CHUNK:
            # RFC says: "Do not print anything until all the chunks are completed"
            return ""
            
        elif message.message_type == MessageType.FILE_RECEIVED:
            # RFC says: "Do not print anything"
            return ""
            
        elif message.message_type == MessageType.REVOKE:
            # RFC says: "Do not print anything"
            return ""
            
        elif message.message_type == MessageType.TICTACTOE_INVITE:
            from_user = message.fields.get("FROM", "")
            return f"[TICTACTOE_INVITE]\n\t{from_user} is inviting you to play tic-tac-toe.\n"
            
        elif message.message_type == MessageType.TICTACTOE_MOVE:
            # RFC says: "Print the board"
            return f"[TICTACTOE_MOVE]\n\tPrint the board.\n"
            
        elif message.message_type == MessageType.TICTACTOE_RESULT:
            # RFC says: "Print only the board and whose turn it is"
            return f"[TICTACTOE_RESULT]\n\tPrint only the board and whose turn it is.\n"
            
        elif message.message_type == MessageType.GROUP_CREATE:
            group_name = message.fields.get("GROUP_NAME", "")
            return f"[GROUP_CREATE]\n\tYou've been added to {group_name}\n"
            
        elif message.message_type == MessageType.GROUP_UPDATE:
            group_name = message.fields.get("GROUP_NAME", "Unknown Group")
            return f"[GROUP_UPDATE]\n\tThe group \"{group_name}\" member list was updated.\n"
            
        elif message.message_type == MessageType.GROUP_MESSAGE:
            from_user = message.fields.get("FROM", "")
            content = message.fields.get("CONTENT", "")
            return f"[GROUP_MESSAGE]\n\t{from_user} sent \"{content}\"\n"
            
        elif message.message_type == MessageType.PING:
            # RFC says: "Do not display anything"
            return ""
            
        elif message.message_type == MessageType.ACK:
            # RFC says: "Do not display anything"
            return ""
            
        else:
            return f"[{message.message_type.value}]\n\tFrom: {display_name}\n"
    
    def get_stored_messages(self) -> Dict[str, LSNPMessage]:
        """Get all stored messages with valid tokens"""
        return self.message_storage.copy()
    
    def get_messages_by_type(self, message_type: MessageType) -> List[LSNPMessage]:
        """Get all stored messages of a specific type"""
        return [msg for msg in self.message_storage.values() 
                if msg.message_type == message_type]
    
    def get_posts_by_user(self, user_id: str) -> List[LSNPMessage]:
        """Get all posts by a specific user"""
        return [msg for msg in self.message_storage.values() 
                if msg.message_type == MessageType.POST 
                and msg.fields.get("USER_ID") == user_id]
    
    def get_dms_by_user(self, user_id: str) -> List[LSNPMessage]:
        """Get all DMs from a specific user"""
        return [msg for msg in self.message_storage.values() 
                if msg.message_type == MessageType.DM 
                and msg.fields.get("FROM") == user_id]
    
    def print_all_messages_summary(self):
        """Print summary of all stored messages"""
        print("\n=== STORED MESSAGES SUMMARY ===")
        type_counts = {}
        for msg in self.message_storage.values():
            msg_type = msg.message_type.value
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        for msg_type, count in type_counts.items():
            print(f"{msg_type}: {count}")
        
        print(f"Total messages: {len(self.message_storage)}")
        print("===============================\n")