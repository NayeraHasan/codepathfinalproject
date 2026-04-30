# PawPal+ AI — Project Reflection

---

## 1. System Design

### 1a. Initial Design

The system is organized into four core classes with clearly separated responsibilities:

- **Task (dataclass)** — A single pet care activity. Holds `description`, `time` (HH:MM string), `frequency` (once/daily/weekly), `pet_name`, `priority`, `completed`, `due_date`, and a UUID `task_id`. Using a Python dataclass eliminates boilerplate and makes the model readable at a glance.

- **Pet** — Stores pet metadata (name, species, breed, age) and owns a `List[Task]`. Responsible for adding, removing, and querying only its own tasks. It knows nothing about scheduling algorithms.

- **Owner** — The top-level aggregate: holds a `List[Pet]` and provides `get_all_tasks()` to flatten all tasks for the Scheduler. Acts as the single source of truth for the application's data.

- **Scheduler** — The algorithmic layer. Takes an `Owner` as a dependency and implements sorting, filtering, conflict detection, recurring task management, and daily schedule retrieval. Intentionally stateless — it reads from `Owner` but never modifies it directly except through `mark_task_complete()`.

For Project 4, two new modules extend the original:
- **KnowledgeBase** (`rag_system.py`) — Loads markdown documents and provides keyword-based retrieval. Decoupled from the AI agent so it can be tested independently.
- **PawPalAgent** (`ai_agent.py`) — A Claude-powered agent that defines five tools mapping to Scheduler methods and KnowledgeBase queries. Uses the Anthropic tool-use API to perform multi-step reasoning before responding.

### 1b. Design Changes

One key change from the initial design: `get_todays_schedule()` was added to `Scheduler` to filter tasks by `due_date == date.today()`. The original design sorted all tasks regardless of date, which made the daily dashboard show future and past tasks mixed together — not useful for a pet owner checking today's to-do list.

A second change: the `PawPalAgent` was initially designed to cache the `Scheduler` object permanently. This broke when new pets or tasks were added after agent initialization. The fix was to always reconstruct the `Scheduler` from the current `Owner` state on each app run, ensuring the agent always works with live data.

---

## 2. Algorithmic Layer

### 2a. Algorithms Implemented

| Algorithm | Implementation | Notes |
|---|---|---|
| **Sort by time** | `sorted(tasks, key=lambda t: t.time)` | Works because HH:MM zero-padded strings compare lexicographically |
| **Filter tasks** | List comprehensions with optional kwargs | Supports pet_name and completed filters independently or combined |
| **Conflict detection** | Single-pass dictionary keyed by `(pet_name.lower(), time)` | O(n), flags first-occurrence duplicates |
| **Recurring tasks** | `mark_complete()` returns new Task with `due_date + timedelta` | daily → +1 day, weekly → +7 days, once → None |

### 2b. Tradeoffs

**Conflict detection** only flags exact time-string matches. A 30-minute morning walk starting at 07:00 would not conflict with a task at 07:15, even though both cannot realistically happen simultaneously. Implementing overlap-aware detection would require storing task durations and comparing time intervals — this adds complexity (converting strings to `datetime` objects, interval arithmetic) without proportional benefit for the typical use case where tasks are point-in-time reminders rather than calendar blocks.

**Sorting** uses string comparison on `HH:MM` rather than converting to `time` objects. This is intentional: the format is enforced at input (Streamlit's `time_input` always produces zero-padded strings), so string comparison is correct and avoids unnecessary parsing overhead.

---

## 3. AI Collaboration and Reflection

### Most Effective Approach

The tool-use architecture was the single biggest design decision. By defining five concrete tools that map directly to Scheduler methods and RAG retrieval, the agent is grounded in real, live data. Claude can fetch exactly the context it needs for each question rather than receiving a dumped context string that may be stale or irrelevant.

The RAG component uses simple keyword overlap instead of vector embeddings. For a domain as narrow as pet care, vocabulary overlap between user queries and knowledge base documents is high enough that TF-IDF-style matching works well. This avoids needing `sentence-transformers`, a GPU, or a vector database — making setup a single `pip install` command.

### One Instance Where AI Helped

When structuring the agentic conversation loop, an early approach called the Claude API once and injected the full schedule into the system prompt. Switching to the proper tool-use pattern — letting Claude decide *which* data to retrieve and *when* — produced more focused responses, reduced unnecessary context, and enabled multi-hop reasoning (e.g., "check the schedule, detect conflicts, then explain what to do").

### One Instance Where AI Suggestion Was Flawed

An early AI-generated draft of `detect_conflicts()` used nested loops:
```python
for i in range(len(tasks)):
    for j in range(i + 1, len(tasks)):
        if tasks[i].time == tasks[j].time and tasks[i].pet_name == tasks[j].pet_name:
            ...
```
This is O(n²) and generates duplicate warnings for the same conflict when more than two tasks share a time slot. It was replaced with the single-pass dictionary approach, which is O(n), generates one warning per conflict, and is easier to read.

### Limitations and Ethical Considerations

**Limitations:**
- The knowledge base is static — it won't reflect new veterinary guidelines without manual updates.
- Conflict detection handles only exact time matches, not overlapping durations.
- No authentication or multi-user support; designed for a single household.
- No data persistence between sessions — all state lives in `st.session_state`.

**Could it be misused?**
A user could prompt the AI for specific medication dosing (e.g., "what dose of phenobarbital for a 20kg dog?"). The system mitigates this by: (1) a system prompt that directs clinical questions to a veterinarian, (2) a knowledge base that deliberately omits prescription dosing, and (3) responses that cite general guidelines only. The model could still be jailbroken with adversarial prompting — a production system would add input filtering.

**What surprised me during reliability testing:**
The agent called `search_pet_care_knowledge` on pure scheduling questions that didn't require it. This is a behavior where the model is being cautious and comprehensive, but it adds unnecessary latency and occasionally returns tangential pet care content alongside schedule information. The fix is in the tool description — being explicit about *when not* to use a tool is as important as describing what it does.

### What This Project Taught Me

Being the "lead architect" when collaborating with AI means the AI handles implementation details but the human must own the *structure* — which abstractions to create, where to draw boundaries between modules, which tradeoffs to accept. The best AI-assisted code came from clear, specific prompts that described what I wanted and why, not just what to write. The cleaner the design specification, the cleaner the AI output.
