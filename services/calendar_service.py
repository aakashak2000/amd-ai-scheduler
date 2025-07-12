"""
Google Calendar integration service
Uses provided Google Calendar examples and authentication
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from utils.config import Config

class CalendarService:
    """Service for Google Calendar integration"""
    
    def __init__(self):
        # For hackathon, we'll use mock data based on provided examples
        self.mock_calendar_data = self._load_mock_calendar_data()
    
    def _load_mock_calendar_data(self) -> Dict[str, List[Dict]]:
        """Load mock calendar data based on provided examples"""
        return {
            "userone.amd@gmail.com": [
                {
                    "StartTime": "2025-07-17T00:00:00+05:30",
                    "EndTime": "2025-07-17T09:00:00+05:30",
                    "NumAttendees": 1,
                    "Attendees": ["SELF"],
                    "Summary": "Off Hours"
                },
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": ["userone.amd@gmail.com", "ajithsirra@gmail.com", "usertwo.amd@gmail.com"],
                    "Summary": "Team Meet"
                },
                {
                    "StartTime": "2025-07-17T18:00:00+05:30",
                    "EndTime": "2025-07-18T00:00:00+05:30",
                    "NumAttendees": 1,
                    "Attendees": ["SELF"],
                    "Summary": "Off Hours"
                }
            ],
            "usertwo.amd@gmail.com": [
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"],
                    "Summary": "Team Meet"
                },
                {
                    "StartTime": "2025-07-17T14:00:00+05:30",
                    "EndTime": "2025-07-17T15:00:00+05:30",
                    "NumAttendees": 2,
                    "Attendees": ["usertwo.amd@gmail.com", "client@company.com"],
                    "Summary": "Client Call"
                }
            ],
            "userthree.amd@gmail.com": [
                {
                    "StartTime": "2025-07-17T10:00:00+05:30",
                    "EndTime": "2025-07-17T10:30:00+05:30",
                    "NumAttendees": 3,
                    "Attendees": ["userone.amd@gmail.com", "usertwo.amd@gmail.com", "userthree.amd@gmail.com"],
                    "Summary": "Team Meet"
                },
                {
                    "StartTime": "2025-07-17T13:00:00+05:30",
                    "EndTime": "2025-07-17T14:00:00+05:30",
                    "NumAttendees": 1,
                    "Attendees": ["SELF"],
                    "Summary": "Lunch with Customers"
                }
            ]
        }
    
    async def get_events(self, user_email: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get calendar events for a user within date range"""
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Get mock data for user
        user_events = self.mock_calendar_data.get(user_email, [])
        
        # Filter events within date range (simplified)
        filtered_events = []
        for event in user_events:
            event_start = datetime.fromisoformat(event["StartTime"].replace('+05:30', ''))
            range_start = datetime.fromisoformat(start_date.replace('+05:30', ''))
            range_end = datetime.fromisoformat(end_date.replace('+05:30', ''))
            
            if range_start <= event_start <= range_end:
                filtered_events.append(event)
        
        return filtered_events
    
    async def fetch_multiple_calendars(self, user_emails: List[str], start_date: str, end_date: str) -> Dict[str, List[Dict]]:
        """Fetch calendars for multiple users in parallel - GPU showcase"""
        
        print(f"📅 Fetching calendars for {len(user_emails)} users in parallel")
        
        # Create parallel tasks
        tasks = [
            self.get_events(email, start_date, end_date)
            for email in user_emails
        ]
        
        # Execute in parallel
        calendar_results = await asyncio.gather(*tasks)
        
        # Combine results
        result = {}
        for email, events in zip(user_emails, calendar_results):
            result[email] = events
        
        print(f"✅ Retrieved {sum(len(events) for events in result.values())} total events")
        
        return result
    
    def find_available_slots(self, events: List[Dict], duration_minutes: int, 
                           start_date: str, end_date: str) -> List[Dict[str, str]]:
        """Find available time slots between existing events"""
        
        available_slots = []
        
        # Convert to datetime objects
        start_dt = datetime.fromisoformat(start_date.replace('+05:30', ''))
        end_dt = datetime.fromisoformat(end_date.replace('+05:30', ''))
        
        # Start from business hours (9 AM)
        current_time = start_dt.replace(hour=9, minute=0, second=0, microsecond=0)
        
        while current_time < end_dt:
            slot_end = current_time + timedelta(minutes=duration_minutes)
            
            # Check if this slot conflicts with any existing event
            has_conflict = False
            for event in events:
                event_start = datetime.fromisoformat(event["StartTime"].replace('+05:30', ''))
                event_end = datetime.fromisoformat(event["EndTime"].replace('+05:30', ''))
                
                # Check for overlap
                if not (slot_end <= event_start or current_time >= event_end):
                    has_conflict = True
                    break
            
            # Check if within business hours
            if (current_time.hour >= Config.BUSINESS_HOURS_START and 
                slot_end.hour <= Config.BUSINESS_HOURS_END and
                current_time.weekday() < 5 and  # Monday to Friday
                not has_conflict):
                
                available_slots.append({
                    "start": current_time.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                    "end": slot_end.strftime("%Y-%m-%dT%H:%M:%S+05:30")
                })
            
            # Move to next 30-minute slot
            current_time += timedelta(minutes=30)
        
        return available_slots
    
    def check_conflict(self, proposed_start: str, proposed_end: str, existing_events: List[Dict]) -> tuple[bool, List[str]]:
        """Check if proposed time conflicts with existing events"""
        
        conflicts = []
        
        prop_start = datetime.fromisoformat(proposed_start.replace('+05:30', ''))
        prop_end = datetime.fromisoformat(proposed_end.replace('+05:30', ''))
        
        for event in existing_events:
            event_start = datetime.fromisoformat(event["StartTime"].replace('+05:30', ''))
            event_end = datetime.fromisoformat(event["EndTime"].replace('+05:30', ''))
            
            # Check for overlap
            if not (prop_end <= event_start or prop_start >= event_end):
                conflicts.append(event["Summary"])
        
        return len(conflicts) > 0, conflicts
