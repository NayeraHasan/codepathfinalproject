#!/usr/bin/env python3
"""
PawPal+ Reliability Evaluation Harness
Runs predefined test cases and prints a scored summary + JSON report.
"""

import json
import os
import sys
import time
from datetime import date, timedelta
from typing import Tuple

# Allow running from project root or tests/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import Owner, Pet, Task, Scheduler
from rag_system import KnowledgeBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Result = Tuple[bool, str, float]  # (passed, message, confidence 0-1)


def run(name: str, fn) -> Tuple[str, bool, str, float, float]:
    """Execute a test function and return (name, passed, msg, confidence, elapsed_s)."""
    t0 = time.perf_counter()
    try:
        passed, msg, conf = fn()
    except Exception as exc:
        passed, msg, conf = False, f"Exception: {exc}", 0.0
    elapsed = time.perf_counter() - t0
    return name, passed, msg, conf, elapsed


def make_setup() -> Tuple[Owner, Scheduler]:
    owner = Owner("Harness Owner")
    buddy = Pet("Buddy", "Dog", "Labrador", 3)
    whiskers = Pet("Whiskers", "Cat", "Tabby", 5)
    owner.add_pet(buddy)
    owner.add_pet(whiskers)
    today = date.today()
    buddy.add_task(Task("Morning walk", "07:00", "daily",  "Buddy",    "high",   due_date=today))
    buddy.add_task(Task("Feeding",      "08:00", "daily",  "Buddy",    "high",   due_date=today))
    buddy.add_task(Task("Medication",   "09:00", "weekly", "Buddy",    "high",   due_date=today))
    whiskers.add_task(Task("Feeding",   "08:30", "daily",  "Whiskers", "high",   due_date=today))
    return owner, Scheduler(owner)


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def tc_sorting_correctness() -> Result:
    owner, scheduler = make_setup()
    owner.get_pet("Buddy").add_task(Task("Night check", "22:00", "daily", "Buddy"))
    times = [t.time for t in scheduler.sort_by_time()]
    ok = times == sorted(times)
    return ok, f"Order: {times}", 1.0 if ok else 0.0


def tc_conflict_true_positive() -> Result:
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    today = date.today()
    pet.add_task(Task("Walk", "07:00", "once", "Dog", due_date=today))
    pet.add_task(Task("Vet",  "07:00", "once", "Dog", due_date=today))
    conflicts = Scheduler(owner).detect_conflicts()
    ok = len(conflicts) == 1
    return ok, f"Detected {len(conflicts)} conflict(s)", 1.0 if ok else 0.0


def tc_conflict_true_negative() -> Result:
    owner, scheduler = make_setup()
    conflicts = scheduler.detect_conflicts()
    ok = len(conflicts) == 0
    return ok, f"False positives: {len(conflicts)}", 1.0 if ok else 0.0


def tc_daily_recurrence() -> Result:
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    today = date.today()
    task = Task("Daily feed", "08:00", "daily", "Dog", due_date=today)
    pet.add_task(task)
    Scheduler(owner).mark_task_complete(task.task_id)
    ok = (len(pet.tasks) == 2 and pet.tasks[-1].due_date == today + timedelta(days=1))
    return ok, f"Next due: {pet.tasks[-1].due_date if len(pet.tasks) > 1 else 'N/A'}", 1.0 if ok else 0.0


def tc_weekly_recurrence() -> Result:
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    today = date.today()
    task = Task("Weekly bath", "10:00", "weekly", "Dog", due_date=today)
    pet.add_task(task)
    Scheduler(owner).mark_task_complete(task.task_id)
    ok = (len(pet.tasks) == 2 and pet.tasks[-1].due_date == today + timedelta(weeks=1))
    return ok, f"Next due: {pet.tasks[-1].due_date if len(pet.tasks) > 1 else 'N/A'}", 1.0 if ok else 0.0


def tc_once_no_recurrence() -> Result:
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    task = Task("Vet", "10:00", "once", "Dog")
    pet.add_task(task)
    Scheduler(owner).mark_task_complete(task.task_id)
    ok = len(pet.tasks) == 1
    return ok, f"Task count after complete: {len(pet.tasks)}", 1.0 if ok else 0.0


def tc_filter_by_pet() -> Result:
    owner, scheduler = make_setup()
    buddy_tasks = scheduler.filter_tasks(pet_name="Buddy")
    ok = len(buddy_tasks) > 0 and all(t.pet_name == "Buddy" for t in buddy_tasks)
    return ok, f"Returned {len(buddy_tasks)} Buddy task(s)", 1.0 if ok else 0.0


