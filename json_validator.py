import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pytz
from config import VALIDATION_RULES

class JSONValidator:
    def __init__(self, validation_rules: Dict = None):
        self.rules = validation_rules or VALIDATION_RULES
        self.errors = []
        self.warnings = []
    
    def validate_request(self, data: Dict) -> Dict[str, Any]:
        """Validate incoming meeting request"""
        self.errors = []
        self.warnings = []
        
        # Check if data is valid JSON
        if not isinstance(data, dict):
            self.errors.append("Request must be a valid JSON object")
            return self._create_validation_result()
        
        # Validate required fields
        self._validate_required_fields(data)
        
        # Validate field types and values
        self._validate_field_types(data)
        
        # Validate business logic
        self._validate_business_logic(data)
        
        # Validate attendees
        self._validate_attendees(data)
        
        # Validate datetime fields
        self._validate_datetime_fields(data)
        
        return self._create_validation_result()
    
    def validate_response(self, data: Dict) -> Dict[str, Any]:
        """Validate outgoing response"""
        self.errors = []
        self.warnings = []
        
        # Check required response fields
        required_response_fields = [
            'Request_id', 'Subject', 'From', 'EmailContent', 
            'Duration_mins', 'Attendees', 'MetaData'
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
        
        # Validate MetaData structure
        if 'MetaData' in data:
            self._validate_metadata(data['MetaData'])
        
        return self._create_validation_result()
    
    def _validate_required_fields(self, data: Dict):
        """Validate required fields are present"""
        required_fields = self.rules.get('required_fields', [])
        
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required field: {field}")
            elif data[field] is None or data[field] == "":
                self.errors.append(f"Required field cannot be empty: {field}")
    
    def _validate_field_types(self, data: Dict):
        """Validate field types"""
        
        # EmailContent should be string
        if 'EmailContent' in data and not isinstance(data['EmailContent'], str):
            self.errors.append("EmailContent must be a string")
        
        # Duration_mins should be convertible to int
        if 'Duration_mins' in data:
            try:
                duration = int(data['Duration_mins'])
                if duration < self.rules['min_meeting_duration']:
                    self.errors.append(f"Meeting duration too short (minimum {self.rules['min_meeting_duration']} minutes)")
                elif duration > self.rules['max_meeting_duration']:
                    self.errors.append(f"Meeting duration too long (maximum {self.rules['max_meeting_duration']} minutes)")
            except (ValueError, TypeError):
                self.errors.append("Duration_mins must be a valid number")
        
        # Attendees should be list
        if 'Attendees' in data and not isinstance(data['Attendees'], list):
            self.errors.append("Attendees must be a list")
    
    def _validate_business_logic(self, data: Dict):
        """Validate business logic rules"""
        
        # Check attendee count
        if 'Attendees' in data:
            attendee_count = len(data['Attendees'])
            if attendee_count == 0:
                self.errors.append("At least one attendee is required")
            elif attendee_count > self.rules['max_attendees']:
                self.errors.append(f"Too many attendees (maximum {self.rules['max_attendees']})")
        
        # Check for reasonable email content length
        if 'EmailContent' in data:
            content_length = len(data['EmailContent'])
            if content_length < 10:
                self.warnings.append("Email content seems very short")
            elif content_length > 1000:
                self.warnings.append("Email content seems very long")
    
    def _validate_attendees(self, data: Dict):
        """Validate attendee structure"""
        if 'Attendees' not in data:
            return
        
        attendees = data['Attendees']
        
        for i, attendee in enumerate(attendees):
            if not isinstance(attendee, dict):
                self.errors.append(f"Attendee {i} must be an object")
                continue
            
            # Check required attendee fields
            if 'email' not in attendee:
                self.errors.append(f"Attendee {i} missing email field")
            elif not self._is_valid_email(attendee['email']):
                self.errors.append(f"Attendee {i} has invalid email format")
            
            # Validate events if present
            if 'events' in attendee:
                if not isinstance(attendee['events'], list):
                    self.errors.append(f"Attendee {i} events must be a list")
                else:
                    self._validate_attendee_events(attendee['events'], i)
    
    def _validate_attendee_events(self, events: List[Dict], attendee_index: int):
        """Validate attendee calendar events"""
        for j, event in enumerate(events):
            if not isinstance(event, dict):
                self.errors.append(f"Attendee {attendee_index} event {j} must be an object")
                continue
            
            # Check required event fields
            required_event_fields = ['StartTime', 'EndTime', 'Summary']
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
    
    def _validate_metadata(self, metadata: Dict):
        """Validate metadata structure"""
        if not isinstance(metadata, dict):
            self.errors.append("MetaData must be an object")
            return
        
        # Check for required metadata sections
        expected_sections = ['scheduling_decision', 'conflict_resolution']
        
        for section in expected_sections:
            if section not in metadata:
                self.warnings.append(f"MetaData missing recommended section: {section}")
        
        # Validate scheduling_decision structure
        if 'scheduling_decision' in metadata:
            decision = metadata['scheduling_decision']
            if not isinstance(decision, dict):
                self.errors.append("scheduling_decision must be an object")
            else:
                if 'chosen_slot' not in decision:
                    self.warnings.append("scheduling_decision missing chosen_slot")
                if 'why_this_time' not in decision:
                    self.warnings.append("scheduling_decision missing why_this_time explanation")
    
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
                # Try alternative format
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
        """Sanitize and clean request data"""
        sanitized = data.copy()
        
        # Trim whitespace from string fields
        string_fields = ['EmailContent', 'Subject', 'From', 'Location']
        for field in string_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = sanitized[field].strip()
        
        # Ensure Duration_mins is string
        if 'Duration_mins' in sanitized:
            sanitized['Duration_mins'] = str(sanitized['Duration_mins'])
        
        # Add Request_id if missing
        if 'Request_id' not in sanitized or not sanitized['Request_id']:
            sanitized['Request_id'] = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add default Subject if missing
        if 'Subject' not in sanitized or not sanitized['Subject']:
            sanitized['Subject'] = "Meeting"
        
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