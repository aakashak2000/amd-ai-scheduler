"""
Simple configuration for AI Scheduler
"""
import os

class Config:
    # LLM Configuration  
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:3000")
    LLM_MODEL_PATH = "/home/user/Models/deepseek-ai/deepseek-llm-7b-chat"
    
    # API Configuration
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 5000
    
    # Default meeting duration
    DEFAULT_MEETING_DURATION = 30
