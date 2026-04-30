#!/usr/bin/env python3
"""CLI demo for PawPal+ AI — verifies core logic and the agentic assistant end-to-end."""

import os
from datetime import date

from pawpal_system import Owner, Pet, Task, Scheduler
from rag_system import KnowledgeBase
from ai_agent import PawPalAgent


def sep(title: str = "") -> None:
    if title:
        print(f"\n{'='*64}\n  {title}\n{'='*64}")
    else:
        print("-" * 64)


# ---------------------------------------------------------------------------
# Demo 1: Core OOP scheduling system
# ---------------------------------------------------------------------------

def demo_scheduling() -> Owner:
    sep("DEMO 1 — CORE SCHEDULING SYSTEM")

    owner = Owner("Alex Johnson", "alex@example.com")
    buddy = Pet("Buddy", "Dog", "Golden Retriever", 3)
    whiskers = Pet("Whiskers", "Cat", "Tabby", 5)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)

    today = date.today()

    # Buddy's tasks (intentionally out of order to test sorting)
    buddy.add_task(Task("Evening walk",       "18:00", "daily",  "Buddy",    "medium", due_date=today))
    buddy.add_task(Task("Heartworm tablet",   "09:00", "weekly", "Buddy",    "high",   due_date=today))
    buddy.add_task(Task("Morning walk",       "07:00", "daily",  "Buddy",    "high",   due_date=today))
    buddy.add_task(Task("Breakfast",          "07:30", "daily",  "Buddy",    "high",   due_date=today))
    buddy.add_task(Task("Teeth brushing",     "20:00", "daily",  "Buddy",    "low",    due_date=today))
    # Intentional conflict — same time as Morning walk
    buddy.add_task(Task("Vet appointment",    "07:00", "once",   "Buddy",    "high",   due_date=today))

    # Whiskers' tasks
    whiskers.add_task(Task("Breakfast",       "08:00", "daily",  "Whiskers", "high",   due_date=today))
    whiskers.add_task(Task("Litter cleaning", "09:30", "daily",  "Whiskers", "medium", due_date=today))
    whiskers.add_task(Task("Playtime",        "19:00", "daily",  "Whiskers", "low",    due_date=today))

    scheduler = Scheduler(owner)

    sep("TODAY'S SCHEDULE — sorted by time")
    for t in scheduler.get_todays_schedule():
        print(f"  {t}")

    sep("HIGH PRIORITY TASKS")
    for t in scheduler.get_high_priority_tasks():
        print(f"  {t}")

    sep("CONFLICT DETECTION")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for c in conflicts:
            print(f"  {c}")
    else:
        print("  No conflicts detected.")

    sep("FILTER — Whiskers only")
    for t in scheduler.filter_tasks(pet_name="Whiskers"):
        print(f"  {t}")

    sep("RECURRING TASK DEMO")
    morning_walk = buddy.tasks[2]  # "Morning walk"
    print(f"  Completing: {morning_walk.description}")
    next_t = scheduler.mark_task_complete(morning_walk.task_id)
    if next_t:
        print(f"  Next occurrence rescheduled → {next_t.due_date} at {next_t.time}")

    sep("SCHEDULE SUMMARY")
    for k, v in scheduler.get_summary().items():
        print(f"  {k}: {v}")

    return owner


# ---------------------------------------------------------------------------
# Demo 2: AI Agent with RAG
# ---------------------------------------------------------------------------

def demo_ai_agent(owner: Owner) -> None:
    sep("DEMO 2 — AI AGENT (requires ANTHROPIC_API_KEY)")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("  Skipped: set ANTHROPIC_API_KEY to run the AI agent demo.")
        return

    kb = KnowledgeBase()
    agent = PawPalAgent(owner, kb)

    queries = [
        "What does today's schedule look like for all pets?",
        "Are there any scheduling conflicts I should fix?",
        "How often should I feed my dog and at what times?",
    ]

    for q in queries:
        print(f"\n  > {q}")
        reply = agent.chat(q)
        # Truncate long replies for CLI readability
        preview = reply[:400] + ("…" if len(reply) > 400 else "")
        print(f"  PawPal AI: {preview}")
        sep()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    owner = demo_scheduling()
    demo_ai_agent(owner)
    print("\n✅  Demo complete!")
