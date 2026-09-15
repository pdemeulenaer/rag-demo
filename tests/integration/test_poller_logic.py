# tests/integration/test_poller_logic.py
import json
import redis
from pathlib import Path
from unittest.mock import MagicMock
import uuid

from src.api.core.config import config
from src.api.ingestion import poller
from src.api.ingestion.poller import process_completed_batch

# --- PATH LOGIC ---
# This finds the directory where THIS script lives (tests/integration)
# then goes up one level and into the mocks folder.
CURRENT_DIR = Path(__file__).parent
MOCK_FILE_PATH = CURRENT_DIR.parent / "mocks" / "openai_results.jsonl"

# 1. Setup Redis for the test
r = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0)

def simulate_batch_submission():
    batch_id = "batch_test_123"
    
    # Generate valid UUID strings
    valid_uuid_1 = str(uuid.uuid4())
    valid_uuid_2 = str(uuid.uuid4())
    
    # Mapping custom_ids from mock_openai_results.jsonl to valid UUIDs
    mock_metadata = {
        "task_local_test_001": valid_uuid_1,
        "task_local_test_002": valid_uuid_2
    }
    
    r.sadd("pending_openai_batches", batch_id)
    r.set(f"metadata:{batch_id}", json.dumps(mock_metadata))
    
    print(f"✅ Injected test batch {batch_id} into Redis.")
    print(f"🔹 Using Test UUIDs: {valid_uuid_1}, {valid_uuid_2}")

def run_mock_poller_cycle():

    batch_id = "batch_test_123"
    
    # 1. Create the Mock
    mock_client = MagicMock()
    
    # 2. Setup the mock response for files.content().text
    with open(MOCK_FILE_PATH, "r") as f:
        mock_content = f.read()
    
    # This simulates: client.files.content(id).text
    mock_client.files.content.return_value.text = mock_content

    # 3. 🔥 THE KEY STEP: Replace the real client in the poller module
    poller.client = mock_client 

    print("🏃 Running mock processing cycle...")
    
    # 4. Now when this runs, it uses our mock_client!
    process_completed_batch(batch_id, "file-mock-123")

if __name__ == "__main__":
    simulate_batch_submission()
    run_mock_poller_cycle()