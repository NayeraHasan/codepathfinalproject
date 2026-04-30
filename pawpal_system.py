"""Core OOP logic for PawPal+: Owner, Pet, Task, and Scheduler classes."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional
import logging
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}


@dataclass
class Task:
    """A single pet care activity."""

    description: str
    time: str                   # "HH:MM" 24-hour format
    frequency: str              # "once" | "daily" | "weekly"
    pet_name: str
    priority: str = "medium"   # "low" | "medium" | "high"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def mark_complete(self) -> Optional["Task"]:
        """Mark complete; return next Task for recurring frequencies, else None."""
        self.completed = True
        logger.info("Task '%s' for %s marked complete.", self.description, self.pet_name)

        if self.frequency == "daily":
            return Task(self.description, self.time, self.frequency, self.pet_name,
                        self.priority, due_date=self.due_date + timedelta(days=1))
        if self.frequency == "weekly":
            return Task(self.description, self.time, self.frequency, self.pet_name,
                        self.priority, due_date=self.due_date + timedelta(weeks=1))
        return None

    def __repr__(self) -> str:
        status = "✅" if self.completed else "⏳"
        emoji = PRIORITY_EMOJI.get(self.priority, "⚪")
        return f"{status} [{self.time}] {emoji} {self.description} ({self.pet_name}) [{self.frequency}]"


class Pet:
    """Stores pet metadata and owns a list of Tasks."""

    def __init__(self, name: str, species: str, breed: str = "", age: int = 0):
        self.name = name
        self.species = species
        self.breed = breed
        self.age = age
        self.tasks: List[Task] = []
        logger.info("Pet '%s' (%s) created.", name, species)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's schedule."""
        self.tasks.append(task)
        logger.info("Task '%s' added to %s.", task.description, self.name)

    def remove_task(self, task_id: str) -> bool:
        """Remove task by ID; return True if found and removed."""
        for i, t in enumerate(self.tasks):
            if t.task_id == task_id:
                logger.info("Task '%s' removed from %s.", t.description, self.name)
                self.tasks.pop(i)
                return True
        return False

    def get_pending_tasks(self) -> List[Task]:
        """Return all incomplete tasks."""
        return [t for t in self.tasks if not t.completed]

    def __repr__(self) -> str:
        return f"Pet({self.name}, {self.species}, {len(self.tasks)} tasks)"


class Owner:
    """Top-level entity; holds a list of Pets and provides aggregate task access."""

    def __init__(self, name: str, email: str = ""):
        self.name = name
        self.email = email
        self.pets: List[Pet] = []
        logger.info("Owner '%s' created.", name)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's profile."""
        self.pets.append(pet)
        logger.info("Pet '%s' added to %s's profile.", pet.name, self.name)

    def get_pet(self, name: str) -> Optional[Pet]:
        """Find a pet by name (case-insensitive)."""
        for p in self.pets:
            if p.name.lower() == name.lower():
                return p
        return None

    def get_all_tasks(self) -> List[Task]:
        """Return every task across all pets."""
        return [t for pet in self.pets for t in pet.tasks]

    def __repr__(self) -> str:
        return f"Owner({self.name}, {len(self.pets)} pets)"


class Scheduler:
    """Algorithmic layer: sorting, filtering, conflict detection, and recurrence."""

    def __init__(self, owner: Owner):
        self.owner = owner
        logger.info("Scheduler initialized for '%s'.", owner.name)

    def sort_by_time(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Return tasks sorted by 'HH:MM' time string."""
        if tasks is None:
            tasks = self.owner.get_all_tasks()
        return sorted(tasks, key=lambda t: t.time)

    def filter_tasks(self, pet_name: Optional[str] = None,
                     completed: Optional[bool] = None) -> List[Task]:
        """Return tasks matching optional pet_name and/or completion status."""
        tasks = self.owner.get_all_tasks()
        if pet_name:
            tasks = [t for t in tasks if t.pet_name.lower() == pet_name.lower()]
        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]
        return tasks

    def detect_conflicts(self) -> List[str]:
        """Flag tasks scheduled at the exact same time for the same pet."""
        warnings: List[str] = []
        seen: dict = {}
        for task in self.owner.get_all_tasks():
            key = (task.pet_name.lower(), task.time)
            if key in seen:
                msg = (f"⚠️ Conflict: '{task.description}' and '{seen[key]}' "
                       f"both at {task.time} for {task.pet_name}")
                warnings.append(msg)
                logger.warning(msg)
            else:
                seen[key] = task.description
        return warnings

    def mark_task_complete(self, task_id: str) -> Optional[Task]:
        """Complete a task and auto-schedule the next recurrence if applicable."""
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.task_id == task_id:
                    next_task = task.mark_complete()
                    if next_task:
                        pet.add_task(next_task)
                        logger.info("Recurring task rescheduled for %s.", next_task.due_date)
                    return next_task
        logger.warning("Task ID %s not found.", task_id)
        return None

    def get_todays_schedule(self) -> List[Task]:
        """Return today's tasks sorted by time."""
        today = date.today()
        return self.sort_by_time([t for t in self.owner.get_all_tasks() if t.due_date == today])

    def get_high_priority_tasks(self) -> List[Task]:
        """Return pending high-priority tasks sorted by time."""
        tasks = [t for t in self.owner.get_all_tasks() if t.priority == "high" and not t.completed]
        return self.sort_by_time(tasks)

    def get_summary(self) -> dict:
        """Return aggregate counts for the current schedule."""
        all_tasks = self.owner.get_all_tasks()
        return {
            "total_tasks": len(all_tasks),
            "completed": sum(1 for t in all_tasks if t.completed),
            "pending": sum(1 for t in all_tasks if not t.completed),
            "conflicts": len(self.detect_conflicts()),
            "pets": len(self.owner.pets),
        }
