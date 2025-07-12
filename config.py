import os
from typing import Dict, Any

# LLM Configuration
LLM_CONFIG = {
    # vLLM local server configuration
    'base_url': os.getenv('VLLM_BASE_URL', 'http://localhost:8000'),
    'model_name': os.getenv('LLM_MODEL', 'mixtral-8x7b'),
    'timeout': int(os.getenv('LLM_TIMEOUT', '30')),
    'max_retries': int(os.getenv('LLM_MAX_RETRIES', '3')),
    
    # OpenAI fallback (optional)
    'openai_api_key': os.getenv('OPENAI_API_KEY'),
    'openai_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
    
    # Generation parameters
    'temperature': float(os.getenv('LLM_TEMPERATURE', '0.7')),
    'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '512')),
    'top_p': float(os.getenv('LLM_TOP_P', '0.9')),
}

# Calendar Service Configuration
CALENDAR_CONFIG = {
    'default_timezone': os.getenv('DEFAULT_TIMEZONE', 'Asia/Kolkata'),
    'business_start_hour': int(os.getenv('BUSINESS_START_HOUR', '9')),
    'business_end_hour': int(os.getenv('BUSINESS_END_HOUR', '18')),
    'working_days': [0, 1, 2, 3, 4],  # Monday to Friday
    'slot_duration_minutes': int(os.getenv('SLOT_DURATION_MINUTES', '15')),
    'buffer_minutes': int(os.getenv('DEFAULT_BUFFER_MINUTES', '15')),
}

# Agent Configuration
AGENT_CONFIG = {
    'max_negotiation_rounds': int(os.getenv('MAX_NEGOTIATION_ROUNDS', '3')),
    'consensus_threshold': float(os.getenv('CONSENSUS_THRESHOLD', '0.6')),
    'preference_weight': float(os.getenv('PREFERENCE_WEIGHT', '0.7')),
    'timezone_fairness_weight': float(os.getenv('TIMEZONE_FAIRNESS_WEIGHT', '0.3')),
    'default_meeting_duration': int(os.getenv('DEFAULT_MEETING_DURATION', '30')),
}

# API Configuration
API_CONFIG = {
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', '5000')),
    'debug': os.getenv('API_DEBUG', 'True').lower() == 'true',
    'cors_enabled': os.getenv('CORS_ENABLED', 'True').lower() == 'true',
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    'file_path': os.getenv('LOG_FILE_PATH', 'scheduler.log'),
    'max_file_size': int(os.getenv('LOG_MAX_FILE_SIZE', '10485760')),  # 10MB
    'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5')),
}

# GPU Configuration (for future GPU acceleration)
GPU_CONFIG = {
    'enabled': os.getenv('GPU_ENABLED', 'False').lower() == 'true',
    'device_id': int(os.getenv('GPU_DEVICE_ID', '0')),
    'memory_fraction': float(os.getenv('GPU_MEMORY_FRACTION', '0.85')),
    'parallel_agents': int(os.getenv('GPU_PARALLEL_AGENTS', '6')),
    'batch_size': int(os.getenv('GPU_BATCH_SIZE', '32')),
}

# User Preferences (default values)
DEFAULT_USER_PREFERENCES = {
    'preferred_times': ['morning', 'afternoon'],
    'buffer_minutes': 15,
    'timezone': 'Asia/Kolkata',
    'max_meeting_length': 120,
    'avoid_lunch': True,
    'seniority_weight': 0.5,
    'avoid_back_to_back': True,
    'focus_time_blocks': False,
}

# Mock Data Configuration
MOCK_CONFIG = {
    'use_mock_llm': os.getenv('USE_MOCK_LLM', 'False').lower() == 'true',
    'use_mock_calendar': os.getenv('USE_MOCK_CALENDAR', 'True').lower() == 'true',
    'demo_mode': os.getenv('DEMO_MODE', 'True').lower() == 'true',
}

# Validation Rules
VALIDATION_RULES = {
    'min_meeting_duration': 15,  # minutes
    'max_meeting_duration': 480,  # 8 hours
    'max_attendees': 20,
    'max_date_range_days': 30,
    'required_fields': ['EmailContent', 'Attendees', 'Duration_mins'],
}

def get_config() -> Dict[str, Any]:
    """Get complete configuration dictionary"""
    return {
        'llm': LLM_CONFIG,
        'calendar': CALENDAR_CONFIG,
        'agent': AGENT_CONFIG,
        'api': API_CONFIG,
        'logging': LOGGING_CONFIG,
        'gpu': GPU_CONFIG,
        'mock': MOCK_CONFIG,
        'validation': VALIDATION_RULES,
        'default_preferences': DEFAULT_USER_PREFERENCES,
    }

def validate_config() -> bool:
    """Validate configuration settings"""
    errors = []
    
    # Check required LLM settings
    if not LLM_CONFIG['base_url']:
        errors.append("LLM base URL not configured")
    
    # Check timezone
    try:
        import pytz
        pytz.timezone(CALENDAR_CONFIG['default_timezone'])
    except:
        errors.append(f"Invalid timezone: {CALENDAR_CONFIG['default_timezone']}")
    
    # Check business hours
    if CALENDAR_CONFIG['business_start_hour'] >= CALENDAR_CONFIG['business_end_hour']:
        errors.append("Invalid business hours configuration")
    
    if errors:
        print("Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True