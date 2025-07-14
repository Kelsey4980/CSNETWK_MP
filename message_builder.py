"""
LSNP Message Builder
Handles construction of all LSNP message types according to RFC specifications
"""

import time
import secrets
from typing import Optional, List, Dict, Any
from dictionary import MessageType, ttl

class MessageBuilder:
    """
    Message builder for LSNP protocol
    Constructs properly formatted messages according to RFC specifications
    """
    
    def __init__(self, user_id: str, display_name: str):
        self.user_id = user_id
        self.display_name = display_name
        self.token_cache = {}  # Cache tokens to avoid regeneration
    
    def generate_message_id(self) -> str:
        """Generate a unique message ID"""
        return secrets.token_hex(8)
    
    def generate_token(self, scope: str = "chat", ttl_seconds: int = None) -> str:
        """
        Generate a token for message authentication
        Format: user_id|expiry_timestamp|scope
        """
        if ttl_seconds is None:
            ttl_seconds = ttl
        
        expiry = int(time.time()) + ttl_seconds
        token = f"{self.user_id}|{expiry}|{scope}"
        
        # Cache the token
        self.token_cache[scope] = token
        
        return token
    
    def get_cached_token(self, scope: str = "chat") -> Optional[str]:
        """Get cached token if valid, otherwise generate new one"""
        if scope in self.token_cache:
            token = self.token_cache[scope]
            try:
                _, expiry_str, _ = token.split('|')
                expiry = int(expiry_str)
                if time.time() < expiry - 60:  # Use if more than 1 minute left
                    return token
            except (ValueError, IndexError):
                pass
        
        return self.generate_token(scope)
    
    def build_profile(self, status: str = "") -> str:
        """
        Build a PROFILE message
        """
        message_parts = [
            f"TYPE: PROFILE",
            f"USER_ID: {self.user_id}",
            f"DISPLAY_NAME: {self.display_name}"
        ]
        
        if status:
            message_parts.append(f"STATUS: {status}")
        
        message_parts.append("")  # Empty line at end
        return "\n".join(message_parts)
    
    def build_post(self, content: str, ttl_seconds: int = None) -> str:
        """
        Build a POST message
        """
        if ttl_seconds is None:
            ttl_seconds = ttl
        
        message_id = self.generate_message_id()
        token = self.get_cached_token("chat")
        
        message_parts = [
            f"TYPE: POST",
            f"USER_ID: {self.user_id}",
            f"CONTENT: {content}",
            f"TTL: {ttl_seconds}",
            f"MESSAGE_ID: {message_id}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_dm(self, to_user_id: str, content: str) -> str:
        """
        Build a DM (Direct Message) message
        """
        message_id = self.generate_message_id()
        token = self.get_cached_token("direct")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: DM",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"CONTENT: {content}",
            f"TIMESTAMP: {timestamp}",
            f"MESSAGE_ID: {message_id}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_follow(self, to_user_id: str) -> str:
        """
        Build a FOLLOW message
        """
        message_id = self.generate_message_id()
        token = self.get_cached_token("follow")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: FOLLOW",
            f"MESSAGE_ID: {message_id}",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_unfollow(self, to_user_id: str) -> str:
        """
        Build an UNFOLLOW message
        """
        message_id = self.generate_message_id()
        token = self.get_cached_token("follow")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: UNFOLLOW",
            f"MESSAGE_ID: {message_id}",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_like(self, to_user_id: str, post_timestamp: int, action: str = "LIKE") -> str:
        """
        Build a LIKE message
        """
        token = self.get_cached_token("chat")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: LIKE",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"POST_TIMESTAMP: {post_timestamp}",
            f"ACTION: {action}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_ping(self) -> str:
        """
        Build a PING message
        """
        message_parts = [
            f"TYPE: PING",
            f"USER_ID: {self.user_id}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_ack(self, message_id: str, status: str = "RECEIVED") -> str:
        """
        Build an ACK message
        """
        message_parts = [
            f"TYPE: ACK",
            f"MESSAGE_ID: {message_id}",
            f"STATUS: {status}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_revoke(self, token: str) -> str:
        """
        Build a REVOKE message
        """
        message_parts = [
            f"TYPE: REVOKE",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_file_offer(self, to_user_id: str, filename: str, filesize: int, 
                        filetype: str, file_id: str = None) -> str:
        """
        Build a FILE_OFFER message
        """
        if file_id is None:
            file_id = self.generate_message_id()
        
        token = self.get_cached_token("file")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: FILE_OFFER",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"FILENAME: {filename}",
            f"FILESIZE: {filesize}",
            f"FILETYPE: {filetype}",
            f"FILEID: {file_id}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_file_chunk(self, to_user_id: str, file_id: str, chunk_index: int,
                        total_chunks: int, chunk_size: int, data: str) -> str:
        """
        Build a FILE_CHUNK message
        """
        token = self.get_cached_token("file")
        
        message_parts = [
            f"TYPE: FILE_CHUNK",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"FILEID: {file_id}",
            f"CHUNK_INDEX: {chunk_index}",
            f"TOTAL_CHUNKS: {total_chunks}",
            f"CHUNK_SIZE: {chunk_size}",
            f"TOKEN: {token}",
            f"DATA: {data}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_file_received(self, to_user_id: str, file_id: str, status: str = "RECEIVED") -> str:
        """
        Build a FILE_RECEIVED message
        """
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: FILE_RECEIVED",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"FILEID: {file_id}",
            f"STATUS: {status}",
            f"TIMESTAMP: {timestamp}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_group_create(self, group_id: str, group_name: str, members: List[str]) -> str:
        """
        Build a GROUP_CREATE message
        """
        token = self.get_cached_token("group")
        timestamp = int(time.time())
        members_str = ','.join(members)
        
        message_parts = [
            f"TYPE: GROUP_CREATE",
            f"FROM: {self.user_id}",
            f"GROUP_ID: {group_id}",
            f"GROUP_NAME: {group_name}",
            f"MEMBERS: {members_str}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_group_update(self, group_id: str, action: str = "UPDATE", 
                          members: List[str] = None) -> str:
        """
        Build a GROUP_UPDATE message
        """
        token = self.get_cached_token("group")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: GROUP_UPDATE",
            f"FROM: {self.user_id}",
            f"GROUP_ID: {group_id}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}"
        ]
        
        if members:
            members_str = ','.join(members)
            message_parts.append(f"MEMBERS: {members_str}")
        
        message_parts.append("")
        return "\n".join(message_parts)
    
    def build_group_message(self, group_id: str, content: str) -> str:
        """
        Build a GROUP_MESSAGE message
        """
        token = self.get_cached_token("group")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: GROUP_MESSAGE",
            f"FROM: {self.user_id}",
            f"GROUP_ID: {group_id}",
            f"CONTENT: {content}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_tictactoe_invite(self, to_user_id: str, game_id: str, symbol: str) -> str:
        """
        Build a TICTACTOE_INVITE message
        """
        message_id = self.generate_message_id()
        token = self.get_cached_token("game")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: TICTACTOE_INVITE",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"GAMEID: {game_id}",
            f"MESSAGE_ID: {message_id}",
            f"SYMBOL: {symbol}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_tictactoe_move(self, to_user_id: str, game_id: str, position: int,
                            symbol: str, turn: int) -> str:
        """
        Build a TICTACTOE_MOVE message
        """
        message_id = self.generate_message_id()
        token = self.get_cached_token("game")
        
        message_parts = [
            f"TYPE: TICTACTOE_MOVE",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"GAMEID: {game_id}",
            f"MESSAGE_ID: {message_id}",
            f"POSITION: {position}",
            f"SYMBOL: {symbol}",
            f"TURN: {turn}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_tictactoe_result(self, to_user_id: str, game_id: str, result: str, 
                              symbol: str) -> str:
        """
        Build a TICTACTOE_RESULT message
        """
        message_id = self.generate_message_id()
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: TICTACTOE_RESULT",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"GAMEID: {game_id}",
            f"MESSAGE_ID: {message_id}",
            f"RESULT: {result}",
            f"SYMBOL: {symbol}",
            f"TIMESTAMP: {timestamp}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_custom_message(self, message_type: str, fields: Dict[str, Any]) -> str:
        """
        Build a custom message with arbitrary fields
        Useful for testing or extending the protocol
        """
        message_parts = [f"TYPE: {message_type}"]
        
        for key, value in fields.items():
            if key != "TYPE":  # Avoid duplicate TYPE field
                message_parts.append(f"{key}: {value}")
        
        message_parts.append("")
        return "\n".join(message_parts)
    
    def update_user_info(self, user_id: str = None, display_name: str = None):
        """
        Update user information for future messages
        """
        if user_id:
            self.user_id = user_id
        if display_name:
            self.display_name = display_name
        
        # Clear token cache when user info changes
        self.token_cache.clear()
    
    def clear_token_cache(self):
        """Clear all cached tokens"""
        self.token_cache.clear()
    
    def get_token_info(self, scope: str = "chat") -> Dict[str, Any]:
        """
        Get information about a cached token
        """
        if scope not in self.token_cache:
            return {"exists": False}
        
        token = self.token_cache[scope]
        try:
            user_id, expiry_str, token_scope = token.split('|')
            expiry = int(expiry_str)
            
            return {
                "exists": True,
                "user_id": user_id,
                "expiry": expiry,
                "scope": token_scope,
                "expires_in": expiry - int(time.time()),
                "is_valid": time.time() < expiry
            }
        except (ValueError, IndexError):
            return {"exists": True, "valid": False, "error": "Invalid token format"}
    
    def validate_message_format(self, message: str) -> Dict[str, Any]:
        """
        Validate that a built message follows proper LSNP format
        """
        lines = message.strip().split('\n')
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not lines:
            validation_result["valid"] = False
            validation_result["errors"].append("Empty message")
            return validation_result
        
        # Check for TYPE field
        if not lines[0].startswith("TYPE: "):
            validation_result["valid"] = False
            validation_result["errors"].append("Missing TYPE field")
        
        # Check for proper field format
        for i, line in enumerate(lines):
            if line.strip() == "":
                continue
            
            if ':' not in line:
                validation_result["warnings"].append(f"Line {i+1} doesn't follow 'FIELD: value' format")
            else:
                field, value = line.split(':', 1)
                field = field.strip()
                value = value.strip()
                
                if not field:
                    validation_result["errors"].append(f"Line {i+1} has empty field name")
                if not value and field != "STATUS":  # STATUS can be empty
                    validation_result["warnings"].append(f"Line {i+1} has empty value for field {field}")
        
        return validation_result