# CSNETWK_MP

## How to Run
1. Install required package by running:  
   ```bash
   pip install prompt_toolkit
   ```
   (If pip is not recognized on Windows, use: `py -m pip install prompt_toolkit`)
2. Run `python webserver.py` on terminal.  
3. On a different terminal, go to test_send folder. Run `python <test_file.py>`.  
4. Check the server terminal if the message is received.

## Server Logic

### Milestone #1
   1. **Clean Architecture & Logging**
      - Multiple files created each serving different purpose:
         - `webserver.py` : server proper with enhanced command interface
         - `dictionary.py` : stores global variables
         - `utils.py` : helper functions and legacy compatibility
         - `message_parser.py` : comprehensive LSNP message parser and validator
      - Log and other output are structured:
         - `>> [LOG]` : log messages
         - Verbose and non-verbose output are in this format:
            ```
            ============ >> PROCESSING MESSAGE << ============
                           < message here >
            ============= >> END OF MESSAGE << =============               
            ```
      - Peer IPs and Peer Profiles can be viewed:
         - `peer_profiles` are those who entered the server with username.
         - `peers_IP` are peers who entered with IP address only.
         - Peer Profiles are also in Peer IPs but Peer IPs can contain IPs that are not in Peer Profiles.
   2. **Protocol Compliance Test Suite**
      - **[ONGOING]** CLI and tests for crafting, parsing, and simulating LSNP messages.
      - Comprehensive message parser supporting LSNP message types:
         - TESTED w/ SEND_TEST and TEST_MESSAGE_PARSER
            - PROFILE, POST
         - LOOSELY TESTED w/ TEST_MESSAGE_PARSER
            - DM, FOLLOW, UNFOLLOW, LIKE
            - FILE_OFFER, FILE_CHUNK, FILE_RECEIVED
            - GROUP_CREATE, GROUP_UPDATE, GROUP_MESSAGE
            - GAME_START, GAME_MOVE, GAME_END
            - ACK, PING
      - Message validation and token authentication system. (Loosely tested)
      - Verbose and nonverbose modes are supported:
         - By default, it runs on nonverbose mode.
         - `python webserver.py --verbose` activates the verbose mode.
         - Runtime verbose mode toggle via `verbose` command.
   3. **Message Sending and Receiving**
      - Message sending and receiving capabilities.
      - Automatic ACK response system for messages with MESSAGE_ID.
      - Message storage and retrieval system for valid messages. (Not persistent after program exit)
   4. **Protocol Parsing and Message Format**
      - Sent messages are parsed and formatted as required.
      - Field extraction and validation for different message types.
      - Token validation with expiration and scope checking.
      - Debug output for invalid messages and parsing errors.