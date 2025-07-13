# metadata_framework.py
"""
Business-Friendly Metadata Framework for AMD AI Scheduler
Generates clear, readable summaries for business stakeholders
"""

import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

class BusinessMetadata:
    """Collects and formats agent activities in business-friendly language"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        
        # Track key activities
        self.initial_request = {}
        self.coordinator_activities = []
        self.negotiator_activities = []
        self.participant_responses = {}
        self.available_slots = []
        self.selected_slot = None
        self.final_reasoning = ""
        
    def record_initial_request(self, request_data: Dict):
        """Record the initial meeting request details"""
        attendees = request_data.get('Attendees', [])
        email_content = request_data.get('EmailContent', '')
        
        self.initial_request = {
            'attendee_count': len(attendees),
            'email_content': email_content,
            'request_id': request_data.get('Request_id', 'unknown'),
            'from': request_data.get('From', 'unknown'),
            'subject': request_data.get('Subject', 'Meeting')
        }
    
    def record_coordinator_activity(self, action: str, outcome: str, reasoning: str):
        """Record coordinator agent activities"""
        self.coordinator_activities.append({
            'action': action,
            'outcome': outcome,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_negotiator_activity(self, action: str, outcome: str, reasoning: str):
        """Record negotiator agent activities"""
        self.negotiator_activities.append({
            'action': action,
            'outcome': outcome,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_participant_response(self, participant_id: str, decision: str, reasoning: str, conflict_details: str = None):
        """Record individual participant responses"""
        if participant_id not in self.participant_responses:
            self.participant_responses[participant_id] = []
        
        response = {
            'decision': decision,
            'reasoning': reasoning,
            'conflict_details': conflict_details,
            'timestamp': datetime.now().isoformat()
        }
        self.participant_responses[participant_id].append(response)
    
    def record_available_slots(self, slots: List[Dict], slot_analysis: Dict = None):
        """Record all available time slots with analysis"""
        self.available_slots = slots
        self.slot_analysis = slot_analysis or {}
    
    def record_final_selection(self, selected_slot: Dict, reasoning: str):
        """Record the final selected time slot and reasoning"""
        self.selected_slot = selected_slot
        self.final_reasoning = reasoning
    
    def generate_business_summary(self) -> List[str]:
        """Generate a clean list of summary strings"""
        
        summary_lines = []
        
        # Initial Request Summary
        attendee_count = self.initial_request.get('attendee_count', 0)
        subject = self.initial_request.get('subject', 'Meeting')
        email_content = self.initial_request.get('email_content', '')
        
        # Extract key details from email
        if email_content:
            import re
            # Look for duration
            duration_match = re.search(r'(\d+)\s*(minutes?|mins?|hours?|hrs?)', email_content, re.IGNORECASE)
            if duration_match:
                duration = duration_match.group(1)
                unit = duration_match.group(2)
                if 'hour' in unit.lower():
                    duration_text = f"({duration} hour{'s' if int(duration) > 1 else ''})"
                else:
                    duration_text = f"({duration} minutes)"
            else:
                duration_text = ""
            
            # Look for specific time requests
            time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)', email_content, re.IGNORECASE)
            if time_match:
                requested_time = f"Requested {time_match.group(0).upper()}"
            else:
                requested_time = ""
        else:
            duration_text = ""
            requested_time = ""
        
        initial_summary = f"Initial Request: {subject} for {attendee_count} people"
        if duration_text:
            initial_summary += f" {duration_text}"
        if requested_time:
            initial_summary += f". {requested_time}"
        
        summary_lines.append(initial_summary)
        
        # Coordinator Summary
        if self.coordinator_activities:
            coordinator_summary = self._create_coordinator_narrative()
            summary_lines.append(f'Coordinator Agent: "{coordinator_summary}"')
        
        # Negotiator Summary  
        if self.negotiator_activities:
            negotiator_summary = self._create_negotiator_narrative()
            summary_lines.append(f'Negotiator Agent: "{negotiator_summary}"')
        
        # Participant Responses
        if self.participant_responses:
            summary_lines.append("Participant Responses:")
            for participant_id, responses in self.participant_responses.items():
                if responses:
                    latest_response = responses[-1]
                    participant_summary = self._create_participant_narrative(participant_id, latest_response)
                    summary_lines.append(f"- {participant_summary}")
        
        # Available Options (if multiple slots were considered)
        if len(self.available_slots) > 1:
            summary_lines.append("Available Time Options Considered:")
            for slot in self.available_slots:
                slot_summary = self._create_slot_summary(slot, slot == self.selected_slot)
                summary_lines.append(f"• {slot_summary}")
        
        # Final Decision
        if self.final_reasoning:
            summary_lines.append(f"Final Decision: {self.final_reasoning}")
        elif self.selected_slot:
            time_display = self.selected_slot.get('time_display', 'selected time')
            summary_lines.append(f"Final Decision: Meeting scheduled for {time_display}")
        
        return summary_lines
    
    def _create_coordinator_narrative(self) -> str:
        """Create narrative for coordinator activities"""
        if not self.coordinator_activities:
            return "Handled meeting coordination process."
        
        key_actions = []
        for activity in self.coordinator_activities:
            if 'extract' in activity['action'].lower():
                key_actions.append(f"parsed meeting requirements")
            elif 'create' in activity['action'].lower() or 'agent' in activity['action'].lower():
                key_actions.append(f"set up scheduling assistants for each participant")
            elif 'delegate' in activity['action'].lower() or 'negotiat' in activity['action'].lower():
                key_actions.append(f"coordinated the scheduling negotiation")
            elif 'finali' in activity['action'].lower():
                key_actions.append(f"confirmed the final meeting time")
        
        if len(key_actions) == 0:
            return "Managed the overall scheduling process and coordination between participants."
        elif len(key_actions) == 1:
            return f"Received the meeting request and {key_actions[0]}."
        else:
            return f"Received the meeting request, {', '.join(key_actions[:-1])}, and {key_actions[-1]}."
    
    def _create_negotiator_narrative(self) -> str:
        """Create narrative for negotiator activities"""
        if not self.negotiator_activities:
            return "Handled meeting time negotiation."
        
        key_points = []
        has_conflicts = False
        found_alternatives = False
        
        for activity in self.negotiator_activities:
            if 'conflict' in activity['outcome'].lower() or 'reject' in activity['outcome'].lower():
                has_conflicts = True
                # Extract conflict details
                if 'participants' in activity['outcome']:
                    key_points.append(activity['outcome'])
            elif 'alternative' in activity['action'].lower() or 'found' in activity['outcome'].lower():
                found_alternatives = True
                if 'time' in activity['outcome']:
                    key_points.append(activity['outcome'])
            elif 'selected' in activity['action'].lower() or 'optimal' in activity['outcome'].lower():
                key_points.append(activity['outcome'])
        
        if not key_points:
            return "Analyzed participant availability and found a suitable meeting time."
        
        # Build narrative
        narrative_parts = []
        if has_conflicts:
            narrative_parts.append("Found scheduling conflicts")
        if found_alternatives:
            narrative_parts.append("searched for alternative times")
        
        # Add key outcomes
        for point in key_points[:2]:  # Keep it concise
            narrative_parts.append(point.lower())
        
        return "Checked availability and " + ", then ".join(narrative_parts) + "."
    
    def _create_participant_narrative(self, participant_id: str, response: Dict) -> str:
        """Create narrative for participant response"""
        name = participant_id.split('@')[0].title()
        decision = response['decision']
        reasoning = response['reasoning']
        conflict = response.get('conflict_details')
        
        # Convert technical decisions to business language
        if decision == 'ACCEPT':
            decision_text = "Works perfectly"
        elif decision == 'CONDITIONAL_ACCEPT':
            decision_text = "Can make it work"
        elif decision == 'REJECT':
            decision_text = "Can't attend"
        else:
            decision_text = decision
        
        # Build response
        if conflict:
            return f"{name}: \"{decision_text} - {conflict}. {reasoning}\""
        else:
            return f"{name}: \"{decision_text}. {reasoning}\""
    
    def _create_slot_summary(self, slot: Dict, is_selected: bool = False) -> str:
        """Create summary for each available time slot"""
        time_display = slot.get('time_display', slot.get('time', 'Unknown time'))
        attendee_count = slot.get('attendee_count', slot.get('available_count', 0))
        total_participants = slot.get('total_participants', 0)
        conflicts = slot.get('conflicts', [])
        
        # Format the line
        status = "✓ SELECTED" if is_selected else ""
        availability_text = f"{attendee_count} people available" if total_participants > 0 else "available"
        
        conflict_text = ""
        if conflicts:
            conflict_names = [c.split('@')[0].title() if '@' in c else c for c in conflicts[:2]]
            if len(conflicts) > 2:
                conflict_text = f"({', '.join(conflict_names)}, +{len(conflicts)-2} others busy)"
            else:
                conflict_text = f"({', '.join(conflict_names)} busy)"
        
        line = f"• {time_display} - {availability_text}"
        if conflict_text:
            line += f" {conflict_text}"
        if status:
            line += f" {status}"
        
        return line
    
    def _create_final_decision_narrative(self) -> str:
        """Create narrative for final decision with reasoning"""
        if not self.final_reasoning:
            if self.selected_slot:
                return f"Meeting scheduled for {self.selected_slot.get('time_display', 'selected time')}."
            else:
                return "No suitable meeting time could be found that works for all participants."
        
        return self.final_reasoning

# Global instance
_business_metadata = None

def get_business_metadata() -> BusinessMetadata:
    """Get or create the global business metadata collector"""
    global _business_metadata
    if _business_metadata is None:
        _business_metadata = BusinessMetadata()
    return _business_metadata

def reset_business_metadata():
    """Reset for new session"""
    global _business_metadata
    _business_metadata = BusinessMetadata()

# Helper functions for easy integration
def record_request(request_data: Dict):
    """Record initial request"""
    get_business_metadata().record_initial_request(request_data)

def record_coordinator(action: str, outcome: str, reasoning: str):
    """Record coordinator activity"""
    get_business_metadata().record_coordinator_activity(action, outcome, reasoning)

def record_negotiator(action: str, outcome: str, reasoning: str):
    """Record negotiator activity"""
    get_business_metadata().record_negotiator_activity(action, outcome, reasoning)

def record_participant(participant_id: str, decision: str, reasoning: str, conflict_details: str = None):
    """Record participant response"""
    get_business_metadata().record_participant_response(participant_id, decision, reasoning, conflict_details)

def record_slots(slots: List[Dict], analysis: Dict = None):
    """Record available slots"""
    get_business_metadata().record_available_slots(slots, analysis)

def record_selection(selected_slot: Dict, reasoning: str):
    """Record final selection"""
    get_business_metadata().record_final_selection(selected_slot, reasoning)