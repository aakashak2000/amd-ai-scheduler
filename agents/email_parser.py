"""
Simple email parser agent
"""
import re

class EmailParserAgent:
    def __init__(self, llm_service):
        self.llm = llm_service
        
    def parse_meeting_request(self, email_content, subject=""):
        """Parse email content for meeting details"""
        
        # Try LLM first, fallback to simple parsing
        try:
            if self.llm:
                details = self.llm.parse_email_content(email_content)
                if details:
                    return details
        except:
            pass
        
        # Fallback simple parsing
        return self._simple_parse(email_content, subject)
    
    def _simple_parse(self, email_content, subject):
        """Simple rule-based parsing"""
        content = (email_content + " " + subject).lower()
        
        # Extract duration
        duration = 30
        if "hour" in content or "1h" in content:
            duration = 60
        elif "15 min" in content:
            duration = 15
        elif "45 min" in content:
            duration = 45
        
        # Extract urgency
        urgency = "normal"
        if any(word in content for word in ["urgent", "asap", "immediately"]):
            urgency = "high"
        
        return {
            "duration_minutes": duration,
            "urgency": urgency,
            "meeting_type": "discussion"
        }
