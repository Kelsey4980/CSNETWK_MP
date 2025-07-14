# ====== Import Modules
import time
from enum import Enum
from typing import Dict, Optional, List
import dictionary

class MessageType(Enum):
    """Enumeration of LSNP message types"""
    PROFILE = "PROFILE"
    POST = "POST"
    DM = "DM"
    FOLLOW = "FOLLOW"
    PING = "PING"
    PONG = "PONG"
    ACK = "ACK"
    UNKNOWN = "UNKNOWN"

class ParsedMessage:
    """
    Represents a parsed LSNP message
    Simplified for real-time processing without storage
    """
    def __init__(self, raw_message: str, sender_ip: str):
        self.raw_message = raw_message
        self.sender_ip = sender_ip
        self.timestamp = time.time()
        self.message_type = MessageType.UNKNOWN
        self.fields = {}
        self.is_valid = False # Initially assume invalid
        self.validation_errors = []
        
    def get_display_name(self, peer_profiles: Dict) -> str:
        """Get display name for message sender"""
        user_id = self.fields.get("USER_ID")
        if user_id and user_id in peer_profiles:
            return peer_profiles[user_id][0]  # display_name is first element
        # Fallback to DISPLAY_NAME in fields or a default
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
    """
    LSNP Message Parser - Real-time processing without storage
    Parses and validates messages according to LSNP RFC specifications
    """
    
    def __init__(self, verbose_mode: bool = False):
        self.verbose_mode = verbose_mode
        self.processed_count = 0
        self.invalid_count = 0
        
    def get_processed_count(self) -> int:
        """Get count of processed messages"""
        return self.processed_count
    
    def get_invalid_count(self) -> int:
        """Get count of invalid messages"""
        return self.invalid_count
    
    def parse_message(self, raw_message: str, sender_ip: str) -> Optional[ParsedMessage]:
        """Parse a raw LSNP message into a ParsedMessage object"""
        self.processed_count += 1
        
        message = ParsedMessage(raw_message, sender_ip) # Initially message.is_valid = False
        
        if self.verbose_mode:
            print(f">> [DEBUG - Parser] Attempting to parse raw message from {sender_ip}:")
            print("----------------------------------------")
            print(raw_message.strip()) # Print stripped to see actual content
            print("----------------------------------------")

        try:
            # Parse message fields
            self._parse_fields(message)
            
            # Determine message type. If TYPE is not found or invalid,
            # _determine_message_type will mark message.validation_errors and set to UNKNOWN.
            self._determine_message_type(message)

            # --- Critical Change: Check for fundamental parsing failure early ---
            # If after _parse_fields and _determine_message_type, we still have UNKNOWN type
            # and no USER_ID (for ping/pong/ack which might not always have full profile),
            # it's likely a malformed message that can't even be categorized.
            # You might need to adjust this condition based on your exact RFC for minimal messages.
            if message.message_type == MessageType.UNKNOWN and "TYPE" not in message.fields:
                if self.verbose_mode:
                    print(f">> [WARNING - Parser] Message has no recognizable TYPE field. Returning None.")
                self.invalid_count += 1
                return None # Completely unparseable message

            # Validate message based on its determined type
            self._validate_message(message)
            
            if not message.is_valid:
                self.invalid_count += 1
                if self.verbose_mode:
                    print(f">> [DEBUG - Parser] Message is invalid after validation: {message.validation_errors}. Returning None.")
                return None # Return None if validation fails
                
        except Exception as e:
            # Catch any unexpected errors during parsing or validation
            message.validation_errors.append(f"Critical parsing error: {str(e)}")
            message.is_valid = False
            self.invalid_count += 1
            if self.verbose_mode:
                print(f">> [ERROR - Parser] Exception during parsing: {e}. Returning None.")
                print(message.to_debug_string()) # Print debug info for the failed parse
            return None # Return None if an exception occurred

        # If we reach here, the message was successfully parsed and validated, or
        # it was a valid message that just didn't meet certain criteria for "is_valid"
        # but is still a ParsedMessage object that can be processed further by utilities.
        # This part of the code determines what a 'successful parse' means for you.
        # Given your 'Error: Could not parse message...' output, we want to return None
        # for anything that's not fully usable.
        
        # The previous logic was fine if the ParsedMessage object itself carried the validity
        # but the `lsnp_peer` code explicitly checked for `None`.
        # So, if message.is_valid is False at this point, it means it didn't pass specific
        # type validation checks. We should still return None to align with the `lsnp_peer` logic.
        if not message.is_valid:
            return None

        return message # Only return ParsedMessage object if it's considered valid

    def _parse_fields(self, message: ParsedMessage):
        """Parse message fields from raw message"""
        lines = message.raw_message.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                message.fields[key.strip()] = value.strip()
            # If a line doesn't contain ':', it might be actual content (like for POST/DM)
            # or simply a malformed header line. Your current logic just skips it.
            # You might need more sophisticated content parsing depending on your RFC.
            # For now, let's assume content is correctly identified by a 'CONTENT:' header.
            elif self.verbose_mode:
                print(f">> [DEBUG - Parser] Skipping non-colon line in _parse_fields: '{line.strip()}'")
    
    def _determine_message_type(self, message: ParsedMessage):
        """Determine message type from parsed fields"""
        msg_type_str = message.fields.get("TYPE", "").strip().upper() # Get TYPE string
        
        if not msg_type_str: # If TYPE field is empty or missing
            message.message_type = MessageType.UNKNOWN
            message.validation_errors.append("Missing TYPE field in message header")
            return

        try:
            message.message_type = MessageType[msg_type_str] # Convert string to Enum member
        except KeyError: # If string doesn't match any enum member
            message.message_type = MessageType.UNKNOWN
            message.validation_errors.append(f"Unknown message type string: {msg_type_str}")
        
    def _validate_message(self, message: ParsedMessage):
        """Validate message according to LSNP RFC specifications"""
        # Assume valid initially, then invalidate if checks fail
        message.is_valid = True 
        
        msg_type = message.message_type
        
        # Common validation: If message type is UNKNOWN (from _determine_message_type)
        if msg_type == MessageType.UNKNOWN:
            # Error already added in _determine_message_type
            message.is_valid = False
            return
        
        # Type-specific validation
        if msg_type == MessageType.PROFILE:
            self._validate_profile_message(message)
        elif msg_type == MessageType.POST:
            self._validate_post_message(message)
        elif msg_type == MessageType.DM:
            self._validate_dm_message(message)
        elif msg_type == MessageType.FOLLOW:
            self._validate_follow_message(message)
        elif msg_type == MessageType.PING:
            self._validate_ping_message(message)
        elif msg_type == MessageType.PONG:
            self._validate_pong_message(message)
        elif msg_type == MessageType.ACK:
            self._validate_ack_message(message)
        else:
            # This case should ideally not be reached if _determine_message_type is robust,
            # but good for safety.
            message.validation_errors.append(f"No specific validation rules for message type: {msg_type.value}")
            message.is_valid = False # Mark as invalid if no validation rule applies
    
    def _validate_profile_message(self, message: ParsedMessage):
        """Validate PROFILE message"""
        required_fields = ["USER_ID", "DISPLAY_NAME"]
        
        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"PROFILE: Missing or empty required field: {field}")
                message.is_valid = False
        
        # Validate USER_ID format if it exists and is not already flagged as missing
        user_id = message.fields.get("USER_ID", "")
        if message.is_valid and user_id and '@' not in user_id: # Only check if not already invalid for missing
            message.validation_errors.append("PROFILE: USER_ID must be in format username@ip")
            message.is_valid = False
        
        # No explicit `message.is_valid = len(message.validation_errors) == 0` here
        # because we set message.is_valid = True at the start of _validate_message
        # and set it to False only if an error is found. This is a common pattern.
    
    def _validate_post_message(self, message: ParsedMessage):
        """Validate POST message"""
        required_fields = ["USER_ID", "CONTENT"]
        
        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"POST: Missing or empty required field: {field}")
                message.is_valid = False
    
    def _validate_dm_message(self, message: ParsedMessage):
        """Validate DM message"""
        required_fields = ["USER_ID", "TARGET_USER_ID", "CONTENT"]
        
        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"DM: Missing or empty required field: {field}")
                message.is_valid = False
    
    def _validate_follow_message(self, message: ParsedMessage):
        """Validate FOLLOW message"""
        required_fields = ["USER_ID", "TARGET_USER_ID"]
        
        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"FOLLOW: Missing or empty required field: {field}")
                message.is_valid = False
    
    def _validate_ping_message(self, message: ParsedMessage):
        """Validate PING message"""
        required_fields = ["USER_ID"]
        
        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"PING: Missing or empty required field: {field}")
                message.is_valid = False
    
    def _validate_pong_message(self, message: ParsedMessage):
        """Validate PONG message"""
        required_fields = ["USER_ID"]
        
        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"PONG: Missing or empty required field: {field}")
                message.is_valid = False
    
    def _validate_ack_message(self, message: ParsedMessage):
        """Validate ACK message"""
        required_fields = ["MESSAGE_ID", "STATUS"]

        for field in required_fields:
            if field not in message.fields or not message.fields[field].strip(): # Added .strip()
                message.validation_errors.append(f"ACK: Missing or empty required field: {field}")
                message.is_valid = False
        
        status = message.fields.get("STATUS", "").strip() # Added .strip()
        # Only check status if message is still considered valid so far to avoid redundant errors
        if message.is_valid and status not in ["RECEIVED", "ERROR", "NOT_FOUND"]: 
            message.validation_errors.append(f"ACK: Invalid STATUS value: {status}")
            message.is_valid = False
        
    def format_message_output(self, message: ParsedMessage, peer_profiles: Dict) -> str:
        """Format message for display output"""
        # If the message is truly invalid and verbose mode is off, return empty string
        # The 'is_valid' check here is now more reliable because parse_message will return None
        # for truly invalid messages that we don't want to display at all.
        if not message.is_valid and not self.verbose_mode:
            return "" 
        
        timestamp_str = time.strftime("%H:%M:%S", time.localtime(message.timestamp))
        display_name = message.get_display_name(peer_profiles)
        
        # If the message is invalid but verbose mode is ON, provide debug output
        if not message.is_valid and self.verbose_mode:
            return message.to_debug_string() + "\n" # Add a newline for better separation
            
        # Format based on message type
        if message.message_type == MessageType.PROFILE:
            return self._format_profile_output(message, timestamp_str, display_name)
        elif message.message_type == MessageType.POST:
            return self._format_post_output(message, timestamp_str, display_name)
        elif message.message_type == MessageType.DM:
            return self._format_dm_output(message, timestamp_str, display_name)
        elif message.message_type == MessageType.FOLLOW:
            return self._format_follow_output(message, timestamp_str, display_name)
        elif message.message_type == MessageType.PING:
            return self._format_ping_output(message, timestamp_str, display_name)
        elif message.message_type == MessageType.PONG:
            return self._format_pong_output(message, timestamp_str, display_name)
        elif message.message_type == MessageType.ACK:
            return self._format_ack_output(message, timestamp_str, display_name)
        else:
            # This handles MessageType.UNKNOWN which is now explicitly set during parsing failures.
            # If we reach here, it means it's an UNKNOWN type *but* was still passed through
            # from parse_message (which shouldn't happen with the new None returns).
            # This is a fallback, primarily for verbose debugging.
            if self.verbose_mode:
                return f"[{timestamp_str}] UNKNOWN MESSAGE from {display_name} (Type: {message.message_type.value})\n"
            return ""
    
    def _format_profile_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format PROFILE message output"""
        status = message.fields.get("STATUS", "")
        user_id = message.fields.get("USER_ID", "")
        
        status_text = f" (Status: {status})" if status else ""
        return f"[{timestamp_str}] PROFILE: {display_name} ({user_id}){status_text}\n"
    
    def _format_post_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format POST message output"""
        content = message.fields.get("CONTENT", "")
        return f"[{timestamp_str}] POST from {display_name}: {content}\n"
    
    def _format_dm_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format DM message output"""
        content = message.fields.get("CONTENT", "")
        target = message.fields.get("TARGET_USER_ID", "")
        return f"[{timestamp_str}] DM from {display_name} to {target}: {content}\n"
    
    def _format_follow_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format FOLLOW message output"""
        target = message.fields.get("TARGET_USER_ID", "")
        return f"[{timestamp_str}] FOLLOW: {display_name} wants to follow {target}\n"
    
    def _format_ping_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format PING message output"""
        return f"[{timestamp_str}] PING from {display_name}\n"
    
    def _format_pong_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format PONG message output"""
        return f"[{timestamp_str}] PONG from {display_name}\n"
    
    def _format_ack_output(self, message: ParsedMessage, timestamp_str: str, display_name: str) -> str:
        """Format ACK message output"""
        msg_id = message.fields.get("MESSAGE_ID", "")
        status = message.fields.get("STATUS", "")
        
        if self.verbose_mode:
            return f"[{timestamp_str}] ACK from {display_name}: {msg_id} ({status})\n"
        return "" # ACKs are usually not displayed unless in verbose mode