"""
Enhanced email parser with DeepSeek integration
"""
import re
import json

class EmailParserAgent:
    def __init__(self, llm_service):
        self.llm = llm_service
        
    def parse_meeting_request(self, email_content, subject=""):
        """Enhanced parsing with DeepSeek LLM"""
        
        print(f"Parsing email: {email_content[:100]}...")
        
        # Try DeepSeek LLM first
        llm_result = self._try_llm_parsing(email_content, subject)
        if llm_result:
            print(f"LLM parsed: {llm_result}")
            return llm_result
        
        # Fallback to enhanced rule-based
        fallback_result = self._enhanced_rule_parsing(email_content, subject)
        print(f"Fallback parsed: {fallback_result}")
        return fallback_result
    
    def _try_llm_parsing(self, email_content, subject):
        """Try DeepSeek LLM parsing"""
        try:
            prompt = f"""
            Extract meeting details from this email. Return ONLY valid JSON:
            {{
                "requested_time": "11:00 AM IST",
                "duration_minutes": 30,
                "urgency": "normal",
                "meeting_type": "sync",
                "date_mentioned": "Thursday, 17 July 2025",
                "timezone": "IST",
                "preferences": ["morning", "specific_time"]
            }}
            
            Email Subject: {subject}
            Email Content: {email_content}
            
            Focus on extracting the EXACT time mentioned and date.
            """
            
            response = self.llm.generate(prompt, temperature=0.1)
            if response:
                # Clean response
                response = response.strip()
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                
                return json.loads(response)
        except Exception as e:
            print(f"LLM parsing failed: {e}")
        
        return None
    
    def _enhanced_rule_parsing(self, email_content, subject):
        """Enhanced rule-based parsing"""
        content = (email_content + " " + subject).lower()
        
        # Extract specific time mentions
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)\s*(ist|utc|gmt)?',
            r'(\d{1,2})\s*(am|pm)\s*(ist|utc|gmt)?',
            r'at\s+(\d{1,2}):(\d{2})',
            r'at\s+(\d{1,2})\s*(am|pm)'
        ]
        
        requested_time = None
        for pattern in time_patterns:
            match = re.search(pattern, content)
            if match:
                requested_time = match.group(0)
                break
        
        # Extract duration
        duration = 30
        duration_patterns = [
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)\s*hours?',
            r'half\s*hour',
            r'quarter\s*hour'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, content)
            if match:
                if 'hour' in pattern:
                    if 'half' in match.group(0):
                        duration = 30
                    elif 'quarter' in match.group(0):
                        duration = 15
                    else:
                        duration = int(match.group(1)) * 60
                else:
                    duration = int(match.group(1))
                break
        
        return {
            "requested_time": requested_time or "flexible",
            "duration_minutes": duration,
            "urgency": "high" if any(word in content for word in ["urgent", "asap"]) else "normal",
            "meeting_type": "sync" if "sync" in content else "meeting",
            "timezone": "IST" if "ist" in content else "UTC",
            "preferences": ["specific_time"] if requested_time else ["flexible"]
        }
