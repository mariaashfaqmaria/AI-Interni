"""LangGraph workflows for project Q&A and project planning."""
import logging
import re
from datetime import date
from functools import lru_cache
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from ..services import planner, retriever
from ..services.seed import PROJECTS as SEED_PROJECTS, search_seed_projects
from ..services.documents import store as local_store
from ..services.llm import get_llm, structured, text_of

log = logging.getLogger(__name__)

CHAT_ROLE = "You are Project Scheduling Chatbot, a practical software-project assistant."
DOC_TASK = "Answer the user's question using the relevant approved project information."
DOC_INSTRUCTIONS = (
    "Use retrieved project content as the factual source for project title, domain, idea, and listed features. "
    "Never invent project facts or claim that recommendations appear in the source. Clearly label any added "
    "engineering suggestions as Recommendations. Answer only what the user asked. Be concise and professional: "
    "normally use 1-3 short paragraphs or up to 5 focused bullets. When structure helps, use concise Markdown headings (##) and hyphen bullets. "
    "Avoid repetition, generic introductions, unnecessary conclusions, and lengthy background. "
    "If the source does not contain the requested detail, state that briefly and ask one focused clarification. "
    "Start an in-scope answer with the source label supplied in context. Do not mention PDF page numbers."
)
GENERAL_TASK = "Answer the user's general software engineering, AI, or project-development question."
GENERAL_INSTRUCTIONS = (
    "Give accurate, practical advice and do not claim it came from the project catalogue. "
    "Answer only the question asked. Be concise, professional, and directly useful: normally 1-3 short paragraphs "
    "or up to 5 focused bullets. When structure helps, use concise Markdown headings (##) and hyphen bullets. "
    "Avoid repetition, filler, and lengthy "
    "background. If the question is outside software engineering, software projects, AI architecture, development, "
    "testing, deployment, or project planning, briefly explain that this assistant focuses on those topics."
)
MIN_DOCUMENT_MATCH = 0.12

APPROVED_DOMAINS = [
    "Healthcare", "Education", "Finance", "Agriculture", "E-commerce",
    "Transportation", "Real Estate", "Entertainment", "Cybersecurity", "Environment",
    "Manufacturing", "Tourism", "Sports", "Food Service", "Government", "Energy",
]


class ChatState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    mode: str
    docs: list[dict]
    sources: list[dict]
    in_scope: bool
    action: str
    selected_project: dict
    project_found: bool
    plan_result: dict


def _last_question(state: ChatState) -> str:
    messages = state.get("messages", [])
    return text_of(messages[-1].content) if messages else ""


def _recent_context(state: ChatState) -> str:
    messages = state.get("messages", [])[-10:-1]
    return "\n".join(text_of(message.content) for message in messages)


class ActionClassification(BaseModel):
    action: Literal["get_project_details", "generate_plan", "document_question", "general_chat"]


def _is_plan_request(question: str) -> bool:
    text = question.casefold()
    plan_words = r"(?:project\s+)?(?:plan|roadmap|timeline|schedule)"
    explicit_verbs = r"(?:generate|create|make|prepare|build|design|draft|provide)"
    explicit_request = re.search(
        rf"\b{explicit_verbs}\b.{{0,70}}\b{plan_words}\b", text
    )
    need_or_want = re.search(
        rf"\b(?:need|want)\b.{{0,18}}\b(?:a|the|my|our)\s+{plan_words}\b", text
    )
    imperative = re.search(
        r"^\s*(?:plan|schedule|roadmap)\s+(?:for|out|the|this|my|our)\b", text
    )
    task_scheduling = re.search(
        r"\b(?:schedule|organize)\s+(?:the\s+)?(?:project\s+)?tasks\b", text
    )
    timed_plan = re.search(
        rf"^\s*{plan_words}\b.{{0,80}}\b(?:in|within|over)\s+\d+\s+days?\b", text
    )
    return bool(explicit_request or need_or_want or imperative or task_scheduling or timed_plan)

