import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pytz

class JSONValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_request(self, data: Dict) -> Dict[str, Any]:
        """Validate incoming meeting request in new format"""
        self.errors = []
        self.warnings = []
        
        # Check if data is valid JSON
        if not isinstance(data, dict):
            self.errors.append("Request must be a valid JSON object")
            return self._create_validation_result()
        
        # Required fields for new format
        required_fields = ['Request_id', 'Datetime', 'Location', 'From', 'Attendees', 'Subject', 'EmailContent']
        
        # Validate required fields
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required field: {field}")
            elif data[field] is None or data[field] == "":
                self.errors.append(f"Required field cannot be empty: {field}")
        
        # Validate field types
        self._validate_field_types(data)
        
        # Validate attendees in new format
        self._validate_attendees_new_format(data)
        
        # Validate datetime fields
        self._validate_datetime_fields(data)
        
        return self._create_validation_result()
    
    def validate_response(self, data: Dict) -> Dict[str, Any]:
        """Validate outgoing response in required format"""
        self.errors = []
        self.warnings = []
        
        # Required response fields for new format
        required_response_fields = [
            'Request_id', 'Datetime', 'Location', 'From', 'Attendees', 
            'Subject', 'EmailContent', 'EventStart', 'EventEnd', 'Duration_mins', 'MetaData'
        ]
        
        for field in required_response_fields:
            if field not in data:
                self.errors.append(f"Missing required response field: {field}")
        
        # Validate EventStart and EventEnd if present
        if 'EventStart' in data and data['EventStart']:
            if not self._is_valid_datetime(data['EventStart']):
                self.errors.append("Invalid EventStart datetime format")
        
        if 'EventEnd' in data and data['EventEnd']:
            if not self._is_valid_datetime(data['EventEnd']):
                self.errors.append("Invalid EventEnd datetime format")
        
        # Validate attendees output format
        if 'Attendees' in data:
            self._validate_output_attendees(data['Attendees'])
        
        return self._create_validation_result()
    
    def _validate_field_types(self, data: Dict):
        """Validate field types for new format"""
        
        # EmailContent should be string
        if 'EmailContent' in data and not isinstance(data['EmailContent'], str):
            self.errors.append("EmailContent must be a string")
        
        # Attendees should be list
        if 'Attendees' in data and not isinstance(data['Attendees'], list):
            self.errors.append("Attendees must be a list")
        
        # From should be valid email
        if 'From' in data and data['From']:
            if not self._is_valid_email(data['From']):
                self.errors.append("From field must be a valid email")
    
    def _validate_attendees_new_format(self, data: Dict):
        """Validate attendee structure in new input format"""
        if 'Attendees' not in data:
            return
        
        attendees = data['Attendees']
        
        if len(attendees) == 0:
            self.errors.append("At least one attendee is required")
            return
        
        for i, attendee in enumerate(attendees):
            if not isinstance(attendee, dict):
                self.errors.append(f"Attendee {i} must be an object")
                continue
            
            # Check required attendee fields (simple format)
            if 'email' not in attendee:
                self.errors.append(f"Attendee {i} missing email field")
            elif not self._is_valid_email(attendee['email']):
                self.errors.append(f"Attendee {i} has invalid email format")
    
    def _validate_output_attendees(self, attendees: List[Dict]):
        """Validate attendees in output format"""
        for i, attendee in enumerate(attendees):
            if not isinstance(attendee, dict):
                self.errors.append(f"Output attendee {i} must be an object")
                continue
            
            # Check required fields in output format
            if 'email' not in attendee:
                self.errors.append(f"Output attendee {i} missing email field")
            
            if 'events' not in attendee:
                self.errors.append(f"Output attendee {i} missing events field")
            elif isinstance(attendee['events'], list):
                self._validate_attendee_events(attendee['events'], i)
    
    def _validate_attendee_events(self, events: List[Dict], attendee_index: int):
        """Validate attendee calendar events"""
        for j, event in enumerate(events):
            if not isinstance(event, dict):
                self.errors.append(f"Attendee {attendee_index} event {j} must be an object")
                continue
            
            # Check required event fields
            required_event_fields = ['StartTime', 'EndTime', 'Summary', 'Attendees', 'NumAttendees']
            for field in required_event_fields:
                if field not in event:
                    self.errors.append(f"Attendee {attendee_index} event {j} missing {field}")
            
            # Validate datetime fields
            if 'StartTime' in event and not self._is_valid_datetime(event['StartTime']):
                self.errors.append(f"Attendee {attendee_index} event {j} has invalid StartTime")
            
            if 'EndTime' in event and not self._is_valid_datetime(event['EndTime']):
                self.errors.append(f"Attendee {attendee_index} event {j} has invalid EndTime")
            
            # Check that end time is after start time
            if 'StartTime' in event and 'EndTime' in event:
                try:
                    start_dt = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
                    
                    if end_dt <= start_dt:
                        self.errors.append(f"Attendee {attendee_index} event {j} end time must be after start time")
                except:
                    pass  # Already caught by datetime validation
    
    def _validate_datetime_fields(self, data: Dict):
        """Validate datetime fields"""
        datetime_fields = ['Datetime', 'EventStart', 'EventEnd']
        
        for field in datetime_fields:
            if field in data and data[field]:
                if not self._is_valid_datetime(data[field]):
                    self.errors.append(f"Invalid datetime format for {field}")
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_datetime(self, dt_str: str) -> bool:
        """Validate datetime string format"""
        try:
            # Handle various datetime formats
            if dt_str.endswith('Z'):
                dt_str = dt_str.replace('Z', '+00:00')
            
            datetime.fromisoformat(dt_str)
            return True
        except (ValueError, TypeError):
            try:
                # Try alternative format DD-MM-YYYYTHH:MM:SS
                datetime.strptime(dt_str, '%d-%m-%YT%H:%M:%S')
                return True
            except (ValueError, TypeError):
                return False
    
    def _create_validation_result(self) -> Dict[str, Any]:
        """Create validation result"""
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
    
    def sanitize_request(self, data: Dict) -> Dict:
        """Sanitize and clean request data for new format"""
        sanitized = data.copy()
        
        # Trim whitespace from string fields
        string_fields = ['EmailContent', 'Subject', 'From', 'Location']
        for field in string_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = sanitized[field].strip()
        
        # Add Request_id if missing
        if 'Request_id' not in sanitized or not sanitized['Request_id']:
            sanitized['Request_id'] = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Clean attendee emails
        if 'Attendees' in sanitized and isinstance(sanitized['Attendees'], list):
            for attendee in sanitized['Attendees']:
                if isinstance(attendee, dict) and 'email' in attendee:
                    attendee['email'] = attendee['email'].strip().lower()
        
        return sanitized

def validate_json_request(data: Dict) -> Dict[str, Any]:
    """Convenience function to validate a request"""
    validator = JSONValidator()
    return validator.validate_request(data)

def validate_json_response(data: Dict) -> Dict[str, Any]:
    """Convenience function to validate a response"""
    validator = JSONValidator()
    return validator.validate_response(data)

def sanitize_json_request(data: Dict) -> Dict:
    """Convenience function to sanitize a request"""
    validator = JSONValidator()
    return validator.sanitize_request(data)