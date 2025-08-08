#!/usr/bin/env python3
"""
Test script for HackRX Insurance AI Webhook
"""
import requests
import json
import time

# Test configuration
WEBHOOK_URL = "http://localhost:8000/hackrx/run"
BEARER_TOKEN = "b37bee837667836f35b77319b6c7b1f712a2955869766b98de9400065a1c2c7f"

# Sample test request (using the exact format from the requirements)
test_request = {
    "documents": "https://hackrx.blob.core.windows.net/assets/policy.pdf?sv=2023-01-03&st=2025-07-04T09%3A11%3A24Z&se=2027-07-05T09%3A11%3A00Z&sr=b&sp=r&sig=N4a9OU0w0QXO6AOIBiu4bpl7AXvEZogeT%2FjUHNO7HzQ%3D",
    "questions": [
        "What is the grace period for premium payment under the National Parivar Mediclaim Plus Policy?",
        "What is the waiting period for pre-existing diseases (PED) to be covered?",
        "Does this policy cover maternity expenses, and what are the conditions?",
        "What is the waiting period for cataract surgery?",
        "Are the medical expenses for an organ donor covered under this policy?",
        "What is the No Claim Discount (NCD) offered in this policy?",
        "Is there a benefit for preventive health check-ups?",
        "How does the policy define a 'Hospital'?",
        "What is the extent of coverage for AYUSH treatments?",
        "Are there any sub-limits on room rent and ICU charges for Plan A?"
    ]
}

def test_webhook():
    """Test the webhook endpoint"""
    print("Testing HackRX Insurance AI Webhook...")
    print(f"URL: {WEBHOOK_URL}")
    print(f"Questions: {len(test_request['questions'])}")
    print()
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        print("Sending request...")
        start_time = time.time()
        
        response = requests.post(
            WEBHOOK_URL,
            json=test_request,
            headers=headers,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Time: {duration:.2f} seconds")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"Received {len(result.get('answers', []))} answers")
            print()
            
            # Print answers
            for i, (question, answer) in enumerate(zip(test_request['questions'], result.get('answers', [])), 1):
                print(f"Q{i}: {question}")
                print(f"A{i}: {answer}")
                print("-" * 80)
                
        else:
            print("❌ FAILED!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR!")
        print("Make sure the webhook server is running on localhost:8000")
        print("Run: python hackrx_webhook.py")
        
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT ERROR!")
        print("The request took too long (>5 minutes)")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        print(f"Health Check Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"Response: {response.json()}")
        else:
            print("❌ Health check failed")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    print()

if __name__ == "__main__":
    print("=" * 80)
    print("HackRX Insurance AI Webhook Test")
    print("=" * 80)
    print()
    
    # Test health first
    test_health_endpoint()
    
    # Test main webhook
    test_webhook()
    
    print()
    print("Test completed!")
