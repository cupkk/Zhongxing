"""Competition Agent implementation.

The key design is to let the VLM make the visual decision, while local code
handles schema safety, app-name normalization, coordinate clamping, and loop
prevention before returning AgentOutput to the official TestRunner.
"""

from __future__ import annotations

import logging

from agent_base import BaseAgent, AgentInput, AgentOutput
from utils.candidate_miner import CandidateMiner
from utils.memory import AgentMemory
from utils.jsonl_logger import DecisionLogger
from utils.output_parser import OutputParser
from utils.policy import RulePolicy
from utils.prompt_builder import PromptBuilder
from utils.task_parser import parse_task
from utils.validator import ActionValidator


logger = logging.getLogger(__name__)


class Agent(BaseAgent):
    def _initialize(self):
        self.memory = AgentMemory()
        self.prompt_builder = PromptBuilder()
        self.output_parser = OutputParser()
        self.validator = ActionValidator()
        self.policy = RulePolicy()
        self.decision_logger = DecisionLogger()
        self.candidate_miner = CandidateMiner()

    def reset(self):
        self.memory.reset()

    def act(self, input_data: AgentInput) -> AgentOutput:
        task_slots = parse_task(input_data.instruction)
        self.memory.task_slots = task_slots
        self.memory.last_candidates = self.candidate_miner.build(input_data, self.memory, task_slots)

        pre_decision = self.policy.pre_decide(
            input_data=input_data,
            memory=self.memory,
            task_slots=task_slots,
            has_api_key=bool(self.api_key),
        )
        if pre_decision is not None:
            output = self.validator.validate(pre_decision, input_data, self.memory, task_slots)
            output.raw_output = f"rule:{pre_decision}"
            self.decision_logger.log(
                input_data=input_data,
                task_slots=task_slots,
                memory=self.memory,
                source="rule",
                raw_output=output.raw_output,
                parsed_decision=pre_decision,
                final_output=output,
            )
            self.memory.update(output, input_data)
            return output

        raw_output = ""
        decision = {}
        try:
            messages = self.prompt_builder.build(input_data, self.memory, task_slots)
            response = self._call_api(messages, temperature=0, top_p=0.7)
            raw_output = response.choices[0].message.content or ""
            decision = self.output_parser.parse(raw_output)
            if not decision.get("action"):
                decision = self.policy.fallback_decide(input_data, self.memory, task_slots)
            output = self.validator.validate(decision, input_data, self.memory, task_slots)
            output.raw_output = raw_output
            output.usage = self.extract_usage_info(response)
        except Exception as exc:
            logger.exception("VLM decision failed, using safe fallback: %s", exc)
            fallback = self.policy.no_api_fallback(input_data, self.memory, task_slots)
            decision = fallback
            output = self.validator.validate(fallback, input_data, self.memory, task_slots)
            output.raw_output = f"fallback_after_error:{type(exc).__name__}:{exc}\n{raw_output}"

        self.decision_logger.log(
            input_data=input_data,
            task_slots=task_slots,
            memory=self.memory,
            source="vlm" if raw_output else "fallback",
            raw_output=raw_output,
            parsed_decision=decision,
            final_output=output,
            error="" if raw_output else output.raw_output,
        )
        self.memory.update(output, input_data)
        return output
