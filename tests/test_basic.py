import requests
import json

def test_basic_api():
    """Test the basic Flask API"""
    
    test_request = {
        "Request_id": "test-basic",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Basic Test Meeting",
        "EmailContent": "Let's test the basic functionality"
    }
    
    try:
        response = requests.post('http://localhost:9014/receive', json=test_request)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Test Passed!")
            print(f"📅 Scheduled: {result.get('EventStart')} - {result.get('EventEnd')}")
            
            # Validate required fields
            required_fields = ["Request_id", "EventStart", "EventEnd", "Duration_mins", "Attendees"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                print(f"❌ Missing fields: {missing_fields}")
            else:
                print("✅ All required fields present")
                
        else:
            print(f"❌ API Test Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Test Error: {e}")

if __name__ == "__main__":
    test_basic_api()
