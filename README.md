# 🐾 PawPal+ AI: Smart Pet Care Management System

> **Applied AI System — Project 4**
> An extension of the original PawPal+ project from Module 2.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io)
[![Claude AI](https://img.shields.io/badge/Claude-Haiku%204.5-orange.svg)](https://anthropic.com)

---

## 📖 Original Project

**Original Project**: PawPal+ (Module 2 — OOP System Design)

The original PawPal+ was an object-oriented pet care scheduling system built around four Python classes — `Owner`, `Pet`, `Task`, and `Scheduler` — with a Streamlit UI for managing feeding, walking, and medication schedules. It supported task sorting, filtering by pet or completion status, recurring task management, and basic conflict detection.

---

## 🚀 What's New in PawPal+ AI

This version extends the original into a full **applied AI system** by adding three layers on top of the original OOP core:

| Feature | Description |
|---|---|
| **Agentic AI Workflow** | Claude-powered assistant that calls live tools (schedule, conflicts, pet info) before answering |
| **RAG (Retrieval-Augmented Generation)** | Local pet care knowledge base the agent searches for health/medication advice |
| **Test Harness** | Automated evaluation script with 11 predefined cases, confidence scoring, and JSON report |

---

## 🏗️ Architecture Overview

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Interface Layer                                    │
│  app.py (Streamlit)  ·  main.py (CLI demo)          │
└──────────────┬──────────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌─────────────────┐   ┌──────────────────────────────┐
│  Core Logic     │   │  AI Layer                    │
│  pawpal_system  │◄──│  ai_agent.py (PawPalAgent)   │
│  ─ Owner        │   │  · 5 Claude tool definitions │
│  ─ Pet          │   │  · Multi-step tool-use loop  │
│  ─ Task         │   └───────────┬──────────────────┘
│  ─ Scheduler    │               │
└─────────────────┘               ▼
                          ┌───────────────────┐
                          │  RAG Layer        │
                          │  rag_system.py    │
                          │  · 4 .md docs     │
                          │  · Keyword search │
                          └───────────────────┘
```

**Data flow:**
1. User actions in the UI create/update `Owner`, `Pet`, `Task` objects in memory.
2. AI questions route to `PawPalAgent.chat()`, which calls the Claude API.
3. Claude decides which tools to invoke (schedule lookup, conflict check, pet info, knowledge search).
4. Tool results are fed back to Claude, which synthesizes a final response.
5. For health/care questions, `KnowledgeBase.retrieve()` finds relevant chunks from local markdown docs before Claude responds.

See `assets/architecture.md` for the full Mermaid flowchart — paste into [mermaid.live](https://mermaid.live) to render.

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.9 or higher
- An [Anthropic API key](https://console.anthropic.com/) (free tier works)

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
```bash
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows
set ANTHROPIC_API_KEY=sk-ant-...
```

Or create a `.env` file (copy from `.env.example`) — the app loads it automatically via `python-dotenv`.

### 4. Run the CLI demo
```bash
python main.py
```

### 5. Launch the Streamlit app
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### 6. Run tests
```bash
# Unit tests
python -m pytest tests/test_pawpal.py -v

# Evaluation harness (no API key needed)
python tests/test_harness.py
```

---

## 💬 Sample Interactions

### CLI — Scheduling system
```
TODAY'S SCHEDULE — sorted by time
  ⏳ [07:00] 🔴 Morning walk (Buddy) [daily]
  ⏳ [07:00] 🔴 Vet appointment (Buddy) [once]
  ⏳ [07:30] 🔴 Breakfast (Buddy) [daily]
  ⏳ [08:00] 🔴 Breakfast (Whiskers) [daily]
  ...

CONFLICT DETECTION
  ⚠️ Conflict: 'Vet appointment' and 'Morning walk' both at 07:00 for Buddy
```

### AI Assistant — Schedule query
> **User:** What does today's schedule look like?
>
> **PawPal AI:** Here's today's schedule for your pets, sorted by time:
> - 7:00 AM 🔴 Morning walk — Buddy (daily)
> - 7:30 AM 🔴 Breakfast — Buddy (daily)
> - 8:00 AM 🔴 Breakfast — Whiskers (daily)
> - 9:00 AM 🔴 Heartworm tablet — Buddy (weekly)
> - 6:00 PM 🟡 Evening walk — Buddy (daily)
>
> ⚠️ Heads up: Buddy has a scheduling conflict at 7:00 AM — both "Morning walk" and "Vet appointment" are scheduled then. You may want to move the vet appointment.

### AI Assistant — Care advice (RAG)
> **User:** How often should I give Buddy his heartworm medication?
>
> **PawPal AI:** Heartworm prevention for dogs should be given **monthly**, on the same calendar day each month. Products like Heartgard or Interceptor require a prescription and should be given year-round, ideally with food to reduce any stomach upset. Buddy currently has his heartworm tablet scheduled weekly — you may want to adjust that to monthly for most standard prevention products. Always confirm the schedule with your vet.

### AI Assistant — Conflict resolution
> **User:** Are there any conflicts I should fix?
>
> **PawPal AI:** Yes! Buddy has a conflict at **7:00 AM** — both "Morning walk" and "Vet appointment" are scheduled at the same time. I'd suggest moving the vet appointment to a different time slot, or rescheduling the morning walk to 6:30 AM on that day.

---

## ✨ Features

- **Sorted daily schedule** — tasks displayed in chronological order using `sorted()` with a `HH:MM` key.
- **Conflict warnings** — O(n) dictionary scan flags any two tasks at the exact same time for the same pet.
- **Recurring tasks** — completing a daily/weekly task automatically creates the next occurrence using `timedelta`.
- **Filter by pet or status** — view only Buddy's tasks, or only pending tasks across all pets.
- **AI agentic assistant** — Claude Haiku with 5 tools; performs multi-step reasoning before responding.
- **Retrieval-Augmented Generation** — keyword-based search over 4 pet care documents for grounded health advice.
- **Priority levels** — High 🔴 / Medium 🟡 / Low 🟢 with visual badges in the UI.

---

## 🎨 Smarter Scheduling

The `Scheduler` class implements four algorithms beyond the original project:

| Algorithm | Implementation | Complexity |
|---|---|---|
| Sort by time | `sorted()` with lambda key on `HH:MM` strings | O(n log n) |
| Filter tasks | List comprehensions with optional kwargs | O(n) |
| Conflict detection | Dictionary keyed by `(pet_name, time)` | O(n) |
| Recurring tasks | `timedelta(days=1)` or `timedelta(weeks=1)` on `mark_complete()` | O(1) per task |

**Tradeoff**: Conflict detection flags only exact time matches, not overlapping durations. Implementing duration-aware overlap detection would require storing task end times and comparing time intervals — out of scope for this project but a clear next step.

---

## 🧪 Testing PawPal+

### Unit tests
```bash
python -m pytest tests/test_pawpal.py -v
```
20 tests covering: task completion, recurrence, pet CRUD, owner lookup, sorting, filtering, conflict detection, edge cases (empty pets, once-frequency tasks).

### Evaluation harness
```bash
python tests/test_harness.py
```
11 predefined test cases with confidence scoring. Generates `test_report.json` with full results.

**Results summary**: 11/11 tests pass · Average confidence: 97% · Rating: EXCELLENT ⭐⭐⭐⭐⭐

**Confidence level**: ⭐⭐⭐⭐⭐ — All core behaviors verified. The one known limitation is that conflict detection only handles exact time matches, not overlapping task windows.

---

## 🤔 Design Decisions

**Why Claude tool use instead of a single prompt?**
Injecting the full schedule as a string into the system prompt would make responses stale the moment a task changes. Tool use lets Claude fetch fresh data on demand and reason about multiple data sources in one turn.

**Why keyword-based RAG instead of vector embeddings?**
A student project running locally doesn't need a vector database. Keyword overlap is fast, requires no external dependencies, and performs well for the narrow pet care domain where queries and documents share vocabulary. The tradeoff: it won't handle synonyms or paraphrases well (e.g., "give meds" won't match "administer medications").

**Why `date` objects instead of `datetime`?**
Tasks are scheduled at a time-of-day that repeats across days, not at a specific calendar moment. Storing `date` + `time` string separately keeps the model simple and makes recurring task scheduling (`due_date + timedelta`) straightforward without timezone complexity.

**Why no persistent storage?**
Keeping state in `st.session_state` avoids serialization complexity. A future enhancement (see `Optional Extensions`) would add `save_to_json()` / `load_from_json()` methods to `Owner`.

---

## 🔍 Reflection and Ethics

### Limitations and biases
1. **Static knowledge base** — The RAG documents are manually curated and won't reflect updated veterinary guidelines or breed-specific needs.
2. **Shallow conflict detection** — Only exact time matches are flagged; a 30-minute walk at 7:00 and a task at 7:15 would not conflict in the current model.
3. **No persistent storage** — All data is lost on app restart.
4. **Single-owner model** — The system assumes one household; multi-user or vet-clinic use cases would need authentication.

### Misuse potential and mitigations
The AI assistant could be prompted to give harmful medical advice (e.g., "what's a safe ibuprofen dose for my dog?"). Mitigation: the system prompt constrains the agent to scheduling and general care; the knowledge base does not contain prescription dosing information; the agent is instructed to direct users to a veterinarian for clinical questions.

### Surprises during testing
The agent occasionally called `search_pet_care_knowledge` for scheduling questions that didn't need it (e.g., "show me today's schedule"), adding minor latency. The fix would be tightening the tool description with explicit "use this only for health/care advice" guidance.

### AI collaboration
- **Helpful suggestion**: Using `anthropic`'s native tool-use API (rather than manual JSON parsing) made the agentic loop much cleaner — the SDK handles message formatting automatically.
- **Flawed suggestion**: An early AI draft of `detect_conflicts()` used nested O(n²) loops. Replaced with a single-pass dictionary approach that is both faster and more readable.

---

## 📁 Project Structure

```
pawpal-ai/
├── pawpal_system.py          # Core OOP: Owner, Pet, Task, Scheduler
├── ai_agent.py               # Claude-powered agentic assistant
├── rag_system.py             # Keyword-based RAG over local docs
├── app.py                    # Streamlit UI
├── main.py                   # CLI demo script
├── requirements.txt
├── .env.example
├── knowledge_base/
│   ├── dog_care.md
│   ├── cat_care.md
│   ├── general_pet_care.md
│   └── medications.md
├── tests/
│   ├── test_pawpal.py        # 20 pytest unit tests
│   └── test_harness.py       # 11-case evaluation harness
└── assets/
    └── architecture.md       # Mermaid diagram source
```

---

## 🎥 Demo Video

[Loom walkthrough link — add after recording]

---

## 💼 Portfolio Reflection

> Building PawPal+ AI taught me that the most important skill in applied AI isn't knowing which model to use — it's knowing how to structure the *interface* between your application logic and the model. By keeping the OOP core clean and exposing it through well-defined tools, the Claude agent could reason about real, live data rather than hallucinating. This project demonstrates my ability to design modular systems, integrate production AI APIs responsibly, and verify reliability through structured evaluation — skills I'd bring to any AI engineering role.