def _is_greeting_only(question: str) -> bool:
    """Recognize standalone greetings without intercepting real questions."""
    normalized = re.sub(r"[.!?,\s]+", " ", question.casefold()).strip()
    return bool(re.fullmatch(
        r"(?:hi|hello|hey|hiya|good morning|good afternoon|good evening|"
        r"how are you|how are you doing|what's up|whats up|"
        r"good to see you|greetings)(?: there| everyone)?",
        normalized,
    ))


def _references_catalogue_project(question: str) -> bool:
    """Return True only for a reasonably clear reference to the approved catalogue."""
    normalized = question.casefold()
    catalogue = _catalogue_items()

    # Explicit project titles are the strongest signal.
    if any(
        title and title.casefold() in normalized
        for title in (str(item.get("project_title", "")) for item in catalogue)
    ):
        return True

    # Semantic matching is only attempted when the user signals project/document intent.
    project_cues = ("project", "projects", "document", "catalogue", "catalog")
    if not any(cue in normalized for cue in project_cues):
        return False

    try:
        hits = retriever.search(question, k=1)
        return bool(hits and float(hits[0].get("match", 0)) >= 0.50)
    except Exception:
        log.exception("Could not check whether the question refers to a catalogue project")
        return False


def greeting_response(_: ChatState) -> dict:
    """A deterministic greeting works in either answer mode and needs no retrieval."""
    return {
        "messages": [AIMessage(content=(
            "Hello! I'm your Project Scheduling Assistant. "
            "I can help with your approved project document or provide general "
            "software-development and AI project guidance. What would you like to work on?"
        ))],
        "sources": [],
    }


def project_mode_redirect(state: ChatState) -> dict:
    """Explain which answer mode should be used without mixing source types."""
    if state.get("mode") == "General advice":
        message = (
            "This question appears to relate to one of your 16 approved projects. "
            "Please switch to **From document** to get an answer grounded in your project data."
        )
    else:
        message = (
            "I could not find this project or information in your 16 approved projects. "
            "Please switch to **General advice** for an LLM-generated answer based on general knowledge."
        )
    return {"messages": [AIMessage(content=message)], "sources": []}


def classify_action(state: ChatState) -> dict:
    """Route greetings and the two answer modes before doing any retrieval."""
    question = _last_question(state)
    mode = state.get("mode", "From document")

    # Greetings are valid in both modes and should never enter RAG retrieval.
    if _is_greeting_only(question):
        return {"action": "greeting"}

    if mode == "General advice":
        if _references_catalogue_project(question):
            return {"action": "project_mode_redirect"}
        return {"action": "general_chat"}

    normalized = question.casefold()

    if _is_plan_request(question):
        return {"action": "generate_plan"}

    if any(item.get("project_title", "").casefold() in normalized
           for item in _catalogue_items()):
        return {"action": "get_project_details"}

    retrieval_words = (
        "get", "find", "show", "suggest", "recommend", "select", "choose",
        "tell me about", "explain", "describe", "overview", "details",
    )
    has_project_reference = "project" in normalized or any(
        domain.casefold() in normalized for domain in APPROVED_DOMAINS
    )
    if has_project_reference and any(word in normalized for word in retrieval_words):
        return {"action": "get_project_details"}

    detail_words = ("project details", "project overview", "project features", "what is ")
    if any(word in normalized for word in detail_words) and (
        "project" in normalized or any(d.casefold() in normalized for d in APPROVED_DOMAINS)
    ):
        return {"action": "get_project_details"}

    decision = structured(
        ActionClassification,
        "Classify intent. generate_plan ONLY for an explicit request for a project plan, "
        "roadmap, timeline, or task schedule. get_project_details for a request to find, "
        "explain, describe, or retrieve a particular project. document_question for questions "
        "about information in the approved project catalogue. Do not answer.",
        f"User message: {question}",
    )
    if decision and decision.action in ("get_project_details", "generate_plan", "document_question"):
        return {"action": decision.action}

    # In document mode, a general software question must receive the mode-switch message.
    return {"action": "document_question"}


def action_route(state: ChatState) -> str:
    return state.get("action", "document_question")


