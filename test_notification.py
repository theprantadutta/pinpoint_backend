"""
Test script to send a notification via the backend API
Run this to test if notifications are working
"""
import requests
import json

# Backend URL
BASE_URL = "http://localhost:8000"

def test_notification():
    """Test the notification endpoint"""
    print("🧪 Testing notification endpoint...")
    print(f"URL: {BASE_URL}/api/v1/notifications/test\n")

    try:
        response = requests.post(f"{BASE_URL}/api/v1/notifications/test")

        print(f"Status Code: {response.status_code}")
        print(f"\nResponse:")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("\n✅ SUCCESS! Firebase is initialized and working!")
            else:
                print("\n❌ FAILED!")
                print(f"Message: {data.get('message')}")
                if data.get('hint'):
                    print(f"Hint: {data.get('hint')}")
        else:
            print(f"\n❌ Request failed with status {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to backend!")
        print(f"Make sure the backend is running on {BASE_URL}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_notification()
