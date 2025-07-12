"""
JSON input/output validation for meeting requests and responses
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class JSONValidator:
    """Validates input and output JSON formats"""
    
    REQUIRED_INPUT_FIELDS = [
        "Request_id", "Datetime", "Location", "From", 
        "Attendees", "Subject", "EmailContent"
    ]
    
    REQUIRED_OUTPUT_FIELDS = [
        "Request_id", "Datetime", "Location", "From",
        "Attendees", "Subject", "EmailContent", 
        "EventStart", "EventEnd", "Duration_mins", "MetaData"
    ]
    
    @staticmethod
    def validate_input(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate input JSON format"""
        errors = []
        
        # Check required fields
        for field in JSONValidator.REQUIRED_INPUT_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate attendees format
        if "Attendees" in data:
            if not isinstance(data["Attendees"], list):
                errors.append("Attendees must be a list")
            else:
                for i, attendee in enumerate(data["Attendees"]):
                    if not isinstance(attendee, dict) or "email" not in attendee:
                        errors.append(f"Attendee {i} must have 'email' field")
        
        # Validate email format (basic)
        if "From" in data:
            if "@" not in data["From"]:
                errors.append("From field must be a valid email")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_output(data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate output JSON format"""
        errors = []
        
        # Check required fields
        for field in JSONValidator.REQUIRED_OUTPUT_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate time format
        time_fields = ["EventStart", "EventEnd"]
        for field in time_fields:
            if field in data:
                try:
                    # Check ISO format with timezone
                    datetime.fromisoformat(data[field].replace('+05:30', ''))
                except ValueError:
                    errors.append(f"{field} must be in ISO format with timezone")
        
        # Validate duration
        if "Duration_mins" in data:
            try:
                int(data["Duration_mins"])
            except ValueError:
                errors.append("Duration_mins must be a number")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def create_error_response(request_id: str, errors: List[str]) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "Request_id": request_id,
            "error": "Validation failed",
            "details": errors,
            "timestamp": datetime.now().isoformat()
        }

def validate_input(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Convenience function for input validation"""
    return JSONValidator.validate_input(data)

def validate_output(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Convenience function for output validation"""
    return JSONValidator.validate_output(data)
