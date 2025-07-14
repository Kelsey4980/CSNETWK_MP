"""
Test script for LSNP Message Parser
Tests parsing and validation of various message types
"""

from message_parser import MessageParser, MessageType
import time

def create_lsnp_message(**fields):
    """Helper function to create properly formatted LSNP messages"""
    lines = []
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)

def test_message_parser():
    """Test various message types with the parser"""
    parser = MessageParser(verbose_mode=True)
    
    # Test PROFILE message - using helper function for clarity
    profile_msg = create_lsnp_message(
        TYPE="PROFILE",
        USER_ID="alice@192.168.1.12",
        DISPLAY_NAME="Alice",
        STATUS="Hello from LSNP!"
    )
    
    # Test POST message
    post_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="bob@192.168.1.13",
        CONTENT="This is my first post!",
        TTL="3600",
        MESSAGE_ID="abc123def456",
        TOKEN="bob@192.168.1.13|9999999999|broadcast"
    )
    
    # Test DM message
    dm_msg = create_lsnp_message(
        TYPE="DM",
        FROM="alice@192.168.1.12",
        TO="bob@192.168.1.13",
        CONTENT="Hello Bob!",
        TIMESTAMP=str(int(time.time())),
        MESSAGE_ID="def456ghi789",
        TOKEN="alice@192.168.1.12|9999999999|direct"
    )
    
    # Test FILE_OFFER message
    file_offer_msg = create_lsnp_message(
        TYPE="FILE_OFFER",
        FROM="charlie@192.168.1.14",
        TO="bob@192.168.1.13",
        FILENAME="document.pdf",
        FILESIZE="2048576",
        FILETYPE="application/pdf",
        FILEID="file_001",
        TIMESTAMP=str(int(time.time())),
        TOKEN="charlie@192.168.1.14|9999999999|file"
    )
    
    # Test GROUP_CREATE message
    group_create_msg = create_lsnp_message(
        TYPE="GROUP_CREATE",
        FROM="alice@192.168.1.12",
        GROUP_ID="study_group_001",
        GROUP_NAME="Study Group",
        MEMBERS="alice@192.168.1.12,bob@192.168.1.13",
        TIMESTAMP=str(int(time.time())),
        MESSAGE_ID="jkl012mno345",
        TOKEN="alice@192.168.1.12|9999999999|group"
    )
    
    # Test FOLLOW message
    follow_msg = create_lsnp_message(
        TYPE="FOLLOW",
        FROM="alice@192.168.1.12",
        TO="bob@192.168.1.13",
        TIMESTAMP=str(int(time.time())),
        MESSAGE_ID="follow_001",
        TOKEN="alice@192.168.1.12|9999999999|follow"
    )
    
    # Test LIKE message
    like_msg = create_lsnp_message(
        TYPE="LIKE",
        FROM="alice@192.168.1.12",
        TO="bob@192.168.1.13",
        POST_TIMESTAMP=str(int(time.time()) - 3600),
        ACTION="like",
        TIMESTAMP=str(int(time.time())),
        TOKEN="alice@192.168.1.12|9999999999|chat"
    )
    
    # Test TICTACTOE_INVITE message
    tictactoe_invite_msg = create_lsnp_message(
        TYPE="TICTACTOE_INVITE",
        FROM="alice@192.168.1.12",
        TO="bob@192.168.1.13",
        GAMEID="game_001",
        MESSAGE_ID="ttt_invite_001",
        SYMBOL="X",
        TIMESTAMP=str(int(time.time())),
        TOKEN="alice@192.168.1.12|9999999999|game"
    )
    
    # Test PING message
    ping_msg = create_lsnp_message(
        TYPE="PING",
        USER_ID="alice@192.168.1.12"
    )
    
    # Test ACK message
    ack_msg = create_lsnp_message(
        TYPE="ACK",
        MESSAGE_ID="abc123def456",
        STATUS="RECEIVED"
    )
    
    # Test invalid message (missing required fields)
    invalid_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="dave@192.168.1.15",
        MESSAGE_ID="mno345pqr678"
        # Missing CONTENT, TTL, and TOKEN - should be invalid
    )
    
    # Test expired token message
    expired_token_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="eve@192.168.1.16",
        CONTENT="This message has expired token",
        TTL="3600",
        MESSAGE_ID="pqr678stu901",
        TOKEN=f"eve@192.168.1.16|{int(time.time()) - 3600}|broadcast"
    )
    
    # Test invalid token format
    invalid_token_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="frank@192.168.1.17",
        CONTENT="This message has invalid token",
        TTL="3600",
        MESSAGE_ID="stu901vwx234",
        TOKEN="invalid_token_format"
    )
    
    test_messages = [
        ("PROFILE", profile_msg),
        ("POST", post_msg),
        ("DM", dm_msg),
        ("FILE_OFFER", file_offer_msg),
        ("GROUP_CREATE", group_create_msg),
        ("FOLLOW", follow_msg),
        ("LIKE", like_msg),
        ("TICTACTOE_INVITE", tictactoe_invite_msg),
        ("PING", ping_msg),
        ("ACK", ack_msg),
        ("INVALID POST", invalid_msg),
        ("EXPIRED TOKEN", expired_token_msg),
        ("INVALID TOKEN", invalid_token_msg)
    ]
    
    # Mock peer profiles for testing
    peer_profiles = {
        "alice@192.168.1.12": ("Alice", "192.168.1.12"),
        "bob@192.168.1.13": ("Bob", "192.168.1.13"),
        "charlie@192.168.1.14": ("Charlie", "192.168.1.14"),
        "dave@192.168.1.15": ("Dave", "192.168.1.15"),
        "eve@192.168.1.16": ("Eve", "192.168.1.16"),
        "frank@192.168.1.17": ("Frank", "192.168.1.17")
    }
    
    print("=== TESTING MESSAGE PARSER ===\n")
    
    for test_name, message in test_messages:
        print(f"Testing: {test_name}")
        print("-" * 40)
        
        # Show the actual message being tested
        print("Raw message:")
        print(repr(message))  # Shows the exact format
        print()
        
        # Parse the message
        parsed = parser.parse_message(message, "192.168.1.100")
        
        # Show parsing results
        print(f"Message Type: {parsed.message_type}")
        print(f"Valid: {parsed.is_valid}")
        
        if parsed.validation_errors:
            print(f"Validation Errors: {parsed.validation_errors}")
        
        # Test token validation
        token_valid = parsed.validate_token()
        print(f"Token Valid: {token_valid}")
        
        # Show formatted output (non-verbose)
        parser.verbose_mode = False
        formatted = parser.format_message_output(parsed, peer_profiles)
        print("Formatted Output:")
        if formatted:
            print(formatted)
        else:
            print("(No output - message type doesn't display)")
        
        # Show debug output
        if not parsed.is_valid or not token_valid:
            print("Debug Info:")
            print(parsed.to_debug_string())
        
        print("=" * 50)
        print()
    
    # Test message storage and retrieval
    print("\n=== TESTING MESSAGE STORAGE ===")
    
    # Get stored messages
    stored = parser.get_stored_messages()
    print(f"Total stored messages: {len(stored)}")
    
    # Get posts by user
    posts = parser.get_posts_by_user("bob@192.168.1.13")
    print(f"Posts by Bob: {len(posts)}")
    
    # Get DMs by user
    dms = parser.get_dms_by_user("alice@192.168.1.12")
    print(f"DMs from Alice: {len(dms)}")
    
    # Get messages by type
    follow_messages = parser.get_messages_by_type(MessageType.FOLLOW)
    print(f"Follow messages: {len(follow_messages)}")
    
    # Print statistics
    parser.print_all_messages_summary()
    
    print("\n=== TESTING VERBOSE MODE ===")
    parser.verbose_mode = True
    verbose_output = parser.format_message_output(parsed, peer_profiles)
    print("Verbose Output:")
    print(verbose_output)

