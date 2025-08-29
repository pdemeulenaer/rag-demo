# inspect_redis.py
import sys
import os
import redis
import pickle

# Add the project's root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


# Now you can import the class directly from your project
from src.api.rag.retrieval import ConversationMemory

# Check if a session ID was provided as a command-line argument
if len(sys.argv) < 2:
    print("Error: Please provide a session ID as a command-line argument.")
    print("Example: python inspect_redis.py <session_id>")
    sys.exit(1)

# The session ID is the first argument after the script name
session_id_to_inspect = sys.argv[1]    

# Assume Redis is running via Docker Compose
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_DB = 0

# # Replace this with the actual session ID you want to inspect
# SESSION_ID_TO_INSPECT = "4ce7bbc6-ab1f-46ec-b900-c8b8d89a84e7"

# Connect to the Redis instance
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    pickled_data = redis_client.get(session_id_to_inspect)
    
    if pickled_data:
        conversation_memory = pickle.loads(pickled_data)
        
        print("\n--- Conversation Summary ---")
        print(conversation_memory.summary)
        
        print("\n--- Recent Messages ---")
        for message in conversation_memory.recent_messages:
            print(f"{message['role'].capitalize()}: {message['content']}")
        
    else:
        print(f"No data found for session ID: {session_id_to_inspect}")
        
except redis.exceptions.ConnectionError as e:
    print(f"Error connecting to Redis: {e}")
except pickle.UnpicklingError as e:
    print(f"Error unpickling data: {e}")