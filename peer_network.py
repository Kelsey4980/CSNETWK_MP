import socket
import threading

class PeerNetwork:
    """Handles all low-level network operations for a peer."""

    DISCOVERY_PORT = 50999
    BROADCAST_IP = '<broadcast>'

    def __init__(self, host_ip, communication_port):
        self.host_ip = host_ip
        self.communication_port = communication_port
        self.running = False

        self.comm_sock = self._create_socket(self.communication_port)
        self.discovery_sock = self._create_socket(self.DISCOVERY_PORT, broadcast=True)

    def _create_socket(self, port, broadcast=False):
        """Creates and binds a UDP socket."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if broadcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(('', port))
            return sock
        except OSError as e:
            print(f"Error binding to port {port}: {e}")
            # In a real app, you might want a more graceful exit
            exit(1)

    def start_listening(self, on_comm_message, on_discovery_message):
        """Starts listening for incoming messages in separate threads."""
        self.running = True
        # Thread for regular communication
        threading.Thread(
            target=self._listen_loop,
            args=(self.comm_sock, on_comm_message),
            daemon=True
        ).start()
        # Thread for discovery messages
        threading.Thread(
            target=self._listen_loop,
            args=(self.discovery_sock, on_discovery_message),
            daemon=True
        ).start()

    def _listen_loop(self, sock, callback):
        """Generic listening loop that passes received data to a callback."""
        while self.running:
            try:
                data, addr = sock.recvfrom(65535)
                # Let the main peer logic decide what to do with the message
                callback(data, addr)
            except Exception as e:
                if self.running:
                    print(f"Error in listen loop: {e}")

    def send_message(self, message, ip, port):
        """Sends a message to a specific IP and port."""
        self.comm_sock.sendto(message.encode(), (ip, port))

    def broadcast_discovery(self, message):
        """Broadcasts a message on the discovery port."""
        self.discovery_sock.sendto(message.encode(), (self.BROADCAST_IP, self.DISCOVERY_PORT))
        self.discovery_sock.sendto(message.encode(), ('127.0.0.1', self.DISCOVERY_PORT))

    def stop(self):
        """Stops the network loops and closes sockets."""
        self.running = False
        self.comm_sock.close()
        self.discovery_sock.close()
        print("Network services stopped.")