def _catalogue_items() -> list[dict]:
    items = [dict(item) for item in getattr(local_store, "projects", [])]
    for name, description, tags, days in SEED_PROJECTS:
        items.append({
            "project_id": name.lower().replace(" ", "-"),
            "project_title": name,
            "domain": tags[0],
            "application_type": "Web application",
            "source_type": "seeds file",
            "source": "seed catalog",
            "match": 1.0,
            "suggested_days": days,
            "text": (
                f"Project: {name}\nDescription: {description}\n"
                f"Domain: {tags[0]}\nLevel: {tags[1]}\nSuggested duration: {days} days"
            ),
        })
    return items


def get_project(state: ChatState) -> dict:
    """Resolve one exact approved project before either explanation or planning."""
    question = _last_question(state)
    context = _recent_context(state)
    combined = f"{question}\n{context}".strip()
    catalogue = _catalogue_items()
    normalized = combined.casefold()

    # Exact title match has priority over vector similarity.
    exact = [
        item for item in catalogue
        if item.get("project_title", "").casefold() in normalized
    ]
    selected = exact[0] if exact else None

    # A domain request maps to its single approved project.
    if selected is None:
        domain_matches = [
            item for item in catalogue
            if str(item.get("domain", "")).casefold() in normalized
        ]
        if len(domain_matches) == 1:
            selected = domain_matches[0]

    # Semantic retrieval is used only when the user supplied a specific project
    # clue, and the result must clear a conservative relevance threshold.
    if selected is None:
        hits = retriever.search(combined, k=16)
        hits = sorted(hits, key=lambda item: float(item.get("match", 0)), reverse=True)
        if hits and float(hits[0].get("match", 0)) >= 0.40:
            title = str(hits[0].get("project_title", "")).casefold()
            # Never promote an arbitrary vector hit: only one of the approved
            # catalogue entries may be selected.
            selected = next(
                (item for item in catalogue
                 if item.get("project_title", "").casefold() == title),
                None,
            )

    if selected is None:
        return {
            "project_found": False,
            "selected_project": {},
            "docs": [],
            "sources": [],
            "in_scope": False,
        }

    selected = dict(selected)
    selected.setdefault("source_type", "document file")
    selected.setdefault("match", 1.0)
    selected.setdefault("text", "")
    source = {
        "project_id": selected.get("project_id"),
        "project_title": selected.get("project_title"),
        "source_type": selected.get("source_type", "document file"),
        "match": selected.get("match", 1.0),
    }
    return {
        "project_found": True,
        "selected_project": selected,
        "docs": [selected],
        "sources": [source],
        "in_scope": True,
    }


def after_get_project(state: ChatState) -> str:
    if not state.get("project_found"):
        return "not_found"
    if state.get("action") == "generate_plan":
        return "generate_plan"
    return "generate_project_answer"


def generate_project_answer(state: ChatState) -> dict:
    return generate_chat_answer(state)


def generate_plan_action(state: ChatState) -> dict:
    """Generate a plan only after get_project has resolved an approved project."""
    selected = state.get("selected_project") or {}
    if not selected.get("project_title"):
        return {
            "messages": [AIMessage(content="Please select one approved project before requesting a plan.")],
            "sources": [],
            "plan_result": {},
        }

    question = _last_question(state)
    day_match = re.search(r"\b(\d{1,3})\s*(?:working\s+)?days?\b", question, re.I)
    hour_match = re.search(r"\b(\d{1,2})\s*hours?\s*(?:per\s+day|/\s*day)?\b", question, re.I)
    default_days = int(selected.get("suggested_days", 14) or 14)
    days = min(60, max(1, int(day_match.group(1)))) if day_match else min(60, max(1, default_days))
    hours = min(12, max(1, int(hour_match.group(1)))) if hour_match else 2
    project_name = selected["project_title"]

    plan_state = get_planner_graph().invoke({
        "project": project_name,
        "selected_project": selected,
        "start": date.today(),
        "days": days,
        "hours": hours,
        "beginner": True,
        "weekends_off": bool(
            re.search(r"\b(?:working days?|weekends off|weekdays only)\b", question, re.I)
        ),
    })
    plan_content = planner.assemble(plan_state)
    lines = [
        f"Here is your {days}-day project plan for {project_name}.",
        "",
        f"Objective: {plan_content['objective']}",
        "",
        "Suggested architecture:",
        *[f"- {item}" for item in plan_content["architecture"]],
        "",
        "Daily implementation tasks:",
    ]
    for task in plan_content["tasks"]:
        lines.append(
            f"- {task['date']}: {task['title']} — {task.get('description', '')} "
            f"({task['time']}, {task['duration']})"
        )
    lines.extend(["", "Completion checklist:"])
    for phase, items in plan_content["checklist"].items():
        lines.append(f"- {phase}: " + "; ".join(items))
    return {
        "messages": [AIMessage(content="\n".join(lines))],
        "sources": state.get("sources", []),
        "plan_result": plan_content,
    }


