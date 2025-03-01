"""
Quick script to test Azure AI Foundry API connection.
"""
import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from .env
api_key = os.getenv("AZURE_AI_FOUNDRY_API_KEY")
endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
model = os.getenv("AZURE_AI_FOUNDRY_MODEL_NAME")

# Print for debugging
print(f"Endpoint: {endpoint}")
print(f"Model name: {model}")
print(f"API key set: {'Yes' if api_key else 'No'}")

# Set request headers
headers = {
    "Content-Type": "application/json",
    "api-key": api_key
}

# Create payload
data = {
    "model": model,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, what is an executive order?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

print("\nSending API request...")

try:
    # Make the API call
    response = requests.post(
        url=endpoint,
        headers=headers,
        json=data,
        timeout=30
    )
    
    # Print status
    print(f"Status code: {response.status_code}")
    
    # If successful, print the response
    if response.status_code == 200:
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "No content")
        print(f"\nResponse:\n{content}")
    else:
        print(f"\nError response:\n{response.text}")
        
except Exception as e:
    print(f"\nException occurred: {str(e)}")