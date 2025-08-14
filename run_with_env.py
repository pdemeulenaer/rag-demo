# run_with_env.py
import os
from dotenv import load_dotenv
import uvicorn

# Load environment variables from the .env file.
# This must be done before any other code runs.
load_dotenv()

# This block ensures the code inside only runs when the script is executed directly.
if __name__ == '__main__':
    # Now run uvicorn as a program.
    # This ensures the new environment variables are available to the uvicorn process.
    uvicorn.run("src.api_test.main:app", host="0.0.0.0", port=8000, reload=True)