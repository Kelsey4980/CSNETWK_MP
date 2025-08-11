"""
    SUBMITTED BY:
        CHING, Justin
        CHUA, Hanielle
        KELSEY, Gabrielle
        TOLENTINO, Hephzi

    CSNETWK S15
"""

from enum import Enum

class MessageType(Enum):
    """Enumeration of all LSNP message types"""
    PROFILE = "PROFILE"
    POST = "POST"
    DM = "DM"
    FOLLOW = "FOLLOW"
    UNFOLLOW = "UNFOLLOW"
    LIKE = "LIKE"
    UNLIKE = "UNLIKE"
    FILE_OFFER = "FILE_OFFER"
    FILE_CHUNK = "FILE_CHUNK"
    FILE_RECEIVED = "FILE_RECEIVED"
    GROUP_CREATE = "GROUP_CREATE"
    GROUP_UPDATE = "GROUP_UPDATE"
    GROUP_MESSAGE = "GROUP_MESSAGE"
    TICTACTOE_INVITE = "TICTACTOE_INVITE"
    TICTACTOE_MOVE = "TICTACTOE_MOVE"
    TICTACTOE_RESULT = "TICTACTOE_RESULT"
    ACK = "ACK"
    PING = "PING"
    REVOKE = "REVOKE"
    UNKNOWN = "UNKNOWN"

class MessageScope(Enum):
    """Enumeration of LSNP token scopes"""
    CHAT = "chat"            # For DM
    FILE = "file"            # For FILE_OFFER, FILE_CHUNK
    BROADCAST = "broadcast"  # For POST, LIKE, UNLIKE
    FOLLOW = "follow"        # For FOLLOW, UNFOLLOW
    GAME = "game"            # For TICTACTOE_*
    GROUP = "group"          # For GROUP_*


MESSAGE_TYPE_TO_SCOPE = {
    MessageType.DM: MessageScope.CHAT,
    # MessageType.REVOKE: MessageScope.CHAT,

    MessageType.FILE_OFFER: MessageScope.FILE,
    MessageType.FILE_CHUNK: MessageScope.FILE,
    MessageType.FILE_RECEIVED: MessageScope.FILE,

    MessageType.POST: MessageScope.BROADCAST,
    MessageType.LIKE: MessageScope.BROADCAST,
    MessageType.UNLIKE: MessageScope.BROADCAST,

    MessageType.FOLLOW: MessageScope.FOLLOW,
    MessageType.UNFOLLOW: MessageScope.FOLLOW,

    MessageType.TICTACTOE_INVITE: MessageScope.GAME,
    MessageType.TICTACTOE_MOVE: MessageScope.GAME,
    MessageType.TICTACTOE_RESULT: MessageScope.GAME,

    MessageType.GROUP_CREATE: MessageScope.GROUP,
    MessageType.GROUP_UPDATE: MessageScope.GROUP,
    MessageType.GROUP_MESSAGE: MessageScope.GROUP,
}