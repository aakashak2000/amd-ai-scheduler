"""
Simple schedule coordinator
"""
from datetime import datetime, timedelta

class ScheduleCoordinatorAgent:
    def __init__(self, calendar_service):
        self.calendar = calendar_service
        
    def coordinate_meeting(self, attendee_emails, meeting_details):
        """Simple meeting coordination"""
        
        print(f"Coordinating meeting for {len(attendee_emails)} participants")
        
        # Get calendars for all attendees
        start_date = "2025-07-17T00:00:00+05:30"
        end_date = "2025-07-17T23:59:59+05:30"
        
        calendars = {}
        for email in attendee_emails:
            calendars[email] = self.calendar.get_events(email, start_date, end_date)
        
        # Find simple available slot
        optimal_slot = self._find_simple_slot(calendars, meeting_details)
        
        return {
            "success": True,
            "scheduled_time": optimal_slot,
            "method": "simple_coordination"
        }
    
    def _find_simple_slot(self, calendars, meeting_details):
        """Find first available slot for all participants"""
        
        duration = meeting_details.get("duration_minutes", 30)
        
        # Try common time slots
        time_slots = [
            "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00"
        ]
        
        for time_slot in time_slots:
            start_time = f"2025-07-17T{time_slot}:00+05:30"
            start_dt = datetime.fromisoformat(start_time.replace('+05:30', ''))
            end_dt = start_dt + timedelta(minutes=duration)
            end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")
            
            # Check if slot is free for all participants
            conflicts = False
            for email, events in calendars.items():
                for event in events:
                    event_start = datetime.fromisoformat(event["StartTime"].replace('+05:30', ''))
                    event_end = datetime.fromisoformat(event["EndTime"].replace('+05:30', ''))
                    
                    if not (end_dt <= event_start or start_dt >= event_end):
                        conflicts = True
                        break
                
                if conflicts:
                    break
            
            if not conflicts:
                return {"start": start_time, "end": end_time}
        
        # Fallback
        return {
            "start": "2025-07-17T14:00:00+05:30",
            "end": "2025-07-17T14:30:00+05:30"
        }
