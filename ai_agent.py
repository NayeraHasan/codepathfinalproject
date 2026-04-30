"""PawPal AI Agent: Claude-powered agentic assistant using tool use + RAG."""

import json
import logging
from typing import List

import anthropic

from pawpal_system import Owner, Scheduler
from rag_system import KnowledgeBase

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are PawPal AI, a warm and knowledgeable pet care assistant.
You help owners manage schedules, medications, and daily routines for their pets.

You have tools to:
- View today's schedule and overall summary
- Check for scheduling conflicts
- Look up details on a specific pet
- Search a pet care knowledge base for health and care advice

Always retrieve data with a tool before answering schedule or pet-specific questions.
For health or care advice, search the knowledge base first to ground your response.
Keep answers concise, actionable, and friendly. Flag conflicts or urgent issues clearly."""


class PawPalAgent:
    """Agentic assistant that calls Scheduler tools and RAG before answering."""

    def __init__(self, owner: Owner, knowledge_base: KnowledgeBase):
        self.owner = owner
        self.scheduler = Scheduler(owner)
        self.kb = knowledge_base
        self.client = anthropic.Anthropic()
        self.history: List[dict] = []
        self._tools = self._define_tools()
        logger.info("PawPal AI Agent initialized for '%s'.", owner.name)

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def _define_tools(self) -> list:
        return [
            {
                "name": "get_today_schedule",
                "description": "Return all tasks scheduled for today, sorted by time.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_schedule_summary",
                "description": "Return aggregate counts: total tasks, pending, completed, conflicts, pets.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "check_conflicts",
                "description": "Detect tasks scheduled at the same time for the same pet.",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_pet_info",
                "description": "Get details and pending tasks for a named pet.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pet_name": {
                            "type": "string",
                            "description": "Name of the pet to look up.",
                        }
                    },
                    "required": ["pet_name"],
                },
            },
            {
                "name": "search_pet_care_knowledge",
                "description": (
                    "Search the pet care knowledge base for advice on feeding, "
                    "medications, exercise, grooming, or health concerns."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Topic or question to search for.",
                        }
                    },
                    "required": ["query"],
                },
            },
        ]

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _run_tool(self, name: str, inputs: dict) -> str:
        """Dispatch a tool call and return its string result."""
        logger.info("Tool call: %s(%s)", name, inputs)

        if name == "get_today_schedule":
            tasks = self.scheduler.get_todays_schedule()
            return "\n".join(str(t) for t in tasks) if tasks else "No tasks scheduled for today."

        if name == "get_schedule_summary":
            return json.dumps(self.scheduler.get_summary(), indent=2)

        if name == "check_conflicts":
            conflicts = self.scheduler.detect_conflicts()
            return "\n".join(conflicts) if conflicts else "No scheduling conflicts detected."

        if name == "get_pet_info":
            pet_name = inputs.get("pet_name", "")
            pet = self.owner.get_pet(pet_name)
            if not pet:
                available = [p.name for p in self.owner.pets]
                return f"Pet '{pet_name}' not found. Available: {available}"
            pending = pet.get_pending_tasks()
            lines = [
                f"Name: {pet.name}",
                f"Species: {pet.species}",
                f"Breed: {pet.breed or 'Unknown'}",
                f"Age: {pet.age} year(s)",
                f"Total tasks: {len(pet.tasks)}, Pending: {len(pending)}",
                "Pending tasks:",
                *([str(t) for t in pending] if pending else ["  (none)"]),
            ]
            return "\n".join(lines)

        if name == "search_pet_care_knowledge":
            query = inputs.get("query", "")
            context = self.kb.format_context(query)
            return context if context else "No relevant information found in knowledge base."

        return f"Unknown tool: {name}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> str:
        """Send a message; return the assistant's final text response."""
        self.history.append({"role": "user", "content": user_message})
        logger.info("User: %s", user_message[:120])

        for _ in range(6):  # safety cap on agentic iterations
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=self._tools,
                messages=self.history,
            )

            if response.stop_reason == "tool_use":
                self.history.append({"role": "assistant", "content": response.content})
                tool_results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": blk.id,
                        "content": self._run_tool(blk.name, blk.input),
                    }
                    for blk in response.content
                    if blk.type == "tool_use"
                ]
                self.history.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                text = "".join(
                    blk.text for blk in response.content if hasattr(blk, "text")
                )
                self.history.append({"role": "assistant", "content": text})
                logger.info("Agent reply: %s", text[:120])
                return text

            else:
                break

        return "I couldn't complete that request. Please try again with a more specific question."

    def reset_conversation(self) -> None:
        """Clear conversation history."""
        self.history = []
        logger.info("Conversation history cleared.")

    def get_proactive_alerts(self) -> List[str]:
        """Return any urgent alerts (conflicts, high-priority tasks)."""
        alerts: List[str] = []
        alerts.extend(self.scheduler.detect_conflicts())
        high = self.scheduler.get_high_priority_tasks()
        if high:
            alerts.append(f"🔴 {len(high)} high-priority task(s) still pending.")
        summary = self.scheduler.get_summary()
        if summary["total_tasks"] > 0 and summary["pending"] == 0:
            alerts.append("✅ All tasks completed for today!")
        return alerts
