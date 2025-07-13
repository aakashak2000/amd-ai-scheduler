import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from models import EmailParsingResult
from tools import get_current_date, calculate_next_date, extract_duration_from_text

class EmailParserAgent:
    def __init__(self, base_url: str = "http://localhost:3000/v1"):
        # Create provider for local vLLM DeepSeek server
        provider = OpenAIProvider(
            base_url=base_url,
            api_key="dummy"  # vLLM doesn't need real API key
        )
        
        # Use DeepSeek model through vLLM
        self.model = OpenAIModel("deepseek", provider=provider)
        
        self.agent = Agent(
            model=self.model,
            result_type=EmailParsingResult,
            tools=[get_current_date, calculate_next_date, extract_duration_from_text],
            system_prompt="""You are an expert email parser that extracts meeting details from email content.

Your task is to analyze email content and extract:
1. Meeting date (use calculate_next_date tool for relative dates like "next Thursday")
2. Meeting time (if specified)
3. Duration (use extract_duration_from_text tool)
4. Urgency level based on keywords
5. Meeting type based on content

IMPORTANT DATE HANDLING:
- Always use get_current_date() to know what day it is today
- Use calculate_next_date() for any relative date expressions
- "next Thursday" means the Thursday of the upcoming week
- Be precise with date calculations

URGENCY KEYWORDS:
- High: urgent, asap, emergency, critical, immediately
- Medium: important, priority, soon, deadline
- Low: everything else

MEETING TYPES:
- standup: daily standup, scrum, daily meeting
- review: review, retrospective, demo, feedback
- planning: planning, brainstorm, strategy, roadmap
- one_on_one: 1:1, one-on-one, personal meeting
- interview: interview, hiring, candidate
- other: everything else

Return a properly structured EmailParsingResult."""
        )
    
    async def parse_email(self, email_content: str) -> EmailParsingResult:
        """Parse email content to extract meeting details."""
        try:
            result = await self.agent.run(
                f"Parse this email content and extract meeting details: '{email_content}'"
            )
            return result.data
        except Exception as e:
            print(f"Email parsing failed: {e}")
            # Return default values
            return EmailParsingResult(
                suggested_date=await self._get_default_date(),
                suggested_time=None,
                duration_minutes=30,
                urgency='low',
                meeting_type='other'
            )
    
    async def _get_default_date(self) -> str:
        """Get next business day as default."""
        from datetime import datetime, timedelta
        today = datetime.now()
        days_ahead = 1
        while (today + timedelta(days=days_ahead)).weekday() >= 5:  # Skip weekends
            days_ahead += 1
        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')