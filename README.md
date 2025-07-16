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

# TODO: 
- implement different known peers display (so that even ping will be registered to known peers; currently only profile messages save to peer because of tuple defn)
- implement POST to followers only (currently broadcasted)
- should we implement a way for the lsnp to know if it's a new peer so that they would send back their profile/ping? (idt needed based on RFC though)
- improve verbose and non-verbose display (refer to the RFC for non-verbose)
- implement other message features (probably unfollow next)

# GENERAL STEPS FOR IMPLEMENTING NEW FEATURES (may vary):
1. **message_builder.py**: Implement build_<type>() method with required fields if not yet in file
2. **peer.py**: Add send_<type>() method to send the message
3. **message_parser.py**: Add validation rules for the new type in _validate_message()
4. **peer.py**: Add _handle_<type>_message() method IF you need special processing:
   - Storage (add self.<storage> in __init__)
   - State updates (followers, etc.)
   - Can skip this step for simple display-only messages
5. **peer.py**: Update _process_message() to call your handler (if created)
6. **peer.py**: Add command in handle_command() if user-triggered
7. **utils.py**: Update print_help() if new command added
8. **Test!**

# OTHER NOTES FROM HANIELLE:
- debugged the peer class because there were wrong calls to send_message_to_peer, so we will officially depracate lsnp_peer (my old ver lsnp_peer)
- also added a new method for handle_log and handle_profile_message (validate_user_id_and_ip)
- ping also saves to peer now
- cleaned up the codebase, removed unused code in utils and dictionary
- last! i added a last seen for each known peer, this will make it easier to debug in the future when we implement "staling" of peers