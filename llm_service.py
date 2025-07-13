import requests
import json
from typing import Dict, List, Optional
import time

class LLMService:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'http://localhost:8000')
        self.model_name = self.config.get('model_name', 'mixtral-8x7b')
        self.timeout = self.config.get('timeout', 5)  # Reduced timeout
        self.max_retries = self.config.get('max_retries', 1)  # Reduced retries
        self.use_mock = True  # Force mock mode for now
        
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        """Generate text using local LLM service or mock"""
        
        if self.use_mock:
            return self._mock_response(prompt)
            
        # Try local vLLM first
        try:
            return self._call_vllm(prompt, system_prompt, max_tokens)
        except Exception as e:
            print(f"vLLM call failed: {e}")
            
            # Fallback to OpenAI if configured
            if self.config.get('openai_api_key'):
                try:
                    return self._call_openai(prompt, system_prompt, max_tokens)
                except Exception as e2:
                    print(f"OpenAI fallback failed: {e2}")
            
            # Final fallback to mock response
            print("Using mock LLM response")
            return self._mock_response(prompt)
    
    def _call_vllm(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        """Call local vLLM service"""
        
        # Format prompt for Mixtral
        if system_prompt:
            formatted_prompt = f"<s>[INST] {system_prompt}\n\n{prompt} [/INST]"
        else:
            formatted_prompt = f"<s>[INST] {prompt} [/INST]"
        
        payload = {
            "model": self.model_name,
            "prompt": formatted_prompt,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stop": ["</s>", "[INST]", "[/INST]"]
        }
        
        response = requests.post(
            f"{self.base_url}/v1/completions",
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result['choices'][0]['text'].strip()
    
    def _call_openai(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        """Fallback to OpenAI API"""
        import openai
        
        openai.api_key = self.config['openai_api_key']
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def _mock_response(self, prompt: str) -> str:
        """Mock response when LLM services are unavailable"""
        prompt_lower = prompt.lower()
        
        # Email parsing responses
        if 'parse' in prompt_lower and 'email' in prompt_lower:
            return json.dumps({
                "suggested_date": "2025-07-17",
                "suggested_time": "13:00",
                "duration_minutes": 60,
                "urgency": "medium",
                "meeting_type": "other"
            })
        
        # Proposal evaluation responses
        elif 'evaluate' in prompt_lower and 'proposal' in prompt_lower:
            if 'userthree' in prompt_lower:
                return "This time conflicts with my lunch meeting with customers. I'd prefer an earlier or later slot."
            elif 'usertwo' in prompt_lower:
                return "This time works well for me. Good afternoon slot for productive discussions."
            else:
                return "This time slot works reasonably well with my schedule preferences."
        
        # Alternative suggestion responses
        elif 'alternative' in prompt_lower:
            return "This morning slot would be ideal for focused discussion before other meetings begin."
        
        # Negotiation responses
        elif 'negotiate' in prompt_lower or 'compromise' in prompt_lower:
            return "After analyzing all schedules, 3:00 PM provides the best balance for all participants."
        
        # Selection responses
        elif 'select' in prompt_lower or 'option' in prompt_lower:
            return "0"  # Select first option
        
        else:
            return "I understand your request and will process it accordingly."
    
    async def generate_async(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        """Async version of generate"""
        import asyncio
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.generate, 
            prompt, 
            system_prompt, 
            max_tokens
        )
    
    def batch_generate(self, prompts: List[str], system_prompt: str = None, max_tokens: int = 512) -> List[str]:
        """Generate responses for multiple prompts"""
        results = []
        
        for prompt in prompts:
            try:
                result = self.generate(prompt, system_prompt, max_tokens)
                results.append(result)
            except Exception as e:
                print(f"Batch generation failed for prompt: {e}")
                results.append(self._mock_response(prompt))
        
        return results
    
    def health_check(self) -> Dict:
        """Check if LLM service is available"""
        if self.use_mock:
            return {
                "status": "healthy",
                "service": "mock",
                "model": "mock-llm",
                "note": "Using mock responses - vLLM server not available"
            }
            
        try:
            # Try a simple generation
            test_response = self.generate("Hello", max_tokens=10)
            
            return {
                "status": "healthy",
                "service": "vLLM" if "localhost" in self.base_url else "external",
                "model": self.model_name,
                "response_length": len(test_response)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "fallback_available": bool(self.config.get('openai_api_key')),
                "using_mock": True
            }

class MockLLMService:
    """Dedicated mock LLM service for testing without GPU"""
    
    def __init__(self):
        self.call_count = 0
    
    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        self.call_count += 1
        prompt_lower = prompt.lower()
        
        if 'json' in prompt_lower:
            return json.dumps({
                "suggested_date": "2025-07-17",
                "suggested_time": "14:00",
                "duration_minutes": 30,
                "urgency": "medium",
                "meeting_type": "other"
            })
        
        elif 'accept' in prompt_lower or 'reject' in prompt_lower:
            return "ACCEPT - This time works well for my schedule and preferences."
        
        elif 'alternative' in prompt_lower:
            return "I suggest 2:30 PM or 3:00 PM as alternative times that work better."
        
        else:
            return f"Mock response {self.call_count}: I understand and will process this request."
    
    async def generate_async(self, prompt: str, system_prompt: str = None, max_tokens: int = 512) -> str:
        return self.generate(prompt, system_prompt, max_tokens)
    
    def health_check(self) -> Dict:
        return {
            "status": "healthy",
            "service": "mock",
            "model": "mock-llm",
            "calls_made": self.call_count
        }