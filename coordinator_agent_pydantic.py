import asyncio
from typing import List, Dict, Any
from datetime import datetime
import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import (
    MeetingRequest, SchedulingResponse, Attendee, CalendarEvent, 
    UserPreferences, NegotiationResult
)
from email_parser_agent import EmailParserAgent
from participant_agent_pydantic import ParticipantAgent
from negotiator_agent_pydantic import NegotiatorAgent
from calendar_service import CalendarService
from config import get_user_preferences, get_timezone_for_email
from tools import get_current_date, convert_time_across_timezones

class CoordinatorAgent:
    def __init__(self, base_url: str = "http://localhost:3000/v1"):
        self.base_url = base_url
        
        # Create provider for local vLLM DeepSeek server
        provider = OpenAIProvider(
            base_url=base_url,
            api_key="dummy"
        )
        
        self.model = OpenAIModel("deepseek", provider=provider)
        
        # Initialize sub-agents with DeepSeek
        self.email_parser = EmailParserAgent(base_url)
        self.negotiator = NegotiatorAgent(base_url)
        self.calendar_service = CalendarService()
        
        # Narrative generation agent
        self.narrative_agent = Agent(
            model=self.model,
            result_type=str,
            tools=[get_current_date, convert_time_across_timezones],
            system_prompt="""You are a expert meeting coordinator that creates detailed scheduling narratives.

Your role is to generate comprehensive, business-friendly narratives that explain:
1. The scheduling process and challenges
2. Agent reasoning and decision-making
3. Timezone considerations and fairness
4. Participant responses and negotiations
5. Final decision rationale

NARRATIVE STYLE:
- Professional and business-oriented language
- Clear explanation of AI reasoning
- Timezone details and time conversions
- No technical scores or metrics
- Focus on practical scheduling considerations
- Explain trade-offs and compromises made

The narrative should read like a sophisticated AI assistant explaining its scheduling intelligence to business users."""
        )
    
    async def schedule_meeting(self, request_data: Dict[str, Any]) -> SchedulingResponse:
        """Main coordination method for scheduling meetings."""
        try:
            print(f"Processing request: {request_data.get('Request_id', 'unknown')}")
            
            # Step 1: Parse email content to extract meeting details
            email_content = request_data.get('EmailContent', '')
            parsed_email = await self.email_parser.parse_email(email_content)
            print(f"Parsed email - Date: {parsed_email.suggested_date}, Duration: {parsed_email.duration_minutes}min")
            
            # Step 2: Transform input format and gather calendar data
            meeting_request = await self._transform_input_format(request_data, parsed_email)
            
            # Step 3: Create participant agents with preferences and calendar data
            participants = await self._create_participant_agents(meeting_request.Attendees)
            print(f"Created {len(participants)} participant agents")
            
            # Step 4: Negotiate optimal meeting time
            negotiation_result = await self.negotiator.negotiate_meeting(participants, meeting_request)
            
            # Step 5: Generate response based on success/failure
            if negotiation_result.success:
                response = await self._format_success_response(
                    negotiation_result, request_data, meeting_request
                )
                print(f"Success: Scheduled {response.EventStart} to {response.EventEnd}")
                return response
            else:
                response = await self._format_failure_response(
                    negotiation_result, request_data, meeting_request
                )
                print(f"Failed: {negotiation_result.reason}")
                return response
                
        except Exception as e:
            print(f"Coordination error: {e}")
            import traceback
            traceback.print_exc()
            return await self._format_error_response(str(e), request_data)
    
    async def _transform_input_format(self, request_data: Dict, parsed_email) -> MeetingRequest:
        """Transform input format to internal MeetingRequest model."""
        from_email = request_data.get('From', '')
        attendees_input = request_data.get('Attendees', [])
        
        # Handle different input formats
        attendee_emails = []
        if attendees_input and isinstance(attendees_input[0], dict):
            if 'events' in attendees_input[0]:
                # New format with events already provided
                attendees = [
                    Attendee(
                        email=att['email'],
                        events=[CalendarEvent(**event) for event in att['events']]
                    )
                    for att in attendees_input
                ]
                if from_email and from_email not in [att.email for att in attendees]:
                    from_events = self.calendar_service.retrieve_calendar_events(
                        from_email, 
                        f'{parsed_email.suggested_date}T00:00:00+05:30',
                        f'{parsed_email.suggested_date}T23:59:59+05:30'
                    )
                    attendees.append(Attendee(
                        email=from_email,
                        events=[CalendarEvent(**event) for event in from_events]
                    ))
            else:
                # Original format with just emails
                attendee_emails = [att.get('email') for att in attendees_input]
                if from_email and from_email not in attendee_emails:
                    attendee_emails.append(from_email)
                
                # Fetch calendar data for each attendee
                attendees = []
                for email in attendee_emails:
                    calendar_events = self.calendar_service.retrieve_calendar_events(
                        email,
                        f'{parsed_email.suggested_date}T00:00:00+05:30',
                        f'{parsed_email.suggested_date}T23:59:59+05:30'
                    )
                    attendees.append(Attendee(
                        email=email,
                        events=[CalendarEvent(**event) for event in calendar_events]
                    ))
        
        return MeetingRequest(
            Request_id=request_data['Request_id'],
            Datetime=request_data['Datetime'],
            Location=request_data['Location'],
            From=request_data['From'],
            Attendees=attendees,
            Subject=request_data['Subject'],
            EmailContent=request_data['EmailContent'],
            Duration_mins=str(parsed_email.duration_minutes),
            target_date=parsed_email.suggested_date
        )
    
    async def _create_participant_agents(self, attendees: List[Attendee]) -> List[ParticipantAgent]:
        """Create participant agents with preferences and calendar data."""
        agents = []
        
        for attendee in attendees:
            # Get user preferences based on email domain
            preferences_dict = get_user_preferences(attendee.email)
            preferences = UserPreferences(**preferences_dict)
            
            # Create participant agent with DeepSeek
            agent = ParticipantAgent(
                email=attendee.email,
                calendar_events=attendee.events,
                preferences=preferences,
                base_url=self.base_url
            )
            
            agents.append(agent)
        
        return agents
    
    async def _format_success_response(self, 
                                     result: NegotiationResult, 
                                     original_request: Dict, 
                                     meeting_request: MeetingRequest) -> SchedulingResponse:
        """Format successful scheduling response."""
        scheduled_slot = result.scheduled_slot
        
        # Create new meeting event
        new_event = CalendarEvent(
            StartTime=scheduled_slot.start_time,
            EndTime=scheduled_slot.end_time,
            NumAttendees=len(meeting_request.Attendees),
            Attendees=[att.email for att in meeting_request.Attendees],
            Summary=original_request.get('Subject', 'Meeting')
        )
        
        # Add new event to all attendees' calendars
        updated_attendees = []
        for attendee in meeting_request.Attendees:
            updated_events = attendee.events + [new_event]
            updated_attendees.append(Attendee(
                email=attendee.email,
                events=updated_events
            ))
        
        # Generate narrative
        narrative = await self._generate_scheduling_narrative(
            original_request, meeting_request, result, updated_attendees
        )
        
        return SchedulingResponse(
            Request_id=original_request['Request_id'],
            Datetime=original_request['Datetime'],
            Location=original_request['Location'],
            From=original_request['From'],
            Attendees=updated_attendees,
            Subject=original_request['Subject'],
            EmailContent=original_request['EmailContent'],
            EventStart=scheduled_slot.start_time,
            EventEnd=scheduled_slot.end_time,
            Duration_mins=meeting_request.Duration_mins,
            MetaData={'scheduling_narrative': narrative}
        )
    
    async def _format_failure_response(self, 
                                     result: NegotiationResult,
                                     original_request: Dict,
                                     meeting_request: MeetingRequest) -> SchedulingResponse:
        """Format failure response."""
        narrative = await self._generate_failure_narrative(
            original_request, meeting_request, result
        )
        
        return SchedulingResponse(
            Request_id=original_request['Request_id'],
            Datetime=original_request['Datetime'],
            Location=original_request['Location'],
            From=original_request['From'],
            Attendees=meeting_request.Attendees,
            Subject=original_request['Subject'],
            EmailContent=original_request['EmailContent'],
            EventStart=None,
            EventEnd=None,
            Duration_mins=meeting_request.Duration_mins,
            MetaData={'scheduling_narrative': narrative},
            error='No available time slot found'
        )
    
    async def _format_error_response(self, error: str, original_request: Dict) -> SchedulingResponse:
        """Format error response."""
        error_narrative = [
            "Meeting Scheduling Summary",
            f"Initial Request: Failed to process meeting request {original_request.get('Request_id', 'unknown')}.",
            f"System Error: {error}",
            "The scheduling system encountered an unexpected error and could not complete the meeting coordination process."
        ]
        
        return SchedulingResponse(
            Request_id=original_request.get('Request_id', 'unknown'),
            Datetime=original_request.get('Datetime', ''),
            Location=original_request.get('Location', ''),
            From=original_request.get('From', ''),
            Attendees=[],
            Subject=original_request.get('Subject', ''),
            EmailContent=original_request.get('EmailContent', ''),
            EventStart=None,
            EventEnd=None,
            Duration_mins='30',
            MetaData={'scheduling_narrative': error_narrative},
            error=f"Scheduling failed: {error}"
        )
    
    async def _generate_scheduling_narrative(self, 
                                           original_request: Dict,
                                           meeting_request: MeetingRequest,
                                           result: NegotiationResult,
                                           attendees: List[Attendee]) -> List[str]:
        """Generate detailed scheduling narrative using AI agent."""
        try:
            # Gather timezone information
            participant_timezones = {}
            for attendee in meeting_request.Attendees:
                timezone = get_timezone_for_email(attendee.email)
                participant_timezones[attendee.email] = timezone
            
            # Convert meeting time to all timezones
            timezone_times = convert_time_across_timezones(
                result.scheduled_slot.start_time,
                list(set(participant_timezones.values()))
            )
            
            # Prepare context for narrative generation
            context = f"""
            Generate a detailed scheduling narrative for this successful meeting coordination:
            
            MEETING DETAILS:
            - Subject: {original_request.get('Subject', 'Meeting')}
            - Requested by: {original_request.get('From', 'unknown')}
            - Participants: {', '.join([att.email for att in meeting_request.Attendees])}
            - Email content: '{original_request.get('EmailContent', '')}'
            - Duration: {meeting_request.Duration_mins} minutes
            - Target date: {meeting_request.target_date}
            
            TIMEZONE DETAILS:
            - Participant timezones: {participant_timezones}
            - Meeting time across zones: {timezone_times}
            
            NEGOTIATION RESULTS:
            - Selected time: {result.scheduled_slot.start_time}
            - Consensus score: {result.consensus_score}
            - Alternatives considered: {len(result.alternatives_considered)}
            - Selection reasoning: {result.selection_reasoning}
            
            PARTICIPANT RESPONSES:
            {[f"- {eval.participant}: {eval.decision} ({eval.llm_reasoning})" for eval in result.evaluations]}
            
            Create a narrative with these sections:
            1. Meeting Scheduling Summary
            2. Initial Request analysis
            3. Coordinator Agent reasoning
            4. Negotiator Agent strategy and timezone analysis
            5. Participant Responses with timezone context
            6. Time Slot Analysis (if alternatives were considered)
            7. Final Decision with timezone fairness explanation
            8. Meeting confirmation
            
            Format as a list of strings, one per paragraph. No empty strings between sections.
            Focus on business value and intelligent scheduling decisions.
            """
            
            result = await self.narrative_agent.run(context)
            
            # Parse the narrative into list format
            narrative_text = str(result.data) if hasattr(result, 'data') else str(result)
            
            # Split into logical paragraphs and clean up
            lines = narrative_text.split('\n')
            narrative_list = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('```'):
                    narrative_list.append(line)
            
            return narrative_list
            
        except Exception as e:
            print(f"Narrative generation failed: {e}")
            # Return basic narrative
            return [
                "Meeting Scheduling Summary",
                f"Successfully scheduled {original_request.get('Subject', 'Meeting')} for {len(meeting_request.Attendees)} participants.",
                f"Selected time: {result.scheduled_slot.time_display}",
                f"Meeting confirmed across {len(set(participant_timezones.values()))} timezones."
            ]
    
    async def _generate_failure_narrative(self,
                                        original_request: Dict,
                                        meeting_request: MeetingRequest,
                                        result: NegotiationResult) -> List[str]:
        """Generate failure narrative."""
        participant_timezones = {}
        for attendee in meeting_request.Attendees:
            timezone = get_timezone_for_email(attendee.email)
            participant_timezones[attendee.email] = timezone
        
        return [
            "Meeting Scheduling Summary",
            f"Initial Request: {original_request.get('Subject', 'Meeting')} requested by {original_request.get('From', 'unknown')}. Participants: {', '.join([att.email for att in meeting_request.Attendees])} across timezones: {', '.join(set(participant_timezones.values()))}. Duration: {meeting_request.Duration_mins} minutes. Target date: {meeting_request.target_date}.",
            f"Coordinator Agent: 'Received scheduling request for {len(meeting_request.Attendees)}-person meeting across multiple timezones. Created participant agents and analyzed calendar constraints for each timezone.'",
            "Negotiator Agent: 'Attempted to find suitable meeting times across all timezones but encountered significant conflicts. Evaluated all possible business hour combinations but no viable time slots found that satisfy minimum attendance requirements given timezone and calendar constraints.'",
            f"Failure Reason: {result.reason}",
            "Unable to schedule meeting due to irreconcilable timezone and calendar conflicts. Consider expanding the date range, reducing meeting duration, making attendance optional for some participants, or scheduling separate regional meetings."
        ]