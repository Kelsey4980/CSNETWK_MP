from socket import *

sock = socket(AF_INET, SOCK_DGRAM)
sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

PORT = 50999
message = """TYPE: PROFILE
USER_ID: alice@192.168.1.12
DISPLAY_NAME: Alice
STATUS: Hello from LSNP!

"""

sock.sendto(message.encode(), ('<broadcast>', PORT))
sock.close()
