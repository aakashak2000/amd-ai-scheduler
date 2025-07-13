import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing import List, Dict, Any
from models import ParticipantEvaluation, TimeSlot, UserPreferences, CalendarEvent
from tools import (
    get_current_date, 
    find_calendar_conflicts, 
    calculate_preference_score,
    check_business_hours,
    convert_time_across_timezones,
    generate_time_slots
)

class ParticipantAgent:
    def __init__(self, 
                 email: str, 
                 calendar_events: List[CalendarEvent], 
                 preferences: UserPreferences,
                 base_url: str = "http://localhost:3000/v1"):
        
        self.email = email
        self.calendar_events = [event.dict() for event in calendar_events]
        self.preferences = preferences.dict()
        
        # Create provider for local vLLM DeepSeek server
        provider = OpenAIProvider(
            base_url=base_url,
            api_key="dummy"
        )
        
        self.model = OpenAIModel("deepseek", provider=provider)
        
        self.agent = Agent(
            model=self.model,
            result_type=ParticipantEvaluation,
            tools=[
                get_current_date,
                find_calendar_conflicts,
                calculate_preference_score,
                check_business_hours,
                convert_time_across_timezones
            ],
            system_prompt=f"""You are {email}'s intelligent scheduling assistant.

Your role is to evaluate proposed meeting times based on:
1. Calendar conflicts (use find_calendar_conflicts tool)
2. Personal preferences: {self.preferences}
3. Business hours in your timezone
4. Work-life balance considerations

DECISION CRITERIA:
- REJECT if there are hard calendar conflicts
- REJECT if outside business hours or personal preferences
- CONDITIONAL_ACCEPT if time is workable but not ideal
- ACCEPT if time works well with schedule and preferences

REASONING STYLE:
- Be professional and concise
- Explain your decision clearly
- Consider timezone implications
- Mention specific conflicts or preferences
- Suggest alternatives when rejecting

You have access to your calendar events and can check for conflicts.
Always provide honest, helpful feedback about proposed meeting times."""
        )
    
    async def evaluate_proposal(self, proposed_slot: TimeSlot) -> ParticipantEvaluation:
        """Evaluate a proposed meeting time slot."""
        try:
            prompt = f"""
            Evaluate this proposed meeting time for {self.email}:
            
            Proposed Time: {proposed_slot.start_time} to {proposed_slot.end_time}
            Duration: {proposed_slot.duration_minutes} minutes
            
            My Calendar Events: {self.calendar_events}
            My Preferences: {self.preferences}
            
            Use the available tools to:
            1. Check for calendar conflicts with find_calendar_conflicts
            2. Calculate preference score with calculate_preference_score  
            3. Check if time is in business hours with check_business_hours
            
            Provide a decision (ACCEPT/REJECT/CONDITIONAL_ACCEPT) with clear reasoning.
            """
            
            result = await self.agent.run(prompt)
            return result.data
            
        except Exception as e:
            print(f"Evaluation failed for {self.email}: {e}")
            # Return default rejection
            return ParticipantEvaluation(
                participant=self.email,
                decision='REJECT',
                reason='evaluation_error',
                preference_score=0.0,
                timezone=self.preferences.get('timezone', 'Asia/Kolkata'),
                llm_reasoning=f"Error evaluating proposal: {str(e)}"
            )
    
    async def find_available_slots(self, date: str, duration_minutes: int) -> List[TimeSlot]:
        """Find available time slots for a given date."""
        try:
            # Generate all possible slots for the day
            timezone = self.preferences.get('timezone', 'Asia/Kolkata')
            all_slots = generate_time_slots(date, duration_minutes, timezone)
            
            available_slots = []
            for slot_data in all_slots:
                if 'error' in slot_data:
                    continue
                
                # Check for conflicts
                conflicts = find_calendar_conflicts(
                    self.calendar_events,
                    slot_data['start_time'],
                    slot_data['end_time'],
                    self.preferences.get('buffer_minutes', 15)
                )
                
                # If no conflicts, calculate preference score
                if not conflicts:
                    pref_score = calculate_preference_score(
                        slot_data['start_time'],
                        self.preferences
                    )
                    
                    time_slot = TimeSlot(
                        start_time=slot_data['start_time'],
                        end_time=slot_data['end_time'],
                        duration_minutes=duration_minutes,
                        participants=[self.email],
                        preference_score=pref_score,
                        time_display=slot_data['time_display']
                    )
                    available_slots.append(time_slot)
            
            # Sort by preference score
            available_slots.sort(key=lambda x: x.preference_score or 0, reverse=True)
            return available_slots
            
        except Exception as e:
            print(f"Error finding slots for {self.email}: {e}")
            return []
    
    async def suggest_alternatives(self, rejected_slot: TimeSlot) -> List[TimeSlot]:
        """Suggest alternative time slots when rejecting a proposal."""
        try:
            # Extract date from rejected slot
            from datetime import datetime
            dt = datetime.fromisoformat(rejected_slot.start_time)
            date = dt.strftime('%Y-%m-%d')
            
            # Find available slots
            available = await self.find_available_slots(date, rejected_slot.duration_minutes)
            
            # Return top 3 alternatives
            return available[:3]
            
        except Exception as e:
            print(f"Error generating alternatives for {self.email}: {e}")
            return []