"""Pytest unit tests for PawPal+ core system."""

import pytest
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner_with_pets():
    owner = Owner("Test Owner")
    buddy = Pet("Buddy", "Dog", "Labrador", 2)
    whiskers = Pet("Whiskers", "Cat", "Siamese", 4)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)
    return owner


@pytest.fixture
def populated_owner(owner_with_pets):
    today = date.today()
    buddy = owner_with_pets.get_pet("Buddy")
    whiskers = owner_with_pets.get_pet("Whiskers")
    buddy.add_task(Task("Morning walk", "07:00", "daily",  "Buddy",    "high",   due_date=today))
    buddy.add_task(Task("Feeding",      "12:00", "daily",  "Buddy",    "medium", due_date=today))
    buddy.add_task(Task("Evening walk", "18:00", "once",   "Buddy",    "low",    due_date=today))
    whiskers.add_task(Task("Feeding",   "08:00", "daily",  "Whiskers", "high",   due_date=today))
    return owner_with_pets


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_task_mark_complete_sets_flag():
    task = Task("Test task", "10:00", "once", "Pet")
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_daily_task_returns_next_day():
    today = date.today()
    task = Task("Daily feed", "08:00", "daily", "Buddy", due_date=today)
    next_t = task.mark_complete()
    assert next_t is not None
    assert next_t.due_date == today + timedelta(days=1)
    assert next_t.description == task.description


def test_weekly_task_returns_next_week():
    today = date.today()
    task = Task("Weekly bath", "10:00", "weekly", "Buddy", due_date=today)
    next_t = task.mark_complete()
    assert next_t is not None
    assert next_t.due_date == today + timedelta(weeks=1)


def test_once_task_returns_none():
    task = Task("Vet visit", "10:00", "once", "Buddy")
    assert task.mark_complete() is None


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increments_count():
    pet = Pet("Fido", "Dog")
    pet.add_task(Task("Walk", "09:00", "daily", "Fido"))
    assert len(pet.tasks) == 1


def test_get_pending_tasks_excludes_completed():
    pet = Pet("Fluffy", "Cat")
    t1 = Task("Feed", "08:00", "daily", "Fluffy")
    t2 = Task("Play", "15:00", "daily", "Fluffy")
    pet.add_task(t1)
    pet.add_task(t2)
    t1.mark_complete()
    pending = pet.get_pending_tasks()
    assert len(pending) == 1
    assert pending[0].description == "Play"


def test_remove_task_returns_true():
    pet = Pet("Rex", "Dog")
    task = Task("Walk", "07:00", "daily", "Rex")
    pet.add_task(task)
    assert pet.remove_task(task.task_id) is True
    assert len(pet.tasks) == 0


def test_remove_nonexistent_task_returns_false():
    pet = Pet("Rex", "Dog")
    assert pet.remove_task("fake-id-0000") is False


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_owner_add_pet(owner_with_pets):
    initial = len(owner_with_pets.pets)
    owner_with_pets.add_pet(Pet("Goldie", "Fish"))
    assert len(owner_with_pets.pets) == initial + 1


def test_owner_get_pet_case_insensitive(owner_with_pets):
    assert owner_with_pets.get_pet("buddy") is not None
    assert owner_with_pets.get_pet("BUDDY") is not None


def test_owner_get_nonexistent_pet(owner_with_pets):
    assert owner_with_pets.get_pet("Dragon") is None


def test_owner_get_all_tasks(populated_owner):
    assert len(populated_owner.get_all_tasks()) == 4


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def test_sort_by_time_is_chronological(populated_owner):
    sched = Scheduler(populated_owner)
    times = [t.time for t in sched.sort_by_time()]
    assert times == sorted(times)


def test_sort_by_time_out_of_order_input():
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    today = date.today()
    pet.add_task(Task("Evening",  "20:00", "once", "Dog", due_date=today))
    pet.add_task(Task("Morning",  "07:00", "once", "Dog", due_date=today))
    pet.add_task(Task("Noon",     "12:00", "once", "Dog", due_date=today))
    sched = Scheduler(owner)
    result = sched.sort_by_time()
    assert [t.time for t in result] == ["07:00", "12:00", "20:00"]


def test_conflict_detection_true_positive():
    owner = Owner("T")
    pet = Pet("Buddy", "Dog")
    owner.add_pet(pet)
    today = date.today()
    pet.add_task(Task("Walk", "07:00", "once", "Buddy", due_date=today))
    pet.add_task(Task("Vet",  "07:00", "once", "Buddy", due_date=today))
    sched = Scheduler(owner)
    assert len(sched.detect_conflicts()) == 1


def test_conflict_detection_true_negative(populated_owner):
    sched = Scheduler(populated_owner)
    assert len(sched.detect_conflicts()) == 0


def test_filter_by_pet(populated_owner):
    sched = Scheduler(populated_owner)
    buddy_tasks = sched.filter_tasks(pet_name="Buddy")
    assert all(t.pet_name == "Buddy" for t in buddy_tasks)
    assert len(buddy_tasks) == 3


def test_filter_by_completion(populated_owner):
    sched = Scheduler(populated_owner)
    populated_owner.get_all_tasks()[0].completed = True
    completed = sched.filter_tasks(completed=True)
    pending = sched.filter_tasks(completed=False)
    assert len(completed) == 1
    assert all(not t.completed for t in pending)


def test_mark_complete_adds_recurring_task():
    owner = Owner("T")
    pet = Pet("Buddy", "Dog")
    owner.add_pet(pet)
    today = date.today()
    task = Task("Daily walk", "07:00", "daily", "Buddy", due_date=today)
    pet.add_task(task)
    sched = Scheduler(owner)
    sched.mark_task_complete(task.task_id)
    assert len(pet.tasks) == 2
    assert pet.tasks[-1].due_date == today + timedelta(days=1)


def test_get_todays_schedule_excludes_other_dates():
    owner = Owner("T")
    pet = Pet("Rex", "Dog")
    owner.add_pet(pet)
    today = date.today()
    pet.add_task(Task("Today task",    "07:00", "once", "Rex", due_date=today))
    pet.add_task(Task("Tomorrow task", "07:00", "once", "Rex", due_date=today + timedelta(days=1)))
    sched = Scheduler(owner)
    assert len(sched.get_todays_schedule()) == 1


def test_empty_pet_has_no_tasks():
    owner = Owner("T")
    owner.add_pet(Pet("Empty", "Dog"))
    sched = Scheduler(owner)
    assert sched.sort_by_time() == []
    summary = sched.get_summary()
    assert summary["total_tasks"] == 0
    assert summary["pending"] == 0


def test_schedule_summary_accuracy():
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    pet.add_task(Task("Walk", "07:00", "once", "Dog"))
    pet.add_task(Task("Feed", "08:00", "once", "Dog"))
    pet.tasks[0].completed = True
    sched = Scheduler(owner)
    s = sched.get_summary()
    assert s["total_tasks"] == 2
    assert s["completed"] == 1
    assert s["pending"] == 1
    assert s["pets"] == 1
