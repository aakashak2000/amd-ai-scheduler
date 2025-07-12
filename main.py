"""
Simple AMD AI Meeting Scheduler
"""
from flask import Flask, request, jsonify
import time
from datetime import datetime, timedelta

from agents.email_parser import EmailParserAgent
from agents.schedule_coordinator import ScheduleCoordinatorAgent
from services.llm_service import LLMService
from services.calendar_service import CalendarService
from utils.json_validator import validate_input, validate_output

app = Flask(__name__)

# Initialize system components
llm_service = LLMService()
calendar_service = CalendarService()
email_parser = EmailParserAgent(llm_service)
schedule_coordinator = ScheduleCoordinatorAgent(calendar_service)

@app.route('/receive', methods=['POST'])
def receive():
    """Process meeting request"""
    start_time = time.time()
    
    try:
        request_data = request.get_json()
        
        if not request_data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        request_id = request_data.get('Request_id', 'Unknown')
        print(f"Processing Request: {request_id}")
        
        # Validate input
        is_valid, errors = validate_input(request_data)
        if not is_valid:
            return jsonify({"error": "Invalid input", "details": errors}), 400
        
        # Process meeting request
        result = process_meeting_request(request_data)
        
        # Log processing time
        total_time = time.time() - start_time
        print(f"Request processed in {total_time:.2f}s")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def process_meeting_request(request_data):
    """Process meeting request with simplified logic"""
    
    # Parse email content
    email_content = request_data.get("EmailContent", "")
    subject = request_data.get("Subject", "")
    meeting_details = email_parser.parse_meeting_request(email_content, subject)
    
    # Get attendees
    attendees = request_data.get("Attendees", [])
    attendee_emails = [att["email"] for att in attendees]
    sender_email = request_data.get("From", "")
    all_attendees = [sender_email] + attendee_emails
    
    # Coordinate meeting
    coordination_result = schedule_coordinator.coordinate_meeting(all_attendees, meeting_details)
    
    # Format response
    return format_response(request_data, coordination_result, all_attendees, meeting_details)

def format_response(request_data, coordination_result, attendees, meeting_details):
    """Format final response"""
    
    scheduled_time = coordination_result.get("scheduled_time", {})
    start_time = scheduled_time.get("start", "2025-07-17T10:30:00+05:30")
    end_time = scheduled_time.get("end", "2025-07-17T11:00:00+05:30")
    
    # Calculate duration
    start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
    end_dt = datetime.fromisoformat(end_time.replace('+05:30', ''))
    duration_mins = int((end_dt - start_dt).total_seconds() / 60)
    
    # Create attendee events
    attendee_events = []
    for email in attendees:
        attendee_events.append({
            "email": email,
            "events": [{
                "StartTime": start_time,
                "EndTime": end_time,
                "NumAttendees": len(attendees),
                "Attendees": attendees,
                "Summary": request_data.get("Subject", "Meeting")
            }]
        })
    
    return {
        **request_data,
        "Attendees": attendee_events,
        "EventStart": start_time,
        "EventEnd": end_time,
        "Duration_mins": str(duration_mins),
        "MetaData": {
            "processing_method": "simple_coordination",
            "success": coordination_result.get("success", True)
        }
    }

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("Starting AMD AI Scheduler...")
    print("API available at: http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