def test_field_extraction():
    """Test field extraction functionality"""
    parser = MessageParser()
    
    # Test with properly formatted message
    test_message = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="This is a test message",
        TTL="3600",
        MESSAGE_ID="test123",
        TOKEN="test@example.com|9999999999|broadcast"
    )
    
    fields = parser._extract_fields(test_message)
    
    print("\n=== FIELD EXTRACTION TEST ===")
    print("Test message:")
    print(repr(test_message))
    print()
    print("Extracted fields:")
    for key, value in fields.items():
        print(f"  {key}: {value}")
    
    # Test required fields validation
    required = parser._get_required_fields(MessageType.POST)
    print(f"\nRequired fields for POST: {required}")
    
    missing = [field for field in required if field not in fields]
    print(f"Missing fields: {missing}")

def test_token_validation():
    """Test token validation functionality"""
    parser = MessageParser()
    
    print("\n=== TOKEN VALIDATION TEST ===")
    
    # Test valid token
    valid_token_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="Valid token test",
        TTL="3600",
        MESSAGE_ID="token_test_001",
        TOKEN="test@example.com|9999999999|broadcast"
    )
    
    # Test expired token
    expired_token_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="Expired token test",
        TTL="3600",
        MESSAGE_ID="token_test_002",
        TOKEN=f"test@example.com|{int(time.time()) - 3600}|broadcast"
    )
    
    # Test invalid token format
    invalid_format_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="Invalid format test",
        TTL="3600",
        MESSAGE_ID="token_test_003",
        TOKEN="invalid_format"
    )
    
    # Test invalid scope
    invalid_scope_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="Invalid scope test",
        TTL="3600",
        MESSAGE_ID="token_test_004",
        TOKEN="test@example.com|9999999999|invalid_scope"
    )
    
    token_tests = [
        ("Valid Token", valid_token_msg),
        ("Expired Token", expired_token_msg),
        ("Invalid Format", invalid_format_msg),
        ("Invalid Scope", invalid_scope_msg)
    ]
    
    for test_name, message in token_tests:
        print(f"Testing: {test_name}")
        print("-" * 30)
        
        parsed = parser.parse_message(message, "127.0.0.1")
        token_valid = parsed.validate_token()
        
        print(f"Token: {parsed.fields.get('TOKEN', 'None')}")
        print(f"Valid: {token_valid}")
        
        if parsed.validation_errors:
            print(f"Errors: {parsed.validation_errors}")
        
        print()

def demonstrate_format_importance():
    """Demonstrate why format matters for parsing"""
    parser = MessageParser()
    
    print("\n=== FORMAT IMPORTANCE DEMO ===")
    
    # Correct format
    correct_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="Hello world"
    )
    
    # Incorrect format (indented)
    incorrect_msg = """TYPE: POST
    USER_ID: test@example.com
    CONTENT: Hello world"""
    
    # Malformed lines
    malformed_msg = """TYPE: POST
USER_ID: test@example.com
CONTENT Hello world no colon
EMPTY_LINE:

TRAILING_SPACES:   value   """
    
    print("CORRECT format:")
    print(repr(correct_msg))
    parsed_correct = parser.parse_message(correct_msg, "127.0.0.1")
    print(f"Parsed fields: {parsed_correct.fields}")
    print()
    
    print("INCORRECT format (indented):")
    print(repr(incorrect_msg))
    parsed_incorrect = parser.parse_message(incorrect_msg, "127.0.0.1")
    print(f"Parsed fields: {parsed_incorrect.fields}")
    print("Notice how indented fields are not parsed correctly!")
    print()
    
    print("MALFORMED format:")
    print(repr(malformed_msg))
    parser.verbose_mode = True  # Enable verbose to see warnings
    parsed_malformed = parser.parse_message(malformed_msg, "127.0.0.1")
    print(f"Parsed fields: {parsed_malformed.fields}")
    print("Notice how malformed lines are handled!")

def test_message_type_validation():
    """Test message type specific validation"""
    parser = MessageParser()
    
    print("\n=== MESSAGE TYPE VALIDATION TEST ===")
    
    # Test POST with content too long
    long_content_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="x" * 501,  # Exceeds 500 character limit
        TTL="3600",
        MESSAGE_ID="long_content_test",
        TOKEN="test@example.com|9999999999|broadcast"
    )
    
    # Test POST with non-numeric TTL
    invalid_ttl_msg = create_lsnp_message(
        TYPE="POST",
        USER_ID="test@example.com",
        CONTENT="Invalid TTL test",
        TTL="not_a_number",
        MESSAGE_ID="invalid_ttl_test",
        TOKEN="test@example.com|9999999999|broadcast"
    )
    
    # Test DM with non-numeric timestamp
    invalid_timestamp_msg = create_lsnp_message(
        TYPE="DM",
        FROM="test@example.com",
        TO="other@example.com",
        CONTENT="Invalid timestamp test",
        TIMESTAMP="not_a_number",
        MESSAGE_ID="invalid_timestamp_test",
        TOKEN="test@example.com|9999999999|direct"
    )
    
    # Test FILE_OFFER with non-numeric filesize
    invalid_filesize_msg = create_lsnp_message(
        TYPE="FILE_OFFER",
        FROM="test@example.com",
        TO="other@example.com",
        FILENAME="test.txt",
        FILESIZE="not_a_number",
        FILETYPE="text/plain",
        FILEID="file_001",
        TIMESTAMP=str(int(time.time())),
        TOKEN="test@example.com|9999999999|file"
    )
    
    validation_tests = [
        ("Long Content POST", long_content_msg),
        ("Invalid TTL POST", invalid_ttl_msg),
        ("Invalid Timestamp DM", invalid_timestamp_msg),
        ("Invalid Filesize FILE_OFFER", invalid_filesize_msg)
    ]
    
    for test_name, message in validation_tests:
        print(f"Testing: {test_name}")
        print("-" * 30)
        
        parsed = parser.parse_message(message, "127.0.0.1")
        
        print(f"Valid: {parsed.is_valid}")
        if parsed.validation_errors:
            print(f"Validation Errors: {parsed.validation_errors}")
        
        print()

if __name__ == "__main__":
    test_message_parser()
    test_field_extraction()
    test_token_validation()
    demonstrate_format_importance()
    test_message_type_validation()
    print("\n=== ALL TESTS COMPLETED ===")