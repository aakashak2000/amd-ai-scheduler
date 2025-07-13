# main.py - Modified version with enhanced metadata integration
# Only change: import and coordinator initialization

from flask import Flask, request, jsonify
import asyncio
import traceback
from json_validator import sanitize_json_request
from metadata_framework import get_business_metadata, reset_business_metadata



from coordinator_agent import CoordinatorAgent
app = Flask(__name__)

coordinator = CoordinatorAgent()

@app.route('/receive', methods=['POST'])
def receive():
    """Required endpoint with business-friendly metadata"""
    
    # Reset metadata for new request
    reset_business_metadata()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        request_id = data.get('Request_id', 'unknown')
        print(f"\nReceived Request: {request_id}")
        print(f"Email Content: {data.get('EmailContent', '')}")
        print(f"Attendees: {len(data.get('Attendees', []))} participants")
        
        # Sanitize input
        sanitized_data = sanitize_json_request(data)
        
        # Process with multi-agent system
        result = asyncio.run(coordinator.schedule_meeting(sanitized_data))
        
        # Generate business-friendly summary as clean array
        business_summary_lines = get_business_metadata().generate_business_summary()
        
        # Add metadata to response
        if 'MetaData' not in result:
            result['MetaData'] = {}
        
        result['MetaData']['agent_reasoning_summary'] = business_summary_lines
        
        success = result.get('EventStart') is not None and 'error' not in result
        print(f"Processing complete - Success: {success}")
        
        if success:
            print(f"Scheduled: {result['EventStart']} to {result['EventEnd']}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        
        # Include error metadata
        error_summary = get_business_metadata().generate_business_summary()
        
        return jsonify({
            "error": str(e),
            "Request_id": request.get_json().get('Request_id', 'unknown') if request.get_json() else 'unknown',
            "MetaData": {
                "agent_reasoning_summary": error_summary,
                "error_context": {
                    "error_type": type(e).__name__,
                    "processing_stage": "main_api"
                }
            }
            }), 500
            

if __name__ == '__main__':    
    app.run(host='0.0.0.0', port=5000, debug=True)