def retrieve_document(state: ChatState) -> dict:
    question = _last_question(state)
    hits = retriever.search(question, k=16)
    approved_titles = {
        str(item.get("project_title", "")).casefold()
        for item in _catalogue_items()
        if item.get("project_title")
    }
    # Restrict RAG context to the 16 approved catalogue projects.
    hits = [
        hit for hit in hits
        if str(hit.get("project_title", "")).casefold() in approved_titles
        and float(hit.get("match", 0)) >= MIN_DOCUMENT_MATCH
    ][:4]
    sources = [{
        "project_id": hit.get("project_id"),
        "project_title": hit.get("project_title"),
        "source_type": hit.get("source_type", "document file"),
        "match": hit.get("match", 0),
    } for hit in hits]
    return {"docs": hits, "sources": sources, "in_scope": bool(hits)}


def general_advice(state: ChatState) -> dict:
    return {"docs": [], "sources": [], "in_scope": True}


def generate_chat_answer(state: ChatState) -> dict:
    question = _last_question(state)
    mode = state.get("mode", "From document")
    llm = get_llm()
    history = state.get("messages", [])[-11:-1]

    if mode != "From document":
        if not llm:
            answer = "General advice mode requires OPENROUTER_API_KEY in the backend .env file."
        else:
            system = (
                f"ROLE: {CHAT_ROLE}\nTASK: {GENERAL_TASK}\nINSTRUCTIONS: {GENERAL_INSTRUCTIONS}\n"
                f"QUESTION: {question}\nANSWER:"
            )
            try:
                answer = text_of(llm.invoke([
                    SystemMessage(content=system), *history, HumanMessage(content=question)
                ]).content)
            except Exception:
                log.exception("General answer failed")
                answer = "Sorry, the language model is unavailable right now. Please try again."
        return {"messages": [AIMessage(content=answer)]}

    docs = state.get("docs", [])
    if not docs:
        return project_mode_redirect(state)
    context = "\n\n".join(
        f"PROJECT METADATA: project_id={doc.get('project_id')}; "
        f"title={doc.get('project_title')}; domain={doc.get('domain')}; "
        f"application_type={doc.get('application_type')}; source={doc.get('source_type', 'document file')}.\n"
        f"PROJECT CONTENT:\n{doc.get('text', '')[:6500]}"
        for doc in docs
    )
    source_label = docs[0].get("source_type", "document file")
    if not llm:
        answer = local_store.extractive_answer(question, docs)
        if not answer.startswith("Out of scope"):
            answer = f"Source: from {source_label}.\n" + answer
        return {"messages": [AIMessage(content=answer)]}

    prompt = (
        f"ROLE: {CHAT_ROLE}\nTASK: {DOC_TASK}\nINSTRUCTIONS: {DOC_INSTRUCTIONS}\n"
        f"RETRIEVED PROJECTS:\n{context}\nQUESTION: {question}\nANSWER:"
    )
    try:
        answer = text_of(llm.invoke([
            SystemMessage(content=prompt), *history, HumanMessage(content=question)
        ]).content)
        if answer.lower().startswith("source:"):
            answer = answer.split("\n", 1)[1] if "\n" in answer else ""
        answer = f"Source: from {source_label}.\n{answer}".rstrip()
    except Exception:
        log.exception("Document-grounded answer failed")
        answer = "I found relevant project information, but the language model is unavailable right now. Please try again."
    return {"messages": [AIMessage(content=answer)]}


@lru_cache
def get_checkpointer() -> MemorySaver:
    return MemorySaver()


@lru_cache
def get_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("classify_action", classify_action)
    graph.add_node("greeting", greeting_response)
    graph.add_node("project_mode_redirect", project_mode_redirect)
    graph.add_node("get_project", get_project)
    graph.add_node("generate_project_answer", generate_project_answer)
    graph.add_node("generate_plan", generate_plan_action)
    graph.add_node("project_not_found", project_mode_redirect)
    graph.add_node("retrieve_document", retrieve_document)
    graph.add_node("general_advice", general_advice)
    graph.add_node("generate", generate_chat_answer)

    graph.add_edge(START, "classify_action")
    graph.add_conditional_edges(
        "classify_action",
        action_route,
        {
            "greeting": "greeting",
            "project_mode_redirect": "project_mode_redirect",
            "get_project_details": "get_project",
            "generate_plan": "get_project",
            "document_question": "retrieve_document",
            "general_chat": "general_advice",
        },
    )
    graph.add_conditional_edges(
        "get_project",
        after_get_project,
        {
            "generate_project_answer": "generate_project_answer",
            "generate_plan": "generate_plan",
            "not_found": "project_not_found",
        },
    )
    graph.add_edge("greeting", END)
    graph.add_edge("project_mode_redirect", END)
    graph.add_edge("generate_project_answer", END)
    graph.add_edge("generate_plan", END)
    graph.add_edge("project_not_found", END)
    graph.add_edge("retrieve_document", "generate")
    graph.add_edge("general_advice", "generate")
    graph.add_edge("generate", END)
    return graph.compile(checkpointer=get_checkpointer())


# --------------------------- PLANNER GRAPH ---------------------------

PLANNER_STEPS = ["research", "outline", "tasks", "checklist"]

class PlannerState(TypedDict, total=False):
    project: str
    start: date
    days: int
    hours: int
    beginner: bool
    weekends_off: bool
    research: list[dict]
    selected_project: dict
    outline: dict
    tasks: list[dict]
    checklist: dict

class Outline(BaseModel):
    objective: str = Field(description="One-sentence project objective")
    architecture: list[str] = Field(description="3-6 architecture components")
    week_titles: list[str] = Field(description="One short theme per week, in order")

class DailyTask(BaseModel):
    title: str = Field(description="Short task title")
    description: str = Field(description="One sentence on what to do")
    phase: str = Field(description="Setup and research, Build, or Test and deliver")

class TaskList(BaseModel):
    tasks: list[DailyTask]

class ChecklistGroup(BaseModel):
    phase: str
    items: list[str]

class Checklist(BaseModel):
    groups: list[ChecklistGroup]

def planner_route(state: PlannerState) -> str:
    """Condition-based guard before research; invalid requests terminate safely."""
    return "research" if state.get("project") and state.get("days", 0) > 0 else "checklist"

def _context(state: PlannerState) -> str:
    return "\n\n".join(
        f"PROJECT METADATA: id={item.get('project_id')}; title={item.get('project_title')}; "
        f"domain={item.get('domain')}; source={item.get('source_type', 'document file')}.\n"
        f"PROJECT CONTENT:\n{item.get('text', '')[:6500]}"
        for item in state.get("research", [])
    ) or "(no matching project evidence)"

def _level(state: PlannerState) -> str:
    return "a beginner" if state.get("beginner", True) else "an experienced developer"

def research(state: PlannerState) -> dict:
    # Chat-originated plans must use the exact project already selected by
    # the get_project node. Direct planner requests retrieve the named project.
    selected = state.get("selected_project")
    if selected:
        return {"research": [selected]}
    hits = retriever.search(state["project"], k=16)
    hits = [hit for hit in hits if float(hit.get("match", 0)) >= MIN_DOCUMENT_MATCH]
    exact = [
        hit for hit in hits
        if str(hit.get("project_title", "")).casefold() == state["project"].casefold()
    ]
    if exact:
        return {"research": exact[:1]}
    if not hits:
        hits = search_seed_projects(state["project"], k=16)
    if not hits:
        raise ValueError(f"Project '{state['project']}' was not found in the approved catalogue.")
    return {"research": hits[:1]}