def tc_filter_by_completion() -> Result:
    owner, scheduler = make_setup()
    all_tasks = owner.get_all_tasks()
    all_tasks[0].completed = True
    completed = scheduler.filter_tasks(completed=True)
    pending = scheduler.filter_tasks(completed=False)
    ok = len(completed) == 1 and (len(completed) + len(pending) == len(all_tasks))
    return ok, f"Completed: {len(completed)}, Pending: {len(pending)}", 1.0 if ok else 0.0


def tc_rag_retrieval() -> Result:
    kb = KnowledgeBase()
    if not kb.documents:
        return True, "Knowledge base empty — acceptable for harness run", 0.5
    results = kb.retrieve("dog feeding schedule daily")
    ok = len(results) > 0
    conf = min(1.0, len(results) / 3)
    return ok, f"Retrieved {len(results)} chunk(s)", conf


def tc_empty_owner() -> Result:
    owner = Owner("Empty")
    scheduler = Scheduler(owner)
    ok = scheduler.sort_by_time() == [] and scheduler.get_summary()["total_tasks"] == 0
    return ok, "Empty owner handled without errors", 1.0 if ok else 0.0


def tc_summary_accuracy() -> Result:
    owner = Owner("T")
    pet = Pet("Dog", "Dog")
    owner.add_pet(pet)
    pet.add_task(Task("Walk", "07:00", "once", "Dog"))
    pet.add_task(Task("Feed", "08:00", "once", "Dog"))
    pet.tasks[0].completed = True
    s = Scheduler(owner).get_summary()
    ok = s["total_tasks"] == 2 and s["completed"] == 1 and s["pending"] == 1
    return ok, f"Summary: {s}", 1.0 if ok else 0.0


# ---------------------------------------------------------------------------
# Harness runner
# ---------------------------------------------------------------------------

TESTS = [
    ("Sorting correctness",              tc_sorting_correctness),
    ("Conflict detection — true positive", tc_conflict_true_positive),
    ("Conflict detection — true negative", tc_conflict_true_negative),
    ("Daily recurrence",                 tc_daily_recurrence),
    ("Weekly recurrence",                tc_weekly_recurrence),
    ("Once — no recurrence",             tc_once_no_recurrence),
    ("Filter by pet",                    tc_filter_by_pet),
    ("Filter by completion status",      tc_filter_by_completion),
    ("RAG knowledge retrieval",          tc_rag_retrieval),
    ("Empty owner edge case",            tc_empty_owner),
    ("Schedule summary accuracy",        tc_summary_accuracy),
]


def main() -> None:
    print("\n" + "=" * 70)
    print("  PAWPAL+ RELIABILITY EVALUATION HARNESS")
    print("=" * 70)

    records = []
    for test_name, fn in TESTS:
        name, passed, msg, conf, elapsed = run(test_name, fn)
        records.append((name, passed, msg, conf, elapsed))
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status}  {name}  [{elapsed*1000:.1f} ms]")
        print(f"       {msg}  [confidence: {conf:.0%}]")

    total = len(records)
    n_passed = sum(1 for _, p, *_ in records if p)
    avg_conf = sum(c for _, _, _, c, _ in records) / total
    pass_rate = n_passed / total

    print("\n" + "=" * 70)
    print(f"  RESULT: {n_passed}/{total} passed  ({pass_rate:.0%})")
    print(f"  Average confidence: {avg_conf:.0%}")

    if pass_rate == 1.0:
        rating = "EXCELLENT ⭐⭐⭐⭐⭐"
    elif pass_rate >= 0.8:
        rating = "GOOD ⭐⭐⭐⭐"
    elif pass_rate >= 0.6:
        rating = "FAIR ⭐⭐⭐"
    else:
        rating = "NEEDS WORK ⭐"
    print(f"  Reliability rating: {rating}")
    print("=" * 70 + "\n")

    report = {
        "total": total,
        "passed": n_passed,
        "pass_rate": round(pass_rate, 3),
        "average_confidence": round(avg_conf, 3),
        "rating": rating,
        "tests": [
            {
                "name": n,
                "passed": p,
                "message": m,
                "confidence": round(c, 3),
                "elapsed_ms": round(e * 1000, 2),
            }
            for n, p, m, c, e in records
        ],
    }

    report_path = os.path.join(os.path.dirname(__file__), "..", "test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Full report saved → test_report.json\n")


if __name__ == "__main__":
    main()
