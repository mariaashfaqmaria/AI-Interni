# backend/src/routers/chat.py
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..graphs.graph import get_chat_graph
from ..models import Conversation, Message, Plan, User
from ..schemas import ChatIn, ChatOut
from ..services import retriever
from ..services.llm import text_of

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    thread_id = body.thread_id or str(uuid.uuid4())
    convo = db.scalar(
        select(Conversation).where(
            Conversation.user_id == user.id, Conversation.thread_id == thread_id, Conversation.type == "chat"
        )
    )
    if not convo:
        title = body.message.strip().replace("\n", " ")
        convo = Conversation(user_id=user.id, thread_id=thread_id, type="chat", title=title[:60] or "New chat")
        db.add(convo)
        db.flush()

    graph = get_chat_graph()
    graph_config = {
        "configurable": {"thread_id": f"{user.id}:{thread_id}"},
        "run_name": "project_chat",
        "tags": ["chat", body.mode],
        "metadata": {"user_id": user.id, "thread_id": thread_id},
    }

    # MemorySaver is process-local. Restore prior turns from SQL if no graph
    # checkpoint exists (for example, after a backend restart).
    snapshot = graph.get_state(graph_config)
    checkpoint_messages = (snapshot.values or {}).get("messages", []) if snapshot else []
    history = []
    if not checkpoint_messages:
        for previous in convo.messages[-20:]:
            if previous.role == "user":
                history.append(HumanMessage(content=previous.text))
            else:
                history.append(AIMessage(content=previous.text))

    result = graph.invoke(
        {"messages": [*history, HumanMessage(content=body.message)], "mode": body.mode},
        config=graph_config,
    )
    reply = text_of(result["messages"][-1].content)
    sources = result.get("sources", []) if body.mode == "From document" else []

    plan_id = None
    plan_content = result.get("plan_result")
    if plan_content:
        saved_plan = Plan(user_id=user.id, project=plan_content["project"], content=plan_content)
        db.add(saved_plan)
        db.flush()
        plan_id = saved_plan.id

    db.add(Message(conversation_id=convo.id, role="user", text=body.message))
    db.add(Message(conversation_id=convo.id, role="bot", text=reply, sources=sources or None))
    convo.updated_at = datetime.now(timezone.utc)
    db.commit()
    return ChatOut(
        reply=reply,
        sources=sources,
        conversation_id=convo.id,
        thread_id=thread_id,
        file=retriever.filename() if sources else None,
        plan_id=plan_id,
    )
