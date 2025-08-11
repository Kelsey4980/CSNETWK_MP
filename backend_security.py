import time
from dictionary import MESSAGE_TYPE_TO_SCOPE, MessageType, MessageScope 
from utils import display_manager

class BackendSecurity:
     """
     Handles token validation and scoping
     """

     def __init__(self, revoked_tokens_self, revoked_tokens_others):
          self.revoked_tokens_self = revoked_tokens_self
          self.revoked_tokens_others = revoked_tokens_others

     def is_token_valid(self, token, type):
          current_time = time.time()

          # print("1 ", token, type)

          try:
               # check if the token format is valid
               token_parts = token.split("|")
               if len(token_parts) != 3:
                    display_manager.log_debug(f"Invalid token format: {token}")
                    return False
               
               user_id, timestamp_str, scope = token_parts
               timestamp = float(timestamp_str)

               # print("2 ", user_id, timestamp_str, scope)

               # [1] check if not yet expired
               if current_time > timestamp:
                    display_manager.log_debug(f"Token expired: {token}")
                    return False
               
               # [2] check if right scope
               scope_check = self.is_scope_valid(scope, type)
               if (not scope_check):
                    display_manager.log_debug(f"Token scope invalid: {token}")
                    return False
               
               # [3] check if revoked
               if token in self.revoked_tokens_self or token in self.revoked_tokens_others:
                    display_manager.log_debug(f"A token has been revoked: {token}")
                    display_manager.log_debug(f"Message from {user_id} is removed/rejected.")
                    return False
               
               return True
            
          except Exception as e:
               print(f"Token validation error: {e}")
               return False
          
     def is_scope_valid(self, scope, type):
          expected_scope = MESSAGE_TYPE_TO_SCOPE.get(type)
          
          if expected_scope is None:
               print(f"Warning: No scope mapping found for message type: {type}")
               return False
          
          return scope == expected_scope.value