def outline(state: PlannerState) -> dict:
    days, hours, project = state["days"], state["hours"], state["project"]
    evidence = _context(state)
    system = (
        "ROLE: You are a senior software project architect.\n"
        "TASK: Expand the selected project concept into a feasible technical project outline.\n"
        "INSTRUCTIONS: Treat the retrieved project as inspiration and factual scope, not text to copy. "
        "Add practical architecture details, explain reasonable assumptions, and tailor complexity to the user. "
        "Do not claim unsupported features already exist in the source."
    )
    user = (
        f"QUESTION: Create a project outline for {project}.\n"
        f"User constraints: {days} {'working days' if state.get('weekends_off', True) else 'calendar days'}, "
        f"{hours} hours/day, {_level(state)}.\n"
        f"Suggested week count: {planner.weeks_needed(days)}.\n"
        f"Retrieved evidence:\n{evidence}\nANSWER: Return objective, architecture and week titles."
    )
    result = structured(Outline, system, user)
    data = result.model_dump() if result else planner.fallback_outline(
        project, days, hours, state.get("weekends_off", True)
    )
    return {"outline": data}

def tasks(state: PlannerState) -> dict:
    days, project = state["days"], state["project"]
    system = (
        "ROLE: You are an experienced technical project manager.\n"
        "TASK: Convert the expanded project outline into daily implementation tasks.\n"
        "INSTRUCTIONS: Return exactly the requested number of tasks in chronological order. "
        "Tasks must be actionable, beginner-friendly when requested, and consistent with the project evidence. "
        "Use only these phases: Setup and research, Build, Test and deliver."
    )
    user = (
        f"QUESTION: Create {days} daily tasks for {project}.\n"
        f"Objective: {state['outline']['objective']}\nAudience: {_level(state)}\n"
        f"Evidence: {_context(state)}\nANSWER: Return the task list."
    )
    result = structured(TaskList, system, user)
    items = [task.model_dump() for task in result.tasks][:days] if result else []
    if len(items) < days:
        items += planner.fallback_items(project, days, state.get("beginner", True), start_index=len(items))
    return {"tasks": planner.build_tasks(items, state["start"], state["hours"], state.get("weekends_off", True))}

def checklist(state: PlannerState) -> dict:
    titles = ", ".join(task["title"] for task in state.get("tasks", []))
    system = (
        "ROLE: You are a software quality and delivery lead.\n"
        "TASK: Create a practical project completion checklist.\n"
        "INSTRUCTIONS: Group checklist items into Setup and research, Build, Test and deliver. "
        "Provide 3-5 clear verification items per phase."
    )
    user = f"QUESTION: Create the delivery checklist for {state.get('project', 'the project')}.\nTasks: {titles}\nANSWER:"
    result = structured(Checklist, system, user)
    data = {group.phase: group.items for group in result.groups} if result and result.groups else planner.CHECKLIST
    return {"checklist": data}

@lru_cache
def get_planner_graph():
    graph = StateGraph(PlannerState)
    for name, function in zip(PLANNER_STEPS, (research, outline, tasks, checklist)):
        graph.add_node(name, function)
    graph.add_node("invalid_request", lambda state: {
        "outline": planner.fallback_outline("Unspecified project", 1, 1),
        "tasks": [], "checklist": planner.CHECKLIST,
    })
    graph.add_conditional_edges(
        START, planner_route,
        {"research": "research", "checklist": "invalid_request"},
    )
    graph.add_edge("research", "outline")
    graph.add_edge("outline", "tasks")
    graph.add_edge("tasks", "checklist")
    graph.add_edge("checklist", END)
    graph.add_edge("invalid_request", END)
    return graph.compile()
