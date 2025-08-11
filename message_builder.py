"""
    SUBMITTED BY:
        CHING, Justin
        CHUA, Hanielle
        KELSEY, Gabrielle
        TOLENTINO, Hephzi

    CSNETWK S15
"""

import time
import secrets
from typing import Optional, Dict, Any
from enum import Enum
from dictionary import MessageType

# Default TTL configuration
DEFAULT_TTL = 3600  # 1 hour default

class MessageBuilder:
    """
    Message builder for core LSNP protocol types
    Constructs properly formatted messages according to RFC specifications
    """
    
    def __init__(self, user_id: str, display_name: str, avatar_data: str = None, avatar_type: str = None):
        self.user_id = user_id
        self.display_name = display_name
        self.avatar_data = avatar_data
        self.avatar_type = avatar_type
        self.token_cache = {}  # Cache tokens to avoid regeneration
    
    def generate_message_id(self) -> str:
        """Generate a unique message ID"""
        return secrets.token_hex(8)
    
    def generate_game_id(self) -> str:
        """Generate a unique game ID"""
        number = secrets.randbelow(256)  # Random number between 0 and 255
        return f"g{number:03d}"
    
    def generate_token(self, scope: str = "chat", ttl_seconds: int = None) -> str:
        """
        Generate a token for message authentication
        Format: user_id|expiry_timestamp|scope
        """
        if ttl_seconds is None:
            ttl_seconds = DEFAULT_TTL
        
        expiry = int(time.time()) + ttl_seconds
        token = f"{self.user_id}|{expiry}|{scope}"
        
        print(f"\n[DEBUG] Generated token for {scope}: {token}, expires at {time.ctime(expiry)}")
        return token
    
    def build_profile(self, status: str = "") -> str:
        """
        Build a PROFILE message
        Format: TYPE, USER_ID, DISPLAY_NAME, [STATUS]
        """
        message_parts = [
            f"TYPE: PROFILE",
            f"USER_ID: {self.user_id}",
            f"DISPLAY_NAME: {self.display_name}"
        ]
        
        if status:
            message_parts.append(f"STATUS: {status}")

        # for avatar
        if self.avatar_data and self.avatar_type:
            message_parts.append(f"AVATAR_TYPE: {self.avatar_type}")
            message_parts.append(f"AVATAR_ENCODING: base64")
            message_parts.append(f"AVATAR_DATA: {self.avatar_data}")
        
        message_parts.append("")  # Empty line at end
        return "\n".join(message_parts)
    
    def build_post(self, content: str, ttl_seconds: int = None) -> str:
        """
        Build a POST message
        Format: TYPE, USER_ID, CONTENT, TTL, MESSAGE_ID, TOKEN
        """
        if ttl_seconds is None:
            ttl_seconds = DEFAULT_TTL
        
        message_id = self.generate_message_id()
        token = self.generate_token("broadcast", ttl_seconds)
        
        message_parts = [
            f"TYPE: POST",
            f"USER_ID: {self.user_id}",
            f"CONTENT: {content}",
            f"TTL: {ttl_seconds}",
            f"MESSAGE_ID: {message_id}",
            f"TOKEN: {token}",
            ""
        ]

        # for avatar
        if self.avatar_data and self.avatar_type:
            message_parts.append(f"AVATAR_TYPE: {self.avatar_type}")
            message_parts.append(f"AVATAR_ENCODING: base64")
            message_parts.append(f"AVATAR_DATA: {self.avatar_data}")
        
        return "\n".join(message_parts)
    
    def build_dm(self, to_user_id: str, content: str) -> str:
        """
        Build a DM (Direct Message) message
        Format: TYPE, FROM, TO, CONTENT, TIMESTAMP, MESSAGE_ID, TOKEN
        """

        message_id = self.generate_message_id()
        token = self.generate_token("chat")
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

        # for avatar
        if self.avatar_data and self.avatar_type:
            message_parts.append(f"AVATAR_TYPE: {self.avatar_type}")
            message_parts.append(f"AVATAR_ENCODING: base64")
            message_parts.append(f"AVATAR_DATA: {self.avatar_data}")

        return "\n".join(message_parts)
    
    def build_follow(self, to_user_id: str) -> str:
        """
        Build a FOLLOW message
        Format: TYPE, MESSAGE_ID, FROM, TO, TIMESTAMP, TOKEN
        """
        message_id = self.generate_message_id()
        token = self.generate_token("follow")
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
        Format: TYPE, MESSAGE_ID, FROM, TO, TIMESTAMP, TOKEN
        """
        message_id = self.generate_message_id()
        token = self.generate_token("follow")
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
        Format: TYPE, FROM, TO, POST_TIMESTAMP, ACTION, TIMESTAMP, TOKEN
        """
        token = self.generate_token("broadcast")
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

    def build_unlike(self, to_user_id: str, post_timestamp: int, action: str = "UNLIKE") -> str:
        """
        Build an UNLIKE message
        Format: TYPE, FROM, TO, POST_TIMESTAMP, ACTION, TIMESTAMP, TOKEN
        """
        token = self.generate_token("broadcast")
        timestamp = int(time.time())

        message_parts = [
            f"TYPE: UNLIKE",
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
        Format: TYPE, USER_ID
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
        Format: TYPE, MESSAGE_ID, STATUS
        """
        message_parts = [
            f"TYPE: ACK",
            f"MESSAGE_ID: {message_id}",
            f"STATUS: {status}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_group_create(self, group_id, group_name, group_members, timestamp):
        """
        Build a GROUP_CREATE message
        Format: TYPE, FROM, GROUP_ID, GROUP_NAME, MEMBERS, TIMESTAMP, TOKEN
        """
        token = self.generate_token("group")
        message_parts = [
            f"TYPE: GROUP_CREATE",
            f"FROM: {self.user_id}",
            f"GROUP_ID: {group_id}",
            f"GROUP_NAME: {group_name}",
            f"MEMBERS: {group_members}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_group_message(self, group_id, content, timestamp):
        """
        Build a GROUP_MESSAGE message
        Format: TYPE, FROM, GROUP_ID, CONTENT, TIMESTAMP, TOKEN
        """
        token = self.generate_token("group")
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
    
    def build_group_update(self, group_id, add_members, remove_members, timestamp):
        """
        Build a GROUP_UPDATE message
        Format: TYPE, FROM, GROUP_ID, ADD, REMOVE, TOKEN
        """
        token = self.generate_token("group")

        if add_members and remove_members:
            message_parts = [
                f"TYPE: GROUP_UPDATE",
                f"FROM: {self.user_id}",
                f"GROUP_ID: {group_id}",
                f"ADD: {add_members}",
                f"REMOVE: {remove_members}",
                f"TIMESTAMP: {timestamp}",
                f"TOKEN: {token}",
                ""
            ]
        elif add_members:
            message_parts = [
                f"TYPE: GROUP_UPDATE",
                f"FROM: {self.user_id}",
                f"GROUP_ID: {group_id}",
                f"ADD: {add_members}",
                f"TIMESTAMP: {timestamp}",
                f"TOKEN: {token}",
                ""
            ]
        elif remove_members:
            message_parts = [
                f"TYPE: GROUP_UPDATE",
                f"FROM: {self.user_id}",
                f"GROUP_ID: {group_id}",
                f"REMOVE: {remove_members}",
                f"TIMESTAMP: {timestamp}",
                f"TOKEN: {token}",
                ""
            ]
        
        return "\n".join(message_parts)
    
    def build_revoke(self, token):
        """
        Build a REVOKE message
        Format: TYPE, TOKEN
        """

        message_parts = [
            f"TYPE: REVOKE",
            f"TOKEN: {token}",
            ""
        ]

        return "\n".join(message_parts)
    
    def build_file_offer(self, to_user_id: str, filename: str, filesize: int, filetype: str, description: str = "") -> str:
        """
        Build a FILE_OFFER message
        Format: TYPE, FROM, TO, FILENAME, FILESIZE, FILETYPE, FILEID, DESCRIPTION, TIMESTAMP, TOKEN
        """
        message_id = self.generate_message_id()
        file_id = self.generate_message_id()  # Use same generation for file ID
        token = self.generate_token("file")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: FILE_OFFER",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"FILENAME: {filename}",
            f"FILESIZE: {filesize}",
            f"FILETYPE: {filetype}",
            f"FILEID: {file_id}",
            f"DESCRIPTION: {description}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)

    def build_file_chunk(self, to_user_id: str, file_id: str, chunk_index: int, total_chunks: int, chunk_size: int, data: str) -> str:
        """
        Build a FILE_CHUNK message
        Format: TYPE, FROM, TO, FILEID, CHUNK_INDEX, TOTAL_CHUNKS, CHUNK_SIZE, TOKEN, DATA
        """
        token = self.generate_token("file")
        
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

    def build_file_received(self, to_user_id: str, file_id: str, status: str = "COMPLETE") -> str:
        """
        Build a FILE_RECEIVED message
        Format: TYPE, FROM, TO, FILEID, STATUS, TIMESTAMP
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
    
    def build_tictactoe_invite(self, to_user_id: str, symbol: str) -> str:
        """
        Build a TICTACTOE_INVITE message
        Format: TYPE, FROM, TO, GAME_ID, MESSAGE_ID, SYMBOL, TIMESTAMP, TOKEN
        """
        game_id = self.generate_game_id()
        message_id = self.generate_message_id()
        token = self.generate_token("game")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: TICTACTOE_INVITE",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"GAME_ID: {game_id}",
            f"MESSAGE_ID: {message_id}",
            f"SYMBOL: {symbol}",
            f"TIMESTAMP: {timestamp}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_tictactoe_move(self, to_user_id: str, game_id: str, symbol: str, position: str, turn: str) -> str:
        """
        Build a TICTACTOE_MOVE message
        Format: TYPE, FROM, TO, GAME_ID, MESSAGE_ID, POSITION, SYMBOL, TURN, TOKEN
        """
        message_id = self.generate_message_id()
        token = self.generate_token("game")
        
        message_parts = [
            f"TYPE: TICTACTOE_MOVE",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"GAME_ID: {game_id}",
            f"MESSAGE_ID: {message_id}",
            f"POSITION: {position}",
            f"SYMBOL: {symbol}",
            f"TURN: {turn}",
            f"TOKEN: {token}",
            ""
        ]
        
        return "\n".join(message_parts)
    
    def build_tictactoe_result(self, to_user_id: str, game_id: str, symbol: str, result: str, winning_line: str) -> str:
        """
        Build a TICTACTOE_RESULT message
        Format: TYPE, FROM, TO, GAME_ID, MESSAGE_ID, RESULT, SYMBOL, WINNING_LINE, TIMESTAMP
        """
        message_id = self.generate_message_id()
        token = self.generate_token("game")
        timestamp = int(time.time())
        
        message_parts = [
            f"TYPE: TICTACTOE_RESULT",
            f"FROM: {self.user_id}",
            f"TO: {to_user_id}",
            f"GAME_ID: {game_id}",
            f"MESSAGE_ID: {message_id}",
            f"RESULT: {result}",
            f"SYMBOL: {symbol}",
            f"WINNING_LINE: {winning_line}",
            f"TIMESTAMP: {timestamp}",
            ""
        ]
        
        return "\n".join(message_parts)
    
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
                if not value and field not in ["STATUS"]:  # STATUS can be empty
                    validation_result["warnings"].append(f"Line {i+1} has empty value for field {field}")
        
        return validation_result
    
    def update_user_info(self, user_id: str = None, display_name: str = None):
        """Update user information for future messages"""
        if user_id:
            self.user_id = user_id
        if display_name:
            self.display_name = display_name