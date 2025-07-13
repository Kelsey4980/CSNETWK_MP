# CSNETWK_MP
## How to Run
1. Install required package by running:  
   `pip install prompt_toolkit`  
   (If `pip` is not recognized on Windows, use: `py -m pip install prompt_toolkit`)

2. Run `python webserver.py` on terminal.  
3. On a different terminal, go to `test_send` folder. Run `python <test_file.py>`.  
4. Check the server terminal if the message is received.

## Server Logic
### Milestone #1
   1. **Clean Architecture & Logging**
      - Multiple files created each serving different purpose.
         - `webserver.py` : server proper with enhanced command interface
         - `dictionary.py` : stores global variables
         - `utils.py` : helper functions and legacy compatibility
         - `message_parser.py` : comprehensive LSNP message parser and validator
      - Log and other output are structured.
         - `>> [LOG]` : log messages
         - Verbose and non-verbose output are in this format:
            ```
            ============ >> PROCESSING MESSAGE << ============
                           < message here >
            ============= >> END OF MESSAGE << =============               
            ```
      - Peer IPs and Peer Profiles can be viewed.
         - `peer_profile` are those who entered the server with username.
         - `peers_IP` are peers who entered with IP address only.
         - Peer Profiles are also in Peer IPs but Peer IPs can contain IPs that are not in Peer Profiles.
   2. **Protocol Compliance Test Suite**
      - **[ONGOING]** CLI and tests for crafting, parsing, and simulating LSNP messages.
      - Comprehensive message parser supporting LSNP message types:
         - `PROFILE`, `POST`, `DM`, `FOLLOW`, `UNFOLLOW`, `LIKE`
         - `FILE_OFFER`, `FILE_CHUNK`, `FILE_RECEIVED`
         - `GROUP_CREATE`, `GROUP_UPDATE`, `GROUP_MESSAGE`
         - `GAME_START`, `GAME_MOVE`, `GAME_END`
         - `ACK`, `PING`
      - Message validation and token authentication system.
      - Verbose and nonverbose modes are supported.
         - By default, it runs on nonverbose mode.
         - `python webserver.py --verbose` activates the verbose mode.
         - Runtime verbose mode toggle via `verbose` command.
   3. **Message Sending and Receiving**
      - Message sending and receiving capabilities.
      - Automatic ACK response system for messages with MESSAGE_ID.
      - Message storage and retrieval system for valid messages.
   4. **Protocol Parsing and Message Format**
      - Sent messages are parsed and formatted as required.
      - Field extraction and validation for all message types.
      - Token validation with expiration and scope checking.
      - Debug output for invalid messages and parsing errors.

### Interactive Command Interface
The server now includes an interactive command-line interface with the following commands:
- `peers` - List known peers with their display names and IP addresses
- `ips` - List all known IP addresses
- `posts` - List all stored posts
- `posts <user>` - List posts by a specific user
- `dms <user>` - List DMs from a specific user
- `stats` - Show message statistics and counts by type
- `verbose` - Toggle verbose mode on/off
- `help` - Show available commands
- `exit/quit` - Exit the server

### Message Parser Features
- **Comprehensive Validation**: Validates message structure, required fields, and token authenticity
- **Token System**: Supports token-based authentication with expiration and scope validation
- **Message Storage**: Stores valid messages for later retrieval and analysis
- **Debug Output**: Detailed debugging information for troubleshooting invalid messages
- **Flexible Output**: Both verbose (raw message) and user-friendly formatted output

### File Structure
```
CSNETWK_MP/
├── webserver.py           # Main server with command interface
├── utils.py               # Utility functions and legacy compatibility
├── message_parser.py      # Comprehensive LSNP message parser
├── dictionary.py          # Global variables and configuration
├── test_message_parser.py # Test message parser with different message types
├── test_send/           # Test message scripts
│   ├── send_test_1.py   # PROFILE message test
│   ├── send_test_2.py   # PROFILE message test (alternative)
│   └── send_test_3.py   # POST message test with token
└── README.md            # This file
```

## Testing
The project includes multiple test files in the `test_send/` directory:
- `send_test_1.py` - Tests PROFILE message broadcasting
- `send_test_2.py` - Tests PROFILE message with specific server IP
- `send_test_3.py` - Tests POST message with token authentication

Additionally, there is a `test_message_parser.py` file in the root folder for testing the LSNP message parser functionality.
