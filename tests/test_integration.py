"""
Integration tests for the complete system
"""
import requests
import json
import time
import asyncio
from typing import Dict, Any

# Test configuration
API_BASE_URL = "http://localhost:5000"

class TestIntegration:
    """Integration test suite"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_time = 0
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        print("\n🏥 Testing health endpoint...")
        
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed")
                print(f"📊 Components: {health_data.get('components', {})}")
                self.passed_tests += 1
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            self.failed_tests += 1
            return False
    
    def test_basic_scheduling(self):
        """Test basic scheduling functionality"""
        print("\n📝 Testing basic scheduling...")
        
        test_request = {
            "Request_id": "integration-test-001",
            "Datetime": "12-07-2025T12:34:55",
            "Location": "IIT Mumbai",
            "From": "userone.amd@gmail.com",
            "Attendees": [
                {"email": "usertwo.amd@gmail.com"}
            ],
            "Subject": "Integration Test Meeting",
            "EmailContent": "Let's have a quick 30-minute sync to test the system"
        }
        
        return self._execute_test_request(test_request, "Basic Scheduling")
    
    def test_multi_participant_scheduling(self):
        """Test multi-participant scheduling"""
        print("\n👥 Testing multi-participant scheduling...")
        
        test_request = {
            "Request_id": "integration-test-002", 
            "Datetime": "12-07-2025T12:34:55",
            "Location": "IIT Mumbai",
            "From": "userone.amd@gmail.com",
            "Attendees": [
                {"email": "usertwo.amd@gmail.com"},
                {"email": "userthree.amd@gmail.com"}
            ],
            "Subject": "Multi-Participant Test",
            "EmailContent": "Team meeting to discuss project status. Need everyone for 45 minutes."
        }
        
        return self._execute_test_request(test_request, "Multi-Participant Scheduling")
    
    def test_urgent_scheduling(self):
        """Test urgent meeting scheduling"""
        print("\n🚨 Testing urgent scheduling...")
        
        test_request = {
            "Request_id": "integration-test-003",
            "Datetime": "12-07-2025T12:34:55", 
            "Location": "IIT Mumbai",
            "From": "userone.amd@gmail.com",
            "Attendees": [
                {"email": "usertwo.amd@gmail.com"},
                {"email": "userthree.amd@gmail.com"}
            ],
            "Subject": "URGENT: Crisis Response Meeting",
            "EmailContent": "Urgent meeting needed ASAP to address client issues. Need immediate response."
        }
        
        return self._execute_test_request(test_request, "Urgent Scheduling")
    
    def test_performance_requirements(self):
        """Test performance requirements"""
        print("\n⚡ Testing performance requirements...")
        
        test_request = {
            "Request_id": "integration-test-perf",
            "Datetime": "12-07-2025T12:34:55",
            "Location": "IIT Mumbai", 
            "From": "userone.amd@gmail.com",
            "Attendees": [
                {"email": "usertwo.amd@gmail.com"},
                {"email": "userthree.amd@gmail.com"},
                {"email": "userfour.amd@gmail.com"}
            ],
            "Subject": "Performance Test Meeting",
            "EmailContent": "Complex meeting with multiple participants to test system performance."
        }
        
        start_time = time.time()
        success = self._execute_test_request(test_request, "Performance Test")
        end_time = time.time()
        
        duration = end_time - start_time
        self.total_time += duration
        
        print(f"⏱️  Response time: {duration:.2f}s")
        
        if duration > 10.0:  # 10 second threshold
            print(f"⚠️  Response time above 10s threshold")
        else:
            print(f"✅ Response time within acceptable range")
        
        return success
    
    def _execute_test_request(self, test_request: Dict[str, Any], test_name: str) -> bool:
        """Execute a test request and validate response"""
        
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{API_BASE_URL}/receive",
                json=test_request,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"⏱️  {test_name} response time: {duration:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                
                # Validate required fields
                required_fields = ["Request_id", "EventStart", "EventEnd", "Duration_mins", "Attendees"]
                missing_fields = [field for field in required_fields if field not in result]
                
                if missing_fields:
                    print(f"❌ {test_name} failed - Missing fields: {missing_fields}")
                    self.failed_tests += 1
                    return False
                
                # Validate data types and formats
                if not self._validate_response_format(result):
                    print(f"❌ {test_name} failed - Invalid response format")
                    self.failed_tests += 1
                    return False
                
                print(f"✅ {test_name} passed")
                print(f"📅 Scheduled: {result.get('EventStart')} - {result.get('EventEnd')}")
                
                # Print GPU metrics if available
                metadata = result.get("MetaData", {})
                if "gpu_utilization" in metadata:
                    print(f"📊 GPU Utilization: {metadata['gpu_utilization']}")
                
                self.passed_tests += 1
                return True
                
            else:
                print(f"❌ {test_name} failed - Status: {response.status_code}")
                print(f"Response: {response.text}")
                self.failed_tests += 1
                return False
                
        except Exception as e:
            print(f"❌ {test_name} failed - Error: {e}")
            self.failed_tests += 1
            return False
    
    def _validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate response format matches requirements"""
        
        try:
            # Check EventStart and EventEnd are valid ISO timestamps
            from datetime import datetime
            datetime.fromisoformat(response["EventStart"].replace('+05:30', ''))
            datetime.fromisoformat(response["EventEnd"].replace('+05:30', ''))
            
            # Check Duration_mins is numeric
            int(response["Duration_mins"])
            
            # Check Attendees structure
            attendees = response.get("Attendees", [])
            if not isinstance(attendees, list):
                return False
            
            for attendee in attendees:
                if not isinstance(attendee, dict) or "email" not in attendee or "events" not in attendee:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def run_all_tests(self):
        """Run complete integration test suite"""
        
        print("\n" + "="*60)
        print("🧪 AMD AI Scheduler - Integration Test Suite")
        print("="*60)
        
        start_time = time.time()
        
        # Run tests in sequence
        tests = [
            self.test_health_endpoint,
            self.test_basic_scheduling,
            self.test_multi_participant_scheduling,
            self.test_urgent_scheduling,
            self.test_performance_requirements
        ]
        
        for test in tests:
            test()
            time.sleep(1)  # Brief pause between tests
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Print summary
        print("\n" + "="*60)
        print("📊 Test Results Summary")
        print("="*60)
        print(f"✅ Tests Passed: {self.passed_tests}")
        print(f"❌ Tests Failed: {self.failed_tests}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        print(f"📈 Success Rate: {(self.passed_tests / (self.passed_tests + self.failed_tests) * 100):.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 All tests passed! System ready for hackathon.")
        else:
            print(f"\n⚠️  {self.failed_tests} tests failed. Please check the system.")
        
        return self.failed_tests == 0

def main():
    """Main test execution"""
    tester = TestIntegration()
    success = tester.run_all_tests()
    
    if success:
        exit(0)
    else:
        exit(1)

if __name__ == "__main__":
    main()
