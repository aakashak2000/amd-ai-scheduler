import re
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pytz

class EmailParser:
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        
        # Common time patterns
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)',
            r'(\d{1,2})\s*(AM|PM|am|pm)',
            r'(\d{1,2}):(\d{2})',
            r'at\s+(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?',
            r'at\s+(\d{1,2})\s*(AM|PM|am|pm)'
        ]
        
        # Date patterns
        self.date_patterns = [
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
            r'(tomorrow|today|next week)',
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})',
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)'
        ]
        
        # Duration patterns
        self.duration_patterns = [
            r'(\d+)\s*(minutes?|mins?|hours?|hrs?)',
            r'for\s+(\d+)\s*(minutes?|mins?|hours?|hrs?)',
            r'(\d+)-minute',
            r'(\d+)-hour'
        ]

    def parse_email(self, email_content: str) -> Dict:
        """Parse email content to extract meeting details"""
        
        # Use LLM for complex parsing if available
        if self.llm_service:
            llm_result = self._parse_with_llm(email_content)
            if llm_result:
                return llm_result
        
        # Fallback to regex parsing
        return self._parse_with_regex(email_content)
    
    def _parse_with_llm(self, email_content: str) -> Optional[Dict]:
        """Use LLM to parse email content"""
        try:
            prompt = f"""
            Extract meeting details from this email:
            "{email_content}"
            
            Return JSON with:
            - suggested_date: YYYY-MM-DD format
            - suggested_time: HH:MM format (24-hour)
            - duration_minutes: integer
            - urgency: low/medium/high
            - meeting_type: standup/review/planning/other
            
            If any field cannot be determined, use null.
            """
            
            response = self.llm_service.generate(prompt)
            
            # Parse LLM response (assumes JSON format)
            import json
            return json.loads(response)
            
        except Exception as e:
            print(f"LLM parsing failed: {e}")
            return None
    
    def _parse_with_regex(self, email_content: str) -> Dict:
        """Fallback regex-based parsing"""
        content_lower = email_content.lower()
        
        # Extract time
        suggested_time = self._extract_time(email_content)
        
        # Extract date
        suggested_date = self._extract_date(email_content)
        
        # Extract duration
        duration_minutes = self._extract_duration(email_content)
        
        # Determine urgency
        urgency = self._determine_urgency(email_content)
        
        # Determine meeting type
        meeting_type = self._determine_meeting_type(email_content)
        
        return {
            'suggested_date': suggested_date,
            'suggested_time': suggested_time,
            'duration_minutes': duration_minutes,
            'urgency': urgency,
            'meeting_type': meeting_type
        }
    
    def _extract_time(self, content: str) -> Optional[str]:
        """Extract time from email content"""
        for pattern in self.time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) >= 2:
                    hour = int(groups[0])
                    minute = int(groups[1]) if groups[1] else 0
                    
                    # Handle AM/PM
                    if len(groups) > 2 and groups[2]:
                        period = groups[2].upper()
                        if period == 'PM' and hour != 12:
                            hour += 12
                        elif period == 'AM' and hour == 12:
                            hour = 0
                    
                    return f"{hour:02d}:{minute:02d}"
        
        return None
    
    def _extract_date(self, content: str) -> Optional[str]:
        """Extract date from email content"""
        today = datetime.now()
        
        # Check for relative dates
        if 'tomorrow' in content.lower():
            target_date = today + timedelta(days=1)
            return target_date.strftime('%Y-%m-%d')
        
        if 'today' in content.lower():
            return today.strftime('%Y-%m-%d')
        
        if 'next week' in content.lower():
            target_date = today + timedelta(days=7)
            return target_date.strftime('%Y-%m-%d')
        
        # Check for specific weekdays
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(weekdays):
            if day in content.lower():
                days_ahead = i - today.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
        
        # Check for date patterns
        for pattern in self.date_patterns[2:]:  # Skip weekday patterns
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                # Handle different date formats
                try:
                    groups = match.groups()
                    if '/' in pattern:
                        month, day, year = groups
                        return f"{year}-{month:0>2}-{day:0>2}"
                    elif '-' in pattern:
                        month, day, year = groups
                        return f"{year}-{month:0>2}-{day:0>2}"
                except:
                    continue
        
        # Default to tomorrow if no date found
        tomorrow = today + timedelta(days=1)
        return tomorrow.strftime('%Y-%m-%d')
    
    def _extract_duration(self, content: str) -> int:
        """Extract meeting duration from email content"""
        for pattern in self.duration_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                groups = match.groups()
                number = int(groups[0])
                unit = groups[1].lower() if len(groups) > 1 else 'minutes'
                
                if 'hour' in unit:
                    return number * 60
                else:
                    return number
        
        # Default duration
        return 30
    
    def _determine_urgency(self, content: str) -> str:
        """Determine meeting urgency"""
        content_lower = content.lower()
        
        urgent_keywords = ['urgent', 'asap', 'immediately', 'emergency', 'critical']
        high_keywords = ['important', 'priority', 'deadline', 'soon']
        
        if any(keyword in content_lower for keyword in urgent_keywords):
            return 'high'
        elif any(keyword in content_lower for keyword in high_keywords):
            return 'medium'
        else:
            return 'low'
    
    def _determine_meeting_type(self, content: str) -> str:
        """Determine meeting type"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['standup', 'daily', 'scrum']):
            return 'standup'
        elif any(keyword in content_lower for keyword in ['review', 'retrospective', 'demo']):
            return 'review'
        elif any(keyword in content_lower for keyword in ['planning', 'brainstorm', 'strategy']):
            return 'planning'
        elif any(keyword in content_lower for keyword in ['1:1', 'one-on-one', 'feedback']):
            return 'one_on_one'
        elif any(keyword in content_lower for keyword in ['interview', 'hiring']):
            return 'interview'
        else:
            return 'other'