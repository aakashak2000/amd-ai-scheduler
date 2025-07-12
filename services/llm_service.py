"""
Simple LLM service for DeepSeek model
"""
import requests
import json
from utils.config import Config

class LLMService:
    def __init__(self):
        self.base_url = Config.LLM_BASE_URL
        self.model_path = Config.LLM_MODEL_PATH
    
    def generate(self, prompt, temperature=0.1, max_tokens=256):
        """Generate LLM response"""
        payload = {
            "model": self.model_path,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"LLM API error {response.status_code}")
                
        except Exception as e:
            print(f"LLM Error: {e}")
            return None
    
    def parse_email_content(self, email_content):
        """Simple email parsing"""
        prompt = f"""
        Extract meeting details from this email. Return only JSON:
        {{
            "duration_minutes": 30,
            "urgency": "normal",
            "meeting_type": "discussion"
        }}
        
        Email: {email_content}
        """
        
        response = self.generate(prompt)
        
        try:
            return json.loads(response)
        except:
            return {
                "duration_minutes": 30,
                "urgency": "normal", 
                "meeting_type": "discussion"
            }
