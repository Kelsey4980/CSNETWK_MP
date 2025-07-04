# this is copied code from lab 5. i just put it here first for base

# import socket module
from socket import *
import sys  # In order to terminate the program

serverSocket = socket(AF_INET, SOCK_STREAM)
# Prepare a sever socket
# Fill in start
serverSocket.bind(('', 6969))
serverSocket.listen()
# Fill in end


while True:
    # Establish the connection
    print('CSNETWK Web Server is ready to serve...')
    connSocket, addr = serverSocket.accept()  # Fill in start   #Fill in end
    try:
        message = connSocket.recv(1024).decode()  # Fill in start #Fill in end
        filename = message.split()[1]
        f = open(filename[1:])
        outputdata = f.read()  # Fill in start #Fill in end
        # Send one HTTP header line into socket
        # Fill in start
        connSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())
        # Fill in end
        # Send the content of the requested file to the client
        for i in range(0, len(outputdata)):
            connSocket.send(outputdata[i].encode())

        connSocket.send("\r\n".encode())
        connSocket.close()

    except IOError:
        # Send response message for file not found
        # Fill in start
        connSocket.send("HTTP/1.1 404 Not Found\r\n\r\n".encode())
        connSocket.send("<html><body><h1>404 Not Found</h1></body></html>\r\n".encode())
        # Fill in end

        # Close client socket
        # Fill in start
        connSocket.close()
        # Fill in end
serverSocket.close()
sys.exit()  # Terminate the program after sending the corresponding data