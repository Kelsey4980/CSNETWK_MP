import socket

server_ip = "127.0.0.1"  # change to your server IP if on different machine
server_port = 50999

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Example LSNP message (PROFILE type)
message = """TYPE: PROFILE
USER_ID: testuser@192.168.1.20
DISPLAY_NAME: TestUser
STATUS: Just testing!

"""

# Send message
sock.sendto(message.encode(), (server_ip, server_port))
sock.close()
