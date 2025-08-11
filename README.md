# CSNETWK_MP

## How to Run
1. Install required package by running: `pip install prompt_toolkit`. If `pip` is not recognized on Windows, use: `py -m pip install prompt_toolkit`.
2. Run `python lsnp_peer.py --username <username> --name <name>` on terminal. Make sure you are in root folder.
   - `username` is attached in user ID.
   - `name` is the display name.
   - Additionally, you can add `--verbose` at the end to toggle verbose mode.

## Server Logic

### Milestone #1
   1. **Clean Architecture & Logging**
      - Multiple files created each serving different purpose:
         - `lsnp_peer.py` : server proper with enhanced command interface
         - `dictionary.py` : stores the ENUM which determines the type of messages accepted in this server
         - `utils.py` : helper functions, mostly printing and logging
         - `message_parser.py` : comprehensive LSNP message parser and validator
         - `message_builder.py` : comprehensive LSNP message builder, constructs the messages in a way that is accepted by the server
      - Log and other output are structured:
         - `>> [LOG]` : log messages
         - `>> [WARNING]` : warning messages
         - `>> [DEBUG]` : debug messages
         - Verbose and non-verbose output are in this format:
            ```
            ============ >> START OF MESSAGE << ============
                           < message here >
            ============= >> END OF MESSAGE << =============               
            ```
      - Known **IPs** and known **peers** can be viewed
         - IPs are just addresses while peers are those with user IDs.
   2. **Protocol Compliance Test Suite**
      - CLI and tests for crafting, parsing, and simulating LSNP messages.
         - Formatted are shown after sending in verbose mode.
         - The server already allows creating and parsing messages.
      - Comprehensive message parser supporting LSNP message types:
         - Posts, DM, Ping, Follow, Unfollow, Like, Ack
      - Message validation and token authentication system.
      - Verbose and nonverbose modes are supported:
         - By default, it runs on nonverbose mode.
         - `python lsnp_peer.py --username <username> --name <name> --verbose` activates the verbose mode.
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

### Milestone #2
   1. **User Discovery and Presence**
      - Functionality can be found in `def _discovery_loop(self)`
      - Profile is pinged/broadcasted every 5 minutes
   2. **Messaging Functionality**
      * POST: Peers can now share posts among followers only
      * DM: Peers can send DMs to the specified peer
      * FOLLOW: Peers can follow other peers
      * UNFOLLOW: Peers can unfollow other peers 

### Milestone #3
   1. **Profile Picture and Likes**
      - Avatars are stored in base64 format and are stored as data + type fields in Profile.
      - Avatars appear in DMs and Posts
      - Likes are stored with Posts, are referred to by using a timestamp, and can be removed through Unlike.
   2. **File Transfer**
      - fill
   3. **Token Handling and Scope Validation**
      - fill
   4. **Group Management**
      - Users can create and be a member of multiple groups.
      - Users can update their group to add and remove members.
      - Users can message all the members in a specified group.
   5. **Game Support (Tic Tac Toe)**
      - Users can play tic-tac-toe against other users.
      - Multiple matches can be ongoing at the same time, made possible by utilizing unique game IDs.
      - Users can view the result of a finished game.
