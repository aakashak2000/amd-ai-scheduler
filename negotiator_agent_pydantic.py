import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from typing import List, Dict, Any
import asyncio
from models import NegotiationResult, TimeSlot, ParticipantEvaluation, MeetingRequest
from participant_agent_pydantic import ParticipantAgent
from tools import (
    get_current_date,
    convert_time_across_timezones,
    check_business_hours,
    generate_time_slots
)

class NegotiatorAgent:
    def __init__(self, base_url: str = "http://localhost:3000/v1"):
        # Create provider for local vLLM DeepSeek server
        provider = OpenAIProvider(
            base_url=base_url,
            api_key="dummy"
        )
        
        self.model = OpenAIModel("deepseek", provider=provider)
        
        self.agent = Agent(
            model=self.model,
            result_type=NegotiationResult,
            tools=[
                get_current_date,
                convert_time_across_timezones,
                check_business_hours,
                generate_time_slots
            ],
            system_prompt="""You are an expert meeting negotiator and scheduler.

Your role is to:
1. Find optimal meeting times across multiple participants and timezones
2. Negotiate conflicts and find compromises
3. Evaluate timezone fairness and participant satisfaction
4. Select the best time slot based on overall consensus

NEGOTIATION STRATEGY:
- Prioritize times that work for most participants
- Balance timezone fairness across regions
- Consider participant seniority and preferences
- Find creative compromises when conflicts exist
- Always explain your reasoning clearly

TIMEZONE CONSIDERATIONS:
- Ensure meeting times are reasonable for all timezones
- Avoid very early morning or late evening for any participant
- Rotate inconvenient times fairly across team members

DECISION CRITERIA:
- Participant availability (hard constraint)
- Business hours across timezones
- Individual preferences and work patterns
- Meeting urgency and importance
- Overall team consensus

You have access to tools for timezone conversion and time analysis.
Always provide detailed reasoning for your scheduling decisions."""
        )
    
    async def negotiate_meeting(self, 
                               participants: List[ParticipantAgent], 
                               meeting_request: MeetingRequest) -> NegotiationResult:
        """Negotiate optimal meeting time across all participants."""
        try:
            print(f"Negotiating meeting for {len(participants)} participants")
            
            # Step 1: Collect all available slots from participants
            target_date = meeting_request.target_date
            duration_mins = int(meeting_request.Duration_mins)
            
            all_participant_slots = {}
            for participant in participants:
                slots = await participant.find_available_slots(target_date, duration_mins)
                all_participant_slots[participant.email] = slots
                print(f"  {participant.email}: {len(slots)} available slots")
            
            # Step 2: Find common time slots
            common_slots = self._find_common_slots(all_participant_slots)
            print(f"Found {len(common_slots)} common time slots")
            
            if not common_slots:
                return NegotiationResult(
                    success=False,
                    reason="No common available time slots found across all participants",
                    evaluations=[],
                    conflicts=[],
                    consensus_score=0.0
                )
            
            # Step 3: Evaluate each common slot with all participants
            evaluated_slots = []
            for slot in common_slots:
                evaluations = await self._evaluate_slot_with_participants(slot, participants)
                
                # Calculate consensus score
                consensus_score = self._calculate_consensus_score(evaluations)
                timezone_fairness = self._calculate_timezone_fairness(slot, participants)
                
                slot.overall_score = consensus_score * 0.7 + timezone_fairness * 0.3
                slot.timezone_fairness = timezone_fairness
                
                evaluated_slots.append({
                    'slot': slot,
                    'evaluations': evaluations,
                    'consensus_score': consensus_score
                })
            
            # Step 4: Use AI agent to select the best slot
            best_slot_data = await self._select_best_slot(evaluated_slots, participants)
            
            if best_slot_data:
                return NegotiationResult(
                    success=True,
                    scheduled_slot=best_slot_data['slot'],
                    alternatives_considered=common_slots[:5],  # Top 5 alternatives
                    evaluations=best_slot_data['evaluations'],
                    consensus_score=best_slot_data['consensus_score'],
                    selection_reasoning=best_slot_data.get('reasoning', 'Optimal consensus achieved')
                )
            else:
                return NegotiationResult(
                    success=False,
                    reason="Could not find acceptable compromise among available slots",
                    alternatives_considered=common_slots[:5],
                    evaluations=[],
                    consensus_score=0.0
                )
                
        except Exception as e:
            print(f"Negotiation failed: {e}")
            return NegotiationResult(
                success=False,
                reason=f"Negotiation error: {str(e)}",
                evaluations=[],
                conflicts=[],
                consensus_score=0.0
            )
    
    def _find_common_slots(self, all_participant_slots: Dict[str, List[TimeSlot]]) -> List[TimeSlot]:
        """Find time slots that are available for ALL participants."""
        if not all_participant_slots:
            return []
        
        # Get all unique time slots
        all_time_slots = set()
        for participant_slots in all_participant_slots.values():
            for slot in participant_slots:
                slot_key = (slot.start_time, slot.end_time)
                all_time_slots.add(slot_key)
        
        # Filter to slots available for ALL participants
        common_slots = []
        for start_time, end_time in all_time_slots:
            available_for_all = True
            
            for participant_email, participant_slots in all_participant_slots.items():
                participant_has_slot = any(
                    slot.start_time == start_time and slot.end_time == end_time
                    for slot in participant_slots
                )
                
                if not participant_has_slot:
                    available_for_all = False
                    break
            
            if available_for_all:
                # Get the slot details from first participant
                first_participant_slots = list(all_participant_slots.values())[0]
                matching_slot = next(
                    slot for slot in first_participant_slots 
                    if slot.start_time == start_time and slot.end_time == end_time
                )
                
                common_slot = TimeSlot(
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=matching_slot.duration_minutes,
                    participants=list(all_participant_slots.keys()),
                    time_display=matching_slot.time_display
                )
                common_slots.append(common_slot)
        
        return common_slots
    
    async def _evaluate_slot_with_participants(self, 
                                             slot: TimeSlot, 
                                             participants: List[ParticipantAgent]) -> List[ParticipantEvaluation]:
        """Get evaluations from all participants for a time slot."""
        evaluation_tasks = []
        for participant in participants:
            task = participant.evaluate_proposal(slot)
            evaluation_tasks.append(task)
        
        evaluations = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid evaluations
        valid_evaluations = []
        for i, evaluation in enumerate(evaluations):
            if isinstance(evaluation, Exception):
                print(f"Evaluation failed for participant {participants[i].email}: {evaluation}")
                # Create default evaluation
                valid_evaluations.append(ParticipantEvaluation(
                    participant=participants[i].email,
                    decision='REJECT',
                    reason='evaluation_failed',
                    preference_score=0.0,
                    timezone=participants[i].preferences.get('timezone', 'Asia/Kolkata'),
                    llm_reasoning='Evaluation failed due to system error'
                ))
            else:
                valid_evaluations.append(evaluation)
        
        return valid_evaluations
    
    def _calculate_consensus_score(self, evaluations: List[ParticipantEvaluation]) -> float:
        """Calculate overall consensus score from participant evaluations."""
        if not evaluations:
            return 0.0
        
        total_score = 0.0
        for evaluation in evaluations:
            if evaluation.decision == 'ACCEPT':
                total_score += evaluation.preference_score
            elif evaluation.decision == 'CONDITIONAL_ACCEPT':
                total_score += evaluation.preference_score * 0.7
            # REJECT contributes 0
        
        return total_score / len(evaluations)
    
    def _calculate_timezone_fairness(self, slot: TimeSlot, participants: List[ParticipantAgent]) -> float:
        """Calculate timezone fairness score for a time slot."""
        try:
            from datetime import datetime
            import pytz
            
            start_time = datetime.fromisoformat(slot.start_time)
            
            timezone_scores = []
            for participant in participants:
                participant_tz = participant.preferences.get('timezone', 'Asia/Kolkata')
                tz = pytz.timezone(participant_tz)
                local_time = start_time.astimezone(tz)
                hour = local_time.hour
                
                # Score based on business hours preference
                if 9 <= hour <= 17:
                    timezone_scores.append(1.0)
                elif 8 <= hour <= 18:
                    timezone_scores.append(0.8)
                elif 7 <= hour <= 19:
                    timezone_scores.append(0.6)
                else:
                    timezone_scores.append(0.2)
            
            return sum(timezone_scores) / len(timezone_scores) if timezone_scores else 0.5
        except:
            return 0.5
    
    async def _select_best_slot(self, 
                               evaluated_slots: List[Dict], 
                               participants: List[ParticipantAgent]) -> Dict[str, Any]:
        """Use AI agent to intelligently select the best time slot."""
        try:
            # Sort by overall score first
            sorted_slots = sorted(evaluated_slots, key=lambda x: x['slot'].overall_score or 0, reverse=True)
            
            # Prepare data for AI decision
            slot_summaries = []
            for i, slot_data in enumerate(sorted_slots[:5]):  # Top 5 options
                slot = slot_data['slot']
                evaluations = slot_data['evaluations']
                
                accept_count = sum(1 for e in evaluations if e.decision == 'ACCEPT')
                conditional_count = sum(1 for e in evaluations if e.decision == 'CONDITIONAL_ACCEPT')
                reject_count = sum(1 for e in evaluations if e.decision == 'REJECT')
                
                slot_summaries.append(f"""
                Option {i}: {slot.time_display}
                - Overall Score: {slot.overall_score:.2f}
                - Consensus: {slot_data['consensus_score']:.2f}
                - Timezone Fairness: {slot.timezone_fairness:.2f}
                - Responses: {accept_count} Accept, {conditional_count} Conditional, {reject_count} Reject
                """)
            
            participant_timezones = [p.preferences.get('timezone', 'Asia/Kolkata') for p in participants]
            
            prompt = f"""
            Select the best meeting time for {len(participants)} participants across timezones: {set(participant_timezones)}
            
            Available options:
            {''.join(slot_summaries)}
            
            Consider:
            - Maximum participant acceptance
            - Timezone fairness across regions
            - Overall consensus scores
            - Business hour appropriateness
            
            Return the option number (0-{len(sorted_slots[:5])-1}) of your selection with reasoning.
            """
            
            result = await self.agent.run(prompt)
            
            # Parse the selection (try to extract number from response)
            selection_text = str(result.data.selection_reasoning) if hasattr(result.data, 'selection_reasoning') else str(result.data)
            
            import re
            numbers = re.findall(r'\b(\d+)\b', selection_text)
            selected_index = 0  # Default to first option
            
            if numbers:
                try:
                    selected_index = min(int(numbers[0]), len(sorted_slots) - 1)
                except:
                    selected_index = 0
            
            best_slot_data = sorted_slots[selected_index]
            best_slot_data['reasoning'] = selection_text
            
            return best_slot_data
            
        except Exception as e:
            print(f"AI selection failed: {e}")
            # Return highest scored option
            if evaluated_slots:
                sorted_slots = sorted(evaluated_slots, key=lambda x: x['slot'].overall_score or 0, reverse=True)
                return sorted_slots[0]
            return None