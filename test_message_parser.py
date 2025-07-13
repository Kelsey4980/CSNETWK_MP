#!/usr/bin/env python3
"""
Test script for LSNP Message Parser
Tests parsing and validation of various message types
"""

from message_parser import MessageParser, MessageType
import time

def test_message_parser():
    """Test various message types with the parser"""
    parser = MessageParser(verbose_mode=True)
    
    # Test PROFILE message
    profile_msg = """TYPE: PROFILE
USER_ID: alice@192.168.1.12
DISPLAY_NAME: Alice
STATUS: Hello from LSNP!"""
    
    # Test POST message
    post_msg = """TYPE: POST
USER_ID: bob@192.168.1.13
CONTENT: This is my first post!
TTL: 3600
MESSAGE_ID: abc123def456
TOKEN: bob@192.168.1.13|9999999999|broadcast"""
    
    # Test DM message
    dm_msg = """TYPE: DM
FROM: alice@192.168.1.12
TO: bob@192.168.1.13
CONTENT: Hello Bob!
MESSAGE_ID: def456ghi789
TOKEN: alice@192.168.1.12|9999999999|direct"""
    
    # Test FILE_OFFER message
    file_offer_msg = """TYPE: FILE_OFFER
FROM: charlie@192.168.1.14
FILENAME: document.pdf
FILE_SIZE: 2048576
MESSAGE_ID: ghi789jkl012
TOKEN: charlie@192.168.1.14|9999999999|direct"""
    
    # Test GROUP_CREATE message
    group_create_msg = """TYPE: GROUP_CREATE
FROM: alice@192.168.1.12
GROUP_ID: study_group_001
GROUP_NAME: Study Group
MESSAGE_ID: jkl012mno345
TOKEN: alice@192.168.1.12|9999999999|group"""
    
    # Test invalid message (missing required fields)
    invalid_msg = """TYPE: POST
USER_ID: dave@192.168.1.15
MESSAGE_ID: mno345pqr678"""
    
    # Test expired token message
    expired_token_msg = f"""TYPE: POST
USER_ID: eve@192.168.1.16
CONTENT: This message has expired token
MESSAGE_ID: pqr678stu901
TOKEN: eve@192.168.1.16|{int(time.time()) - 3600}|broadcast"""
    
    test_messages = [
        ("PROFILE", profile_msg),
        ("POST", post_msg),
        ("DM", dm_msg),
        ("FILE_OFFER", file_offer_msg),
        ("GROUP_CREATE", group_create_msg),
        ("INVALID POST", invalid_msg),
        ("EXPIRED TOKEN", expired_token_msg)
    ]
    
    # Mock peer profiles for testing
    peer_profiles = {
        "alice@192.168.1.12": ("Alice", "192.168.1.12"),
        "bob@192.168.1.13": ("Bob", "192.168.1.13"),
        "charlie@192.168.1.14": ("Charlie", "192.168.1.14"),
        "dave@192.168.1.15": ("Dave", "192.168.1.15"),
        "eve@192.168.1.16": ("Eve", "192.168.1.16")
    }
    
    print("=== TESTING MESSAGE PARSER ===\n")
    
    for test_name, message in test_messages:
        print(f"Testing: {test_name}")
        print("-" * 40)
        
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
        print(formatted)
        
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
    
    test_message = """TYPE: POST
USER_ID: test@example.com
CONTENT: This is a test message
TTL: 3600
MESSAGE_ID: test123
TOKEN: test@example.com|9999999999|broadcast"""
    
    fields = parser._extract_fields(test_message)
    
    print("\n=== FIELD EXTRACTION TEST ===")
    print("Extracted fields:")
    for key, value in fields.items():
        print(f"  {key}: {value}")
    
    # Test required fields validation
    required = parser._get_required_fields(MessageType.POST)
    print(f"\nRequired fields for POST: {required}")
    
    missing = [field for field in required if field not in fields]
    print(f"Missing fields: {missing}")

if __name__ == "__main__":
    test_message_parser()
    test_field_extraction()
    print("\n=== ALL TESTS COMPLETED ===")