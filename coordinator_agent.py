import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytz
from participant_agent import ParticipantAgent
from negotiator_agent import NegotiatorAgent
from calendar_service import CalendarService
from llm_service import LLMService
from json_validator import JSONValidator
from mock_data import USER_PREFERENCES

class CoordinatorAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMService()
        self.negotiator = NegotiatorAgent(self.llm)
        self.calendar_service = CalendarService()
        self.validator = JSONValidator()
        self.participants = {}
        
    def create_participant_agents(self, attendees_data: List[Dict]) -> List[ParticipantAgent]:
        """Create participant agents from attendee data"""
        agents = []
        
        for attendee in attendees_data:
            email = attendee['email']
            calendar_events = attendee['events']
            
            # Get user preferences (use defaults if not found)
            preferences = USER_PREFERENCES.get(email, {
                'preferred_times': ['morning', 'afternoon'],
                'buffer_minutes': 15,
                'timezone': 'Asia/Kolkata',
                'avoid_lunch': True,
                'seniority_weight': 0.5
            })
            
            # Create participant agent
            agent = ParticipantAgent(
                email=email,
                calendar_data=calendar_events,
                preferences=preferences,
                llm_client=self.llm
            )
            
            agents.append(agent)
            self.participants[email] = agent
        
        return agents
    
    async def schedule_meeting(self, meeting_request: Dict) -> Dict:
        """Main coordination method for scheduling meetings"""
        try:
            # Validate and sanitize input
            validation_result = self.validator.validate_request(meeting_request)
            if not validation_result['valid']:
                return self._format_error_response(
                    f"Validation failed: {'; '.join(validation_result['errors'])}", 
                    meeting_request
                )
            
            # Sanitize request
            sanitized_request = self.validator.sanitize_request(meeting_request)
            
            print(f"Processing meeting request: {sanitized_request['Request_id']}")
            print(f"Email content: {sanitized_request['EmailContent']}")
            
            # Create participant agents
            participants = self.create_participant_agents(sanitized_request['Attendees'])
            print(f"Created {len(participants)} participant agents")
            
            # Use negotiator to find optimal slot
            negotiation_result = await self.negotiator.negotiate_meeting(participants, sanitized_request)
            
            # Format response based on negotiation outcome
            if negotiation_result['success']:
                response = self._format_success_response(negotiation_result, sanitized_request)
                
                # Create calendar event (mock)
                self._create_calendar_event(response)
                
                return response
            else:
                return self._format_failure_response(negotiation_result, sanitized_request)
                
        except Exception as e:
            print(f"Error in schedule_meeting: {e}")
            import traceback
            traceback.print_exc()
            return self._format_error_response(str(e), meeting_request)
    
    def _format_success_response(self, result: Dict, request: Dict) -> Dict:
        """Format successful scheduling response"""
        scheduled_slot = result['scheduled_slot']
        alternatives = result['alternatives_considered']
        summary = result['negotiation_summary']
        
        # Create simplified, clear metadata
        metadata = {
            'scheduling_decision': {
                'chosen_slot': {
                    'time': scheduled_slot['display_time'],
                    'reason': f"Best consensus score ({summary['consensus_score']:.2f}) among {len(alternatives) + 1} options"
                },
                'why_this_time': self._generate_selection_reasoning(scheduled_slot, alternatives, summary),
                'alternatives_evaluated': len(alternatives) + 1
            },
            'alternatives_considered': [
                {
                    'time_slot': alt['time_display'],
                    'score': f"{alt['overall_score']:.2f}"
                } for alt in alternatives
            ],
            'conflict_resolution': {
                'conflicts_found': summary['total_participants'] - summary['conflicts_resolved'],
                'resolution_method': "intelligent_alternative_search",
                'participants_satisfied': f"{summary['conflicts_resolved']}/{summary['total_participants']}"
            },
            'timezone_handling': {
                'primary_timezone': "Asia/Kolkata (IST)",
                'all_times_normalized': True,
                'fairness_considered': True
            }
        }
        
        # Build complete response
        response = {
            'Request_id': request['Request_id'],
            'Subject': request.get('Subject', 'Meeting'),
            'From': request.get('From', ''),
            'EmailContent': request['EmailContent'],
            'Duration_mins': request['Duration_mins'],
            'EventStart': scheduled_slot['start_time'],
            'EventEnd': scheduled_slot['end_time'],
            'Location': request.get('Location', ''),
            'Attendees': request['Attendees'],
            'Datetime': request.get('Datetime', datetime.now().strftime('%d-%m-%YT%H:%M:%S')),
            'MetaData': metadata
        }
        
        # Validate response format
        response_validation = self.validator.validate_response(response)
        if not response_validation['valid']:
            print(f"Response validation warnings: {response_validation['warnings']}")
        
        return response
    
    def _format_failure_response(self, result: Dict, request: Dict) -> Dict:
        """Format failure response"""
        metadata = {
            'scheduling_decision': {
                'chosen_slot': None,
                'reason': f"No suitable slot found: {result['reason']}",
                'alternatives_evaluated': 0
            },
            'conflict_resolution': {
                'conflicts_found': len(request['Attendees']),
                'resolution_method': "exhaustive_search_failed",
                'participants_satisfied': "0/" + str(len(request['Attendees']))
            },
            'timezone_handling': {
                'primary_timezone': "Asia/Kolkata (IST)",
                'all_times_normalized': True,
                'fairness_considered': True
            }
        }
        
        return {
            'Request_id': request['Request_id'],
            'Subject': request.get('Subject', 'Meeting'),
            'From': request.get('From', ''),
            'EmailContent': request['EmailContent'],
            'Duration_mins': request['Duration_mins'],
            'EventStart': None,
            'EventEnd': None,
            'Location': request.get('Location', ''),
            'Attendees': request['Attendees'],
            'Datetime': request.get('Datetime', datetime.now().strftime('%d-%m-%YT%H:%M:%S')),
            'MetaData': metadata,
            'error': 'No available time slot found'
        }
    
    def _format_error_response(self, error: str, request: Dict) -> Dict:
        """Format error response"""
        return {
            'Request_id': request.get('Request_id', 'unknown'),
            'error': f"Scheduling failed: {error}",
            'MetaData': {
                'scheduling_decision': {
                    'chosen_slot': None,
                    'reason': f"System error: {error}",
                    'alternatives_evaluated': 0
                },
                'conflict_resolution': {
                    'conflicts_found': 0,
                    'resolution_method': "failed_due_to_error",
                    'participants_satisfied': "0/0"
                }
            }
        }
    
    def _generate_selection_reasoning(self, chosen_slot: Dict, alternatives: List[Dict], summary: Dict) -> List[str]:
        """Generate human-readable reasoning for slot selection"""
        reasons = []
        
        # Time of day reasoning
        start_time = datetime.fromisoformat(chosen_slot['start_time'])
        hour = start_time.hour
        
        if 9 <= hour < 12:
            reasons.append("Morning slot - optimal for focus and productivity")
        elif 14 <= hour < 17:
            reasons.append("Afternoon slot - good for collaborative discussions")
        else:
            reasons.append("Available slot that works for all participants")
        
        # Conflict resolution reasoning
        conflicts_resolved = summary.get('conflicts_resolved', 0)
        total_participants = summary.get('total_participants', 0)
        
        if conflicts_resolved == total_participants:
            reasons.append("Zero schedule conflicts detected for all participants")
        else:
            reasons.append(f"Successfully resolved conflicts for {conflicts_resolved}/{total_participants} participants")
        
        # Preference reasoning
        if alternatives:
            reasons.append(f"Highest consensus score among {len(alternatives) + 1} possible times")
        
        # Timezone reasoning
        reasons.append("Optimal timing across all participant timezones")
        
        # Selection method reasoning
        if summary.get('selection_reasoning'):
            reasons.append(f"AI recommendation: {summary['selection_reasoning']}")
        
        return reasons
    
    def _create_calendar_event(self, response: Dict):
        """Create calendar event using calendar service"""
        try:
            event_data = {
                'subject': response['Subject'],
                'start_time': response['EventStart'],
                'end_time': response['EventEnd'],
                'location': response.get('Location', ''),
                'attendees': [attendee['email'] for attendee in response['Attendees']]
            }
            
            # Create the event
            created_event = self.calendar_service.create_calendar_event(event_data)
            
            # Send invites
            attendee_emails = [attendee['email'] for attendee in response['Attendees']]
            self.calendar_service.send_calendar_invite(event_data, attendee_emails)
            
            print(f"Calendar event created: {created_event['id']}")
            
        except Exception as e:
            print(f"Failed to create calendar event: {e}")
    
    async def get_system_status(self) -> Dict:
        """Get system status for health checks"""
        try:
            # Check LLM service
            llm_status = self.llm.health_check()
            
            # Check calendar service
            calendar_stats = getattr(self.calendar_service, 'get_stats', lambda: {})()
            
            return {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'llm_service': llm_status,
                    'calendar_service': {'status': 'healthy', **calendar_stats},
                    'validator': {'status': 'healthy'},
                    'negotiator': {'status': 'healthy'}
                },
                'participants_loaded': len(self.participants)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }