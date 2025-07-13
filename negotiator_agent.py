import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import Counter
from llm_service import LLMService
from email_parser import EmailParser
import pytz
from metadata_framework import record_negotiator, record_slots, record_selection


class NegotiatorAgent:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMService()
        self.email_parser = EmailParser(llm_client)
        self.negotiation_history = []
        self.default_timezone = pytz.timezone('Asia/Kolkata')
    
    async def negotiate_meeting(self, participants: List, meeting_request: Dict) -> Dict:
        """Advanced negotiation with business-friendly slot analysis"""
        
        duration_mins = int(meeting_request.get('Duration_mins', 30))
        email_content = meeting_request.get('EmailContent', '')
        
        # Parse email content for user preferences
        parsed_email = self.email_parser.parse_email(email_content)
        target_date = parsed_email.get('suggested_date', self._get_default_date())
        requested_time = self._build_requested_time(parsed_email, target_date, duration_mins)
        
        print(f"Negotiating meeting for {len(participants)} participants")
        print(f"Target date: {target_date}, Duration: {duration_mins} minutes")
        
        # Check if user requested specific time
        if requested_time and requested_time.get('start'):
            requested_time_display = datetime.fromisoformat(requested_time['start']).strftime('%I:%M %p')
            
            record_negotiator(
                action="evaluate user-requested time",
                outcome=f"checking {requested_time_display} as specifically requested",
                reasoning=f"User specifically asked for {requested_time_display}, so checking if this works for everyone first"
            )
            
            print("Evaluating specifically requested time...")
            initial_result = await self._evaluate_specific_time(participants, requested_time, duration_mins)
            
            if initial_result['success']:
                consensus_score = initial_result['consensus_score']
                
                record_negotiator(
                    action="confirm requested time",
                    outcome=f"success - {requested_time_display} works for everyone",
                    reasoning=f"Perfect outcome - user's preferred time has no conflicts and good participant agreement"
                )
                
                # Record the selection
                record_selection(
                    selected_slot={
                        'time_display': requested_time_display,
                        'start_time': requested_time['start'],
                        'end_time': requested_time['end']
                    },
                    reasoning=f"Selected {requested_time_display} because it was specifically requested by the user and works perfectly for all {len(participants)} participants. No conflicts found and achieved good consensus among the team."
                )
                
                print("Requested time works for everyone!")
                return self._create_success_response(initial_result, meeting_request, [])
                
            else:
                conflicts = initial_result['conflicts']
                conflict_participants = [c['participant'].split('@')[0].title() for c in conflicts]
                
                record_negotiator(
                    action="analyze requested time conflicts",
                    outcome=f"conflicts found with {len(conflicts)} participants: {', '.join(conflict_participants)}",
                    reasoning=f"User's preferred {requested_time_display} doesn't work because of existing commitments"
                )
                
                print(f"Requested time has {len(conflicts)} conflicts")
        
        # Find alternative slots
        record_negotiator(
            action="search for alternative times",
            outcome="analyzing all possible meeting slots",
            reasoning="Since requested time has conflicts, need to find alternative times that work better for everyone"
        )
        
        print("Finding alternative time slots...")
        alternative_slots = await self._find_alternative_slots(participants, target_date, duration_mins)
        
        if not alternative_slots:
            record_negotiator(
                action="complete comprehensive search",
                outcome="no viable time slots found",
                reasoning="Exhaustive analysis of the target date found no times where all participants are available"
            )
            
            print("No alternative slots found")
            return self._create_failure_response(meeting_request, "No available slots found")
        
        # Analyze each slot for business summary
        business_slots = []
        for slot in alternative_slots:
            slot_time = datetime.fromisoformat(slot['start_time']).strftime('%I:%M %p')
            attendee_count = len(participants)  # Assume all can attend if in alternatives
            
            # Create business-friendly slot info
            business_slot = {
                'time_display': slot_time,
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'attendee_count': attendee_count,
                'total_participants': len(participants),
                'overall_score': slot.get('overall_score', 0),
                'conflicts': []  # Will be populated if needed
            }
            business_slots.append(business_slot)
        
        # Record all available options
        record_slots(business_slots)
        
        record_negotiator(
            action="analyze available options",
            outcome=f"found {len(alternative_slots)} potential meeting times",
            reasoning=f"Comprehensive analysis identified multiple options, now selecting the best one based on participant preferences"
        )
        
        # Select the best option
        best_slot = await self._negotiate_best_slot(participants, alternative_slots)
        
        if not best_slot:
            record_negotiator(
                action="attempt consensus building",
                outcome="could not reach agreement on any option",
                reasoning="Multiple time slots available but unable to achieve acceptable consensus among participants"
            )
            
            return self._create_failure_response(meeting_request, "Could not find acceptable compromise")
        
        selected_time = best_slot['slot']['time_display']
        consensus_score = best_slot['consensus_score']
        
        # Create detailed reasoning for selection
        selection_reasoning = self._create_selection_reasoning(best_slot, alternative_slots, participants)
        
        record_negotiator(
            action="select optimal time",
            outcome=f"chose {selected_time} as best option",
            reasoning=f"After analyzing all options, {selected_time} provides the best balance of participant availability and preferences"
        )
        
        # Record the final selection with detailed reasoning
        record_selection(
            selected_slot={
                'time_display': selected_time,
                'start_time': best_slot['slot']['start_time'],
                'end_time': best_slot['slot']['end_time']
            },
            reasoning=selection_reasoning
        )
        
        print(f"Selected best slot: {selected_time}")
        return self._create_success_response(best_slot, meeting_request, alternative_slots)
    
    def _create_selection_reasoning(self, best_slot: Dict, all_slots: List[Dict], participants: List) -> str:
        """Create detailed business reasoning for slot selection"""
        selected_time = best_slot['slot']['time_display']
        consensus_score = best_slot['consensus_score']
        
        # Count how many alternatives were considered
        total_options = len(all_slots)
        
        # Analyze why this slot was best
        reasoning_parts = []
        
        # Primary reason - availability
        reasoning_parts.append(f"Selected {selected_time} after analyzing {total_options} possible times")
        
        # Consensus quality
        if consensus_score >= 0.8:
            reasoning_parts.append("it achieved excellent agreement among all participants")
        elif consensus_score >= 0.6:
            reasoning_parts.append("it provided good balance of everyone's preferences")
        else:
            reasoning_parts.append("it was the best available compromise")
        
        # Additional factors
        hour = datetime.fromisoformat(best_slot['slot']['start_time']).hour
        if 9 <= hour <= 11:
            reasoning_parts.append("morning timing works well for focus and energy levels")
        elif 13 <= hour <= 15:
            reasoning_parts.append("early afternoon timing avoids lunch conflicts")
        
        # Participant considerations
        reasoning_parts.append(f"ensures all {len(participants)} participants can attend")
        
        return ". ".join(reasoning_parts).capitalize() + "."



    
    def _build_requested_time(self, parsed_email: Dict, target_date: str, duration_mins: int) -> Dict:
        """Build requested time object from parsed email"""
        suggested_time = parsed_email.get('suggested_time')
        if not suggested_time:
            return None
        
        try:
            # Parse date and time
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            time_parts = suggested_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            # Create datetime objects
            start_dt = date_obj.replace(hour=hour, minute=minute)
            end_dt = start_dt + timedelta(minutes=duration_mins)
            
            # Add timezone (IST)
            start_dt = self.default_timezone.localize(start_dt)
            end_dt = self.default_timezone.localize(end_dt)
            
            return {
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat()
            }
        except Exception as e:
            print(f"Error building requested time: {e}")
            return None
    
    async def _evaluate_specific_time(self, participants: List, requested_time: Dict, duration_mins: int) -> Dict:
        """Evaluate if all participants can meet at requested time"""
        evaluations = []
        conflicts = []
        
        # Collect evaluations from all participants
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal({
                    'start_time': requested_time['start'],
                    'end_time': requested_time['end']
                })
                evaluations.append(evaluation)
                
                if evaluation['decision'] == 'REJECT':
                    conflicts.append({
                        'participant': participant.email,
                        'reason': evaluation['reason'],
                        'timezone': evaluation.get('timezone', 'Asia/Kolkata')  # Default timezone
                    })
            except Exception as e:
                print(f"Error evaluating proposal for {participant.email}: {e}")
                # Add default rejection for failed evaluation
                evaluations.append({
                    'decision': 'REJECT',
                    'reason': 'evaluation_failed',
                    'preference_score': 0,
                    'participant': participant.email,
                    'timezone': 'Asia/Kolkata'
                })
                conflicts.append({
                    'participant': participant.email,
                    'reason': 'evaluation_failed',
                    'timezone': 'Asia/Kolkata'
                })
        
        success = len(conflicts) == 0
        consensus_score = sum(e.get('preference_score', 0) for e in evaluations) / len(evaluations) if evaluations else 0
        
        return {
            'success': success,
            'slot': {
                'start_time': requested_time['start'],
                'end_time': requested_time['end'],
                'time_display': self._format_time_display(requested_time['start'])
            },
            'evaluations': evaluations,
            'conflicts': conflicts,
            'consensus_score': consensus_score
        }
    
    async def _find_alternative_slots(self, participants: List, target_date: str, duration_mins: int) -> List[Dict]:
        """Find all possible alternative slots"""
        all_available_slots = {}
        
        # Collect available slots from each participant
        for participant in participants:
            try:
                slots = participant.find_available_slots(target_date, duration_mins)
                all_available_slots[participant.email] = slots
                print(f"  {participant.email}: {len(slots)} available slots")
            except Exception as e:
                print(f"Error finding slots for {participant.email}: {e}")
                all_available_slots[participant.email] = []
        
        # Find common slots across all participants
        common_slots = self._find_common_time_slots(all_available_slots, duration_mins)
        print(f"Found {len(common_slots)} common time slots")
        
        # Score and rank slots
        scored_slots = []
        for slot in common_slots:
            try:
                consensus_score = await self._calculate_consensus_score(participants, slot)
                timezone_fairness = self._calculate_timezone_fairness(participants, slot)
                
                scored_slots.append({
                    'start_time': slot['start_time'],
                    'end_time': slot['end_time'],
                    'consensus_score': consensus_score,
                    'timezone_fairness': timezone_fairness,
                    'overall_score': consensus_score * 0.7 + timezone_fairness * 0.3,
                    'time_display': self._format_time_display(slot['start_time'])
                })
            except Exception as e:
                print(f"Error scoring slot {slot}: {e}")
                continue
        
        # Return top 10 alternatives sorted by overall score
        return sorted(scored_slots, key=lambda x: x['overall_score'], reverse=True)[:10]
    
    def _find_common_time_slots(self, all_slots: Dict, duration_mins: int) -> List[Dict]:
        """Find overlapping time slots across all participants"""
        if not all_slots:
            return []
        
        # Get all unique time slots
        all_time_slots = set()
        for participant_slots in all_slots.values():
            for slot in participant_slots:
                slot_key = (slot['start_time'], slot['end_time'])
                all_time_slots.add(slot_key)
        
        # Filter to slots that work for ALL participants
        common_slots = []
        for start_time, end_time in all_time_slots:
            works_for_all = True
            
            # Check if this time slot exists in every participant's available slots
            for participant_email, participant_slots in all_slots.items():
                participant_has_slot = any(
                    slot['start_time'] == start_time and slot['end_time'] == end_time
                    for slot in participant_slots
                )
                
                if not participant_has_slot:
                    works_for_all = False
                    break
            
            if works_for_all:
                common_slots.append({
                    'start_time': start_time,
                    'end_time': end_time
                })
        
        return common_slots
    
    async def _calculate_consensus_score(self, participants: List, slot: Dict) -> float:
        """Calculate how well this slot works for all participants"""
        total_score = 0
        valid_participants = 0
        
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(slot)
                total_score += evaluation.get('preference_score', 0)
                valid_participants += 1
            except Exception as e:
                print(f"Error calculating consensus for {participant.email}: {e}")
                continue
        
        return total_score / valid_participants if valid_participants > 0 else 0
    
    def _calculate_timezone_fairness(self, participants: List, slot: Dict) -> float:
        """Calculate timezone fairness score"""
        try:
            start_time = datetime.fromisoformat(slot['start_time'])
            
            # Check how fair the time is across different timezones
            timezone_scores = []
            for participant in participants:
                try:
                    # Get participant's timezone (default to IST if not available)
                    participant_tz = getattr(participant, 'timezone', self.default_timezone)
                    if isinstance(participant_tz, str):
                        participant_tz = pytz.timezone(participant_tz)
                    
                    local_time = start_time.astimezone(participant_tz)
                    hour = local_time.hour
                    
                    # Score based on business hours (9-17 is optimal)
                    if 9 <= hour <= 17:
                        timezone_scores.append(1.0)
                    elif 8 <= hour <= 18:
                        timezone_scores.append(0.8)
                    elif 7 <= hour <= 19:
                        timezone_scores.append(0.6)
                    else:
                        timezone_scores.append(0.2)
                except Exception as e:
                    print(f"Error calculating timezone fairness for {participant.email}: {e}")
                    timezone_scores.append(0.5)  # Default score
            
            return sum(timezone_scores) / len(timezone_scores) if timezone_scores else 0.5
        except Exception as e:
            print(f"Error in timezone fairness calculation: {e}")
            return 0.5
    
    async def _negotiate_best_slot(self, participants: List, alternative_slots: List[Dict]) -> Dict:
        """Select the best slot through LLM-powered negotiation"""
        if not alternative_slots:
            return None
        
        # Use LLM to analyze and select the best option
        try:
            negotiation_prompt = await self._build_negotiation_prompt(participants, alternative_slots)
            llm_response = await self.llm.generate_async(negotiation_prompt, max_tokens=200)
            selected_index = self._parse_llm_selection(llm_response, len(alternative_slots))
        except Exception as e:
            print(f"LLM negotiation failed: {e}")
            selected_index = 0  # Fallback to highest scored slot
            llm_response = "Selected highest scored option due to LLM failure"
        
        # Get the selected slot
        best_slot = alternative_slots[selected_index]
        
        # Gather final evaluations
        final_evaluations = []
        for participant in participants:
            try:
                evaluation = await participant.evaluate_proposal(best_slot)
                final_evaluations.append(evaluation)
            except Exception as e:
                print(f"Error in final evaluation for {participant.email}: {e}")
                final_evaluations.append({
                    'decision': 'ACCEPT',
                    'reason': 'default_accept',
                    'preference_score': 0.5,
                    'participant': participant.email,
                    'timezone': 'Asia/Kolkata'
                })
        
        return {
            'success': True,
            'slot': best_slot,
            'evaluations': final_evaluations,
            'conflicts': [],
            'consensus_score': best_slot['overall_score'],
            'selection_reasoning': llm_response
        }
    
    async def _build_negotiation_prompt(self, participants: List, alternatives: List[Dict]) -> str:
        """Build prompt for LLM-powered negotiation"""
        participant_info = []
        for p in participants:
            try:
                tz_name = getattr(p, 'timezone', self.default_timezone)
                if hasattr(tz_name, 'zone'):
                    tz_name = tz_name.zone
                preferences = getattr(p, 'preferences', {})
                participant_info.append(f"- {p.email}: timezone {tz_name}, preferences {preferences}")
            except Exception as e:
                participant_info.append(f"- {p.email}: timezone Asia/Kolkata, preferences unknown")
        
        alternatives_info = []
        for i, alt in enumerate(alternatives[:5]):  # Top 5 only
            alternatives_info.append(f"{i}: {alt['time_display']} (score: {alt['overall_score']:.2f})")
        
        prompt = f"""
        You are an AI meeting negotiator. Select the best meeting time for these participants:
        
        Participants:
        {chr(10).join(participant_info)}
        
        Available options (ranked by score):
        {chr(10).join(alternatives_info)}
        
        Consider timezone fairness, individual preferences, and overall consensus.
        Respond with just the number (0-{min(4, len(alternatives)-1)}) of your selected option.
        """
        
        return prompt
    
    def _parse_llm_selection(self, llm_response: str, max_options: int) -> int:
        """Parse LLM response to extract selected option"""
        try:
            # Extract number from response
            import re
            numbers = re.findall(r'\b(\d+)\b', llm_response)
            if numbers:
                selected = int(numbers[0])
                return min(selected, max_options - 1)
        except:
            pass
        
        return 0  # Default to first option
    
    def _create_success_response(self, result: Dict, meeting_request: Dict, alternatives: List[Dict]) -> Dict:
        """Create successful scheduling response"""
        slot = result['slot']
        
        return {
            'success': True,
            'scheduled_slot': {
                'start_time': slot['start_time'],
                'end_time': slot['end_time'],
                'display_time': slot['time_display']
            },
            'alternatives_considered': [
                {
                    'start_time': alt['start_time'],
                    'end_time': alt['end_time'],
                    'overall_score': alt['overall_score'],
                    'time_display': alt['time_display']
                } for alt in alternatives[:5]
            ],
            'negotiation_summary': {
                'consensus_score': result['consensus_score'],
                'conflicts_resolved': len([e for e in result['evaluations'] if e['decision'] == 'ACCEPT']),
                'total_participants': len(result['evaluations']),
                'selection_reasoning': result.get('selection_reasoning', 'Optimal consensus achieved')
            }
        }
    
    def _create_failure_response(self, meeting_request: Dict, reason: str) -> Dict:
        """Create failure response"""
        return {
            'success': False,
            'reason': reason,
            'alternatives_considered': [],
            'negotiation_summary': {
                'consensus_score': 0,
                'conflicts_resolved': 0,
                'total_participants': len(meeting_request.get('Attendees', [])),
                'selection_reasoning': f"Failed: {reason}"
            }
        }
    
    def _get_default_date(self) -> str:
        """Get default target date (tomorrow)"""
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")
    
    def _format_time_display(self, iso_time: str) -> str:
        """Format time for display"""
        try:
            dt = datetime.fromisoformat(iso_time)
            return dt.strftime("%H:%M IST")
        except:
            return iso_time