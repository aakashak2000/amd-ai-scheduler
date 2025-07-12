"""
Test all provided hackathon scenarios
"""
import requests
import json
import time

API_BASE_URL = "http://localhost:5000"

def test_scenario_1_all_available():
    """Test Case 1: USERTWO & USERTHREE are available"""
    print("\n🧪 Test Scenario 1: All Available")
    
    request_data = {
        "Request_id": "scenario-1-001",
        "Datetime": "02-07-2025T12:34:55",
        "Location": "IIT Mumbai",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Team Goals Discussion",
        "EmailContent": "Hi Team. Let's meet next Thursday and discuss about our Goals."
    }
    
    return execute_scenario_test(request_data, "All participants available")

def test_scenario_2_partial_conflict():
    """Test Case 2: USERTWO available, USERTHREE busy"""
    print("\n🧪 Test Scenario 2: Partial Conflict")
    
    request_data = {
        "Request_id": "scenario-2-002", 
        "Datetime": "02-07-2025T12:34:55",
        "Location": "IIT Mumbai",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Urgent Client Feedback",
        "EmailContent": "Hi Team. We've just received quick feedback from the client indicating that the instructions we provided aren't working on their end. Let's prioritize resolving this promptly. Let's meet Monday at 9:00 AM to discuss and resolve this issue."
    }
    
    return execute_scenario_test(request_data, "Partial conflict scenario")

def test_scenario_3_complex_conflicts():
    """Test Case 3: Both USERTWO & USERTHREE busy"""
    print("\n🧪 Test Scenario 3: Complex Conflicts")
    
    request_data = {
        "Request_id": "scenario-3-003",
        "Datetime": "02-07-2025T12:34:55", 
        "Location": "IIT Mumbai",
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Project Status Review",
        "EmailContent": "Hi Team. Let's meet on Tuesday at 11:00 A.M and discuss about our on-going Projects."
    }
    
    return execute_scenario_test(request_data, "Complex conflicts scenario")

def test_scenario_4_priority_scheduling():
    """Test Case 4: USERTWO free but USERTHREE busy"""
    print("\n🧪 Test Scenario 4: Priority Scheduling")
    
    request_data = {
        "Request_id": "scenario-4-004",
        "Datetime": "02-07-2025T12:34:55",
        "Location": "IIT Mumbai", 
        "From": "userone.amd@gmail.com",
        "Attendees": [
            {"email": "usertwo.amd@gmail.com"},
            {"email": "userthree.amd@gmail.com"}
        ],
        "Subject": "Client Feedback Review",
        "EmailContent": "Hi Team. We've received the final feedback from the client. Let's review it together and plan next steps. Let's meet on Wednesday at 10:00 A.M."
    }
    
    return execute_scenario_test(request_data, "Priority scheduling scenario")

def execute_scenario_test(request_data, description):
    """Execute a scenario test"""
    
    print(f"📋 Testing: {description}")
    print(f"📧 Request ID: {request_data['Request_id']}")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{API_BASE_URL}/receive",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=20
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Test passed - Response time: {duration:.2f}s")
            print(f"📅 Scheduled time: {result.get('EventStart')} - {result.get('EventEnd')}")
            print(f"⏱️  Duration: {result.get('Duration_mins')} minutes")
            
            # Print metadata if available
            metadata = result.get("MetaData", {})
            if metadata:
                print(f"📊 Metadata:")
                for key, value in metadata.items():
                    if key not in ["processing_method"]:  # Skip verbose fields
                        print(f"   {key}: {value}")
            
            # Validate required fields
            required_fields = ["Request_id", "EventStart", "EventEnd", "Duration_mins", "Attendees"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                print(f"⚠️  Warning: Missing fields {missing_fields}")
                return False
            
            print(f"✅ All required fields present")
            return True
            
        else:
            print(f"❌ Test failed - Status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def run_all_scenarios():
    """Run all hackathon scenarios"""
    
    print("\n" + "="*60)
    print("🎯 AMD Hackathon - Scenario Test Suite")
    print("="*60)
    
    scenarios = [
        test_scenario_1_all_available,
        test_scenario_2_partial_conflict,
        test_scenario_3_complex_conflicts,
        test_scenario_4_priority_scheduling
    ]
    
    passed = 0
    failed = 0
    total_time = 0
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'='*20} Scenario {i} {'='*20}")
        start_time = time.time()
        
        success = scenario()
        
        scenario_time = time.time() - start_time
        total_time += scenario_time
        
        if success:
            passed += 1
        else:
            failed += 1
        
        time.sleep(2)  # Brief pause between scenarios
    
    # Print final summary
    print("\n" + "="*60)
    print("📊 Scenario Test Results")
    print("="*60)
    print(f"✅ Scenarios Passed: {passed}/4")
    print(f"❌ Scenarios Failed: {failed}/4")
    print(f"⏱️  Total Time: {total_time:.2f}s")
    print(f"📈 Success Rate: {(passed/4*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All scenarios passed! Ready for hackathon submission.")
    else:
        print(f"\n⚠️  {failed} scenarios failed. System needs attention.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_scenarios()
    exit(0 if success else 1)
