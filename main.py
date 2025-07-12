from flask import Flask, request, jsonify
import asyncio
import traceback
from coordinator_agent import CoordinatorAgent
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

if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=5000, debug=True)