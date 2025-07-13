from flask import Flask, request, jsonify
import asyncio
import traceback
import os
from coordinator_agent_pydantic import CoordinatorAgent
from json_validator import sanitize_json_request

app = Flask(__name__)

# Initialize coordinator with DeepSeek via vLLM
VLLM_BASE_URL = os.getenv('VLLM_BASE_URL', 'http://localhost:3000/v1')

print(f"Using DeepSeek model via vLLM at {VLLM_BASE_URL}")
coordinator = CoordinatorAgent(base_url=VLLM_BASE_URL)

@app.route('/receive', methods=['POST'])
def receive():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        print(f"\nReceived Request: {data.get('Request_id', 'unknown')}")
        print(f"Email Content: {data.get('EmailContent', '')}")
        print(f"Attendees: {len(data.get('Attendees', []))} participants")
        
        # Sanitize input
        sanitized_data = sanitize_json_request(data)
        
        # Process with Pydantic AI multi-agent system
        result = asyncio.run(coordinator.schedule_meeting(sanitized_data))
        
        # Convert Pydantic model to dict
        if hasattr(result, 'dict'):
            response_dict = result.dict()
        else:
            response_dict = result
        
        success = response_dict.get('EventStart') is not None and 'error' not in response_dict
        print(f"Processing complete - Success: {success}")
        
        if success:
            print(f"Scheduled: {response_dict['EventStart']} to {response_dict['EventEnd']}")
        else:
            print(f"Failed: {response_dict.get('error', 'Unknown error')}")
        
        return jsonify(response_dict)
        
    except Exception as e:
        print(f"Error processing request: {e}")
        traceback.print_exc()
        
        return jsonify({
            "error": str(e),
            "Request_id": request.get_json().get('Request_id', 'unknown') if request.get_json() else 'unknown',
            "MetaData": {
                "scheduling_narrative": [
                    "Meeting Scheduling Summary",
                    f"System Error: {str(e)}",
                    "The Pydantic AI scheduling system encountered an unexpected error and could not complete the meeting coordination process."
                ]
            }
        }), 500


if __name__ == '__main__':

    
    app.run(host='0.0.0.0', port=5000, debug=True)