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
         - `webserver.py` : server proper
         - `dictionary.py` : stores global variables
         - `utils.py` : helper functions
      - Log and other output are structured.
         - `>> [LOG]` : log messages
         - Verbose and non-verbose output are in this format:
            ```
            ============ >> PRINTING MESSAGE << ============
                           < message here >
            ============= >> END OF MESSAGE << =============               
            ```
      - Peer IPs and Peer Profiles can be viewed.
         - `peer_profile` are those who entered the server with username.
         - `peers_IP` are peers who entered with IP address only.
         - Peer Profiles are also in Peer IPs but Peer IPs can contain IPs that are not in Peer Profiles.
   2. **Protocol Compliance Test Suite**
      - *[ONGOING] CLI or tests for crafting, parsing, and simulating LSNP messages.*
      - Verbose and nonverbose modes are supported.
         - By default, it runs on nonverbose mode.
         - `python webserver.py --verbose` activates the verbose mode.
   3. **Message Sending and Receiving**
   4. **Protocol Parsing and Message Format**
      - Sent messages are parsed and formatted as required.