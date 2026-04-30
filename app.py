"""Streamlit UI for PawPal+ AI — pet care management with an agentic assistant."""

import logging
from datetime import date

import streamlit as st

from ai_agent import PawPalAgent
from pawpal_system import Owner, Pet, Scheduler, Task
from rag_system import KnowledgeBase

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="PawPal+ AI", page_icon="🐾", layout="wide")


# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------

def _init_state() -> None:
    if "owner" not in st.session_state:
        st.session_state.owner = Owner("My Household")
    if "kb" not in st.session_state:
        st.session_state.kb = KnowledgeBase()
    if "messages" not in st.session_state:
        st.session_state.messages = []


_init_state()

owner: Owner = st.session_state.owner
kb: KnowledgeBase = st.session_state.kb

# Rebuild Scheduler and Agent each run so they always see current owner state
scheduler = Scheduler(owner)
agent = PawPalAgent(owner, kb)
# Preserve existing conversation history across reruns
agent.history = st.session_state.get("agent_history", [])


# ---------------------------------------------------------------------------
# Page header + proactive alerts
# ---------------------------------------------------------------------------

st.title("🐾 PawPal+ AI")
st.caption("Smart Pet Care Management · Powered by Claude")

for alert in agent.get_proactive_alerts():
    if "Conflict" in alert or "⚠️" in alert:
        st.warning(alert)
    elif "🔴" in alert:
        st.error(alert)
    else:
        st.success(alert)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_dash, tab_pet, tab_task, tab_ai = st.tabs(
    ["📅 Dashboard", "🐶 Add Pet", "📝 Add Task", "🤖 AI Assistant"]
)


# ── Tab 1: Dashboard ────────────────────────────────────────────────────────
with tab_dash:
    st.subheader("Today's Schedule")

    left, right = st.columns([3, 1])

    with left:
        filter_pet = st.selectbox(
            "Filter by pet", ["All Pets"] + [p.name for p in owner.pets]
        )
        show_done = st.checkbox("Show completed tasks", value=False)

        if filter_pet == "All Pets":
            tasks = scheduler.sort_by_time()
        else:
            tasks = scheduler.sort_by_time(scheduler.filter_tasks(pet_name=filter_pet))

        if not show_done:
            tasks = [t for t in tasks if not t.completed]

        if not tasks:
            st.info("No tasks to display. Add pets and tasks to get started!")
        else:
            for task in tasks:
                c_btn, c_info, c_badge = st.columns([0.5, 4, 0.6])
                with c_btn:
                    if not task.completed and st.button("✅", key=f"done_{task.task_id}"):
                        scheduler.mark_task_complete(task.task_id)
                        st.rerun()
                with c_info:
                    label = f"**{task.time}** — {task.description} *(for {task.pet_name})*"
                    if task.completed:
                        label = f"~~{label}~~"
                    st.markdown(label)
                    st.caption(f"Frequency: {task.frequency} · Due: {task.due_date} · Priority: {task.priority}")
                with c_badge:
                    st.write({"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪"))

        # Conflict warnings inline
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.markdown("---")
            for c in conflicts:
                st.warning(c)

    with right:
        st.subheader("Summary")
        summary = scheduler.get_summary()
        st.metric("Pets", summary["pets"])
        st.metric("Total Tasks", summary["total_tasks"])
        st.metric("Pending", summary["pending"])
        st.metric("Completed", summary["completed"])
        if summary["conflicts"]:
            st.metric("Conflicts ⚠️", summary["conflicts"])
        else:
            st.metric("Conflicts", 0)

        if owner.pets:
            st.markdown("---")
            st.subheader("Pets")
            for p in owner.pets:
                pending_n = len(p.get_pending_tasks())
                st.markdown(f"**{p.name}** — {p.species}")
                st.caption(f"{pending_n} pending task(s)")


# ── Tab 2: Add Pet ───────────────────────────────────────────────────────────
with tab_pet:
    st.subheader("Add a New Pet")
    with st.form("form_add_pet"):
        p_name = st.text_input("Pet Name *")
        p_species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Rabbit", "Fish", "Other"])
        p_breed = st.text_input("Breed (optional)")
        p_age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)
        submitted = st.form_submit_button("Add Pet")

    if submitted:
        p_name = p_name.strip()
        if not p_name:
            st.error("Pet name is required.")
        elif owner.get_pet(p_name):
            st.error(f"A pet named '{p_name}' already exists.")
        else:
            owner.add_pet(Pet(p_name, p_species, p_breed, int(p_age)))
            st.success(f"🐾 {p_name} added!")
            st.rerun()


# ── Tab 3: Add Task ──────────────────────────────────────────────────────────
with tab_task:
    st.subheader("Schedule a New Task")
    if not owner.pets:
        st.warning("Add a pet first before scheduling tasks.")
    else:
        with st.form("form_add_task"):
            t_pet = st.selectbox("Pet", [p.name for p in owner.pets])
            t_desc = st.text_input("Task Description *", placeholder="e.g., Morning walk")
            t_time = st.time_input("Time")
            t_freq = st.selectbox("Frequency", ["once", "daily", "weekly"])
            t_prio = st.selectbox("Priority", ["low", "medium", "high"])
            t_date = st.date_input("Due Date", value=date.today())
            submitted = st.form_submit_button("Schedule Task")

        if submitted:
            t_desc = t_desc.strip()
            if not t_desc:
                st.error("Task description is required.")
            else:
                new_task = Task(
                    description=t_desc,
                    time=t_time.strftime("%H:%M"),
                    frequency=t_freq,
                    pet_name=t_pet,
                    priority=t_prio,
                    due_date=t_date,
                )
                owner.get_pet(t_pet).add_task(new_task)
                fresh_conflicts = Scheduler(owner).detect_conflicts()
                if fresh_conflicts:
                    for c in fresh_conflicts:
                        st.warning(c)
                else:
                    st.success(f"Task '{t_desc}' scheduled for {t_pet} at {t_time.strftime('%H:%M')}!")
                st.rerun()


# ── Tab 4: AI Assistant ──────────────────────────────────────────────────────
with tab_ai:
    st.subheader("🤖 PawPal AI Assistant")
    st.caption("Ask about schedules, conflicts, feeding guidelines, medications, and more.")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask PawPal AI…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                reply = agent.chat(prompt)
            st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.agent_history = agent.history

    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.session_state.agent_history = []
        st.rerun()
