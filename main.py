from flask import Flask, request, jsonify
import asyncio
import json
from datetime import datetime
import traceback
from coordinator_agent import CoordinatorAgent
from mock_data import TEST_SCENARIOS
from json_validator import sanitize_json_request

app = Flask(__name__)

# Initialize the coordinator
coordinator = CoordinatorAgent()

@app.route('/receive', methods=['POST'])
def receive():
    """Required endpoint for hackathon submission"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        print(f"\nReceived Request: {data.get('Request_id', 'unknown')}")
        print(f"Email Content: {data.get('EmailContent', '')}")
        print(f"Attendees: {len(data.get('Attendees', []))} participants")
        
        # Sanitize input
        sanitized_data = sanitize_json_request(data)
        
        # Process with multi-agent system
        result = asyncio.run(coordinator.schedule_meeting(sanitized_data))
        
        success = result.get('EventStart') is not None and 'error' not in result
        print(f"Processing complete - Success: {success}")
        
        if success:
            print(f"Scheduled: {result['EventStart']} to {result['EventEnd']}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing request: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "Request_id": request.get_json().get('Request_id', 'unknown') if request.get_json() else 'unknown'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        status = asyncio.run(coordinator.get_system_status())
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/demo/<scenario_name>', methods=['GET'])
def demo_scenario(scenario_name):
    """Demo endpoint for testing scenarios"""
    if scenario_name not in TEST_SCENARIOS:
        available_scenarios = list(TEST_SCENARIOS.keys())
        return jsonify({
            "error": "Scenario not found",
            "available_scenarios": available_scenarios
        }), 404
    
    try:
        scenario_data = TEST_SCENARIOS[scenario_name]
        print(f"\nRunning Demo Scenario: {scenario_name}")
        print(f"Scenario description: {scenario_data.get('EmailContent', '')}")
        
        result = asyncio.run(coordinator.schedule_meeting(scenario_data))
        
        return jsonify({
            "scenario": scenario_name,
            "input": scenario_data,
            "result": result,
            "success": result.get('EventStart') is not None and 'error' not in result
        })
        
    except Exception as e:
        print(f"Demo scenario error: {e}")
        traceback.print_exc()
        return jsonify({
            "scenario": scenario_name,
            "error": str(e)
        }), 500

@app.route('/test', methods=['POST'])
def test_custom():
    """Test endpoint for custom requests"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Add default values if missing
        if 'Duration_mins' not in data:
            data['Duration_mins'] = '30'
        if 'Request_id' not in data:
            data['Request_id'] = f"test_{datetime.now().strftime('%H%M%S')}"
        if 'Attendees' not in data:
            data['Attendees'] = []
        
        print(f"\nTesting Custom Request: {data['Request_id']}")
        
        result = asyncio.run(coordinator.schedule_meeting(data))
        return jsonify(result)
        
    except Exception as e:
        print(f"Test error: {e}")
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "request_id": data.get('Request_id', 'unknown') if 'data' in locals() else 'unknown'
        }), 500

@app.route('/scenarios', methods=['GET'])
def list_scenarios():
    """List available demo scenarios"""
    scenarios_info = {}
    for name, scenario in TEST_SCENARIOS.items():
        scenarios_info[name] = {
            'description': scenario.get('EmailContent', ''),
            'attendees_count': len(scenario.get('Attendees', [])),
            'duration': scenario.get('Duration_mins', '30'),
            'endpoint': f"/demo/{name}"
        }
    
    return jsonify({
        "available_scenarios": scenarios_info,
        "total_scenarios": len(TEST_SCENARIOS)
    })

@app.route('/llm/status', methods=['GET'])
def llm_status():
    """Check LLM service status"""
    try:
        status = coordinator.llm.health_check()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/validate', methods=['POST'])
def validate_request():
    """Validate a meeting request without processing"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate the request
        from json_validator import validate_json_request
        validation_result = validate_json_request(data)
        
        return jsonify({
            "validation_result": validation_result,
            "sanitized_data": sanitize_json_request(data) if validation_result['valid'] else None
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "validation_result": {
                "valid": False,
                "errors": [str(e)]
            }
        }), 500
