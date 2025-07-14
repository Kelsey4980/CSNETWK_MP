from enum import Enum

# store all IP addresses that entered the server
peers_IP = {}

# map USER_ID to (DISPLAY_NAME, IP, STATUS)
peer_profiles = {}

# verbose mode
verbose_mode = False

# port - changed from 50999 to avoid conflict with discovery port
port = 51000

# ttl
ttl = 3600

class MessageType(Enum):
    """Enumeration of all LSNP message types"""
    PROFILE = "PROFILE"
    POST = "POST"
    DM = "DM"
    FOLLOW = "FOLLOW"
    UNFOLLOW = "UNFOLLOW"
    LIKE = "LIKE"
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