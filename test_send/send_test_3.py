import socket
import time
import secrets

server_ip = "127.0.0.1"  # change if needed
server_port = 50999

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Example LSNP message (POST type)
user_id = f"testuser@{server_ip}"
content = "This is a new post from me hehe."
ttl = 3600
timestamp = int(time.time())
message_id = secrets.token_hex(8)
token = f"{user_id}|{timestamp + ttl}|broadcast"

message = f"""TYPE: POST
USER_ID: {user_id}
CONTENT: {content}
TTL: {ttl}
MESSAGE_ID: {message_id}
TOKEN: {token}

"""

# Send message
sock.sendto(message.encode(), (server_ip, server_port))
sock.close()
