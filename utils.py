import secrets

def generate_message_id(): # message ID generation
    return secrets.token_hex(8)

def extract_message_id(message): # extracts message ID
    for line in message.strip().split('\n'):
        if line.startswith("MESSAGE_ID:"):
            return line.split(':', 1)[1].strip()
    return None