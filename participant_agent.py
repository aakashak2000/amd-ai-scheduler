import asyncio
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any
import json
from llm_service import LLMService

class ParticipantAgent:
    def __init__(self, email: str, calendar_data: List[Dict], preferences: Dict, llm_client=None):
        self.email = email
        self.calendar = calendar_data
        self.preferences = preferences
        self.llm = llm_client or LLMService()
        self.timezone = pytz.timezone(preferences.get('timezone', 'Asia/Kolkata'))
        
    def find_available_slots(self, date_str: str, duration_mins: int, time_window_hours: int = 10) -> List[Dict]:
        """Find all available time slots for the given date"""
        available_slots = []
        
        # Parse the target date
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Business hours: 9 AM to 6 PM in user's timezone
        start_time = self.timezone.localize(datetime.combine(target_date, datetime.min.time().replace(hour=9)))
        end_time = self.timezone.localize(datetime.combine(target_date, datetime.min.time().replace(hour=18)))
        
        # Generate 15-minute slots
        current_time = start_time
        while current_time + timedelta(minutes=duration_mins) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_mins)
            
            if not self._has_conflict(current_time, slot_end):
                preference_score = self._calculate_preference_score(current_time)
                available_slots.append({
                    'start_time': current_time.isoformat(),
                    'end_time': slot_end.isoformat(),
                    'preference_score': preference_score,
                    'participant': self.email
                })
            
            current_time += timedelta(minutes=15)
        
        return sorted(available_slots, key=lambda x: x['preference_score'], reverse=True)
    
    def _has_conflict(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if proposed time conflicts with existing calendar events"""
        for event in self.calendar:
            event_start = datetime.fromisoformat(event['StartTime'].replace('Z', '+00:00'))
            event_end = datetime.fromisoformat(event['EndTime'].replace('Z', '+00:00'))
            
            # Convert to same timezone for comparison
            if event_start.tzinfo != start_time.tzinfo:
                event_start = event_start.astimezone(start_time.tzinfo)
                event_end = event_end.astimezone(start_time.tzinfo)
            
            # Check for overlap with buffer time
            buffer_mins = self.preferences.get('buffer_minutes', 15)
            buffered_start = start_time - timedelta(minutes=buffer_mins)
            buffered_end = end_time + timedelta(minutes=buffer_mins)
            
            if not (buffered_end <= event_start or buffered_start >= event_end):
                return True
        
        return False
    
    def _calculate_preference_score(self, start_time: datetime) -> float:
        """Calculate preference score for a time slot (0-1)"""
        score = 0.5  # Base score
        hour = start_time.hour
        
        # Preferred times
        preferred_times = self.preferences.get('preferred_times', [])
        if 'morning' in preferred_times and 9 <= hour < 12:
            score += 0.3
        elif 'afternoon' in preferred_times and 13 <= hour < 17:
            score += 0.3
        elif 'evening' in preferred_times and 17 <= hour < 20:
            score += 0.2
        
        # Avoid lunch time
        if self.preferences.get('avoid_lunch', False) and 12 <= hour < 14:
            score -= 0.4
        
        # Seniority weight
        seniority = self.preferences.get('seniority_weight', 0.5)
        score = score * (0.7 + 0.6 * seniority)  # Higher seniority = higher weight
        
        return max(0, min(1, score))
    
    async def evaluate_proposal(self, proposed_slot: Dict, context: str = "") -> Dict:
        """Evaluate a proposed meeting time using LLM"""
        start_time = datetime.fromisoformat(proposed_slot['start_time'])
        end_time = datetime.fromisoformat(proposed_slot['end_time'])
        
        # Check hard constraints
        if self._has_conflict(start_time, end_time):
            return {
                'decision': 'REJECT',
                'reason': 'schedule_conflict',
                'preference_score': 0,
                'alternative_suggestions': await self._suggest_alternatives(start_time.date(), 
                                                                         (end_time - start_time).total_seconds() / 60)
            }
        
        # Calculate preference score
        preference_score = self._calculate_preference_score(start_time)
        
        # Use LLM for nuanced evaluation
        llm_evaluation = await self._evaluate_with_llm(proposed_slot, preference_score)
        
        # Decision threshold
        if preference_score >= 0.6:
            decision = 'ACCEPT'
            reason = 'good_time_match'
        elif preference_score >= 0.3:
            decision = 'CONDITIONAL_ACCEPT'
            reason = 'acceptable_but_not_ideal'
        else:
            decision = 'REJECT'
            reason = 'poor_time_preference'
        
        return {
            'decision': decision,
            'reason': reason,
            'preference_score': preference_score,
            'participant': self.email,
            'timezone': str(self.timezone),
            'llm_reasoning': llm_evaluation
        }
    
    async def _evaluate_with_llm(self, proposed_slot: Dict, preference_score: float) -> str:
        """Use LLM to generate evaluation reasoning"""
        start_time = datetime.fromisoformat(proposed_slot['start_time'])
        
        prompt = f"""
        You are {self.email}'s scheduling assistant. Evaluate this meeting proposal:
        
        Proposed Time: {start_time.strftime('%A, %B %d at %I:%M %p %Z')}
        Preference Score: {preference_score:.2f} (0=poor, 1=excellent)
        My Preferences: {self.preferences}
        
        Provide a brief, professional response explaining whether this time works well.
        Keep it under 50 words.
        """
        
        try:
            response = await self.llm.generate_async(prompt, max_tokens=100)
            return response.strip()
        except Exception as e:
            print(f"LLM evaluation failed for {self.email}: {e}")
            return f"Time preference score: {preference_score:.2f}"
    
    async def _suggest_alternatives(self, target_date, duration_mins: int) -> List[Dict]:
        """Suggest alternative time slots using LLM"""
        available_slots = self.find_available_slots(target_date.strftime("%Y-%m-%d"), duration_mins)
        
        # Return top 3 alternatives
        alternatives = []
        for slot in available_slots[:3]:
            start_dt = datetime.fromisoformat(slot['start_time'])
            end_dt = datetime.fromisoformat(slot['end_time'])
            
            # Use LLM to generate reasoning for this alternative
            reasoning = await self._generate_alternative_reasoning(start_dt)
            
            alternatives.append({
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'preference_score': slot['preference_score'],
                'time_display': f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} {start_dt.tzname()}",
                'reasoning': reasoning
            })
        
        return alternatives
    
    async def _generate_alternative_reasoning(self, start_time: datetime) -> str:
        """Generate reasoning for alternative time suggestion"""
        prompt = f"""
        Briefly explain why {start_time.strftime('%I:%M %p')} on {start_time.strftime('%A')} 
        would be a good alternative meeting time for someone with these preferences: {self.preferences}
        
        Keep it under 30 words and be specific about timing benefits.
        """
        
        try:
            response = await self.llm.generate_async(prompt, max_tokens=60)
            return response.strip()
        except Exception as e:
            print(f"Alternative reasoning generation failed: {e}")
            hour = start_time.hour
            if 9 <= hour < 12:
                return "Morning slot - good for focus and productivity"
            elif 13 <= hour < 17:
                return "Afternoon slot - suitable for collaborative work"
            else:
                return "Available time that fits schedule"