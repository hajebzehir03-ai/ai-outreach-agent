"""Orchestrator — LangGraph state machine con routing completo da orchestrator.md."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from adh.agents.qualifier import qualifier_node
from adh.agents.researcher import researcher_node
from adh.agents.scout import scout_node
from adh.agents.sender import sender_node
from adh.agents.state import AgentState
from adh.agents.writer import writer_node

# ---------------------------------------------------------------------------
# Nodi terminali / utility
# ---------------------------------------------------------------------------

def archive_node(state: AgentState) -> AgentState:
    """Archivia il lead (drop o do_not_contact)."""
    return state.model_copy(update={"status": "archived", "current_step": "archived"})


def requeue_writer_node(state: AgentState) -> AgentState:
    """Passa il feedback al writer per il retry (max 2 volte totali)."""
    return state.model_copy(update={"current_step": "writer"})


# ---------------------------------------------------------------------------
# Router functions (conditional edges)
# ---------------------------------------------------------------------------

def _after_qualifier(state: AgentState) -> str:
    """
    score < 60 → archive
    do_not_contact → archive
    altrimenti → writer
    """
    q = state.qualification
    if not q or not q.should_proceed:
        return "archive"
    return "writer"


def _after_writer(state: AgentState) -> str:
    """
    error dopo max retry → archive
    messaggio generato → approval_gate (interrupt_before sender)
    retry necessario → writer di nuovo
    """
    if state.status == "error":
        return "archive"
    if state.current_step == "writer":
        return "writer"   # retry
    return "approval_gate"


def _after_approval(state: AgentState) -> str:
    """
    approved | edited → sender
    rejected → archive (con feedback loggato)
    None (in attesa) → END (il workflow riprende via resume)
    """
    if state.approval_status in ("approved", "edited"):
        return "sender"
    if state.approval_status == "rejected":
        return "archive"
    return "wait"   # non è una strada del grafo — gestita dall'interrupt


def approval_gate_node(state: AgentState) -> AgentState:
    """Nodo placeholder: lo stato viene sospeso qui fino all'approvazione umana."""
    return state.model_copy(update={"current_step": "approval_gate"})


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    g = StateGraph(AgentState)

    g.add_node("scout", scout_node)
    g.add_node("researcher", researcher_node)
    g.add_node("qualifier", qualifier_node)
    g.add_node("writer", writer_node)
    g.add_node("approval_gate", approval_gate_node)
    g.add_node("sender", sender_node)
    g.add_node("archive", archive_node)

    g.set_entry_point("scout")

    g.add_edge("scout", "researcher")
    g.add_edge("researcher", "qualifier")

    g.add_conditional_edges(
        "qualifier",
        _after_qualifier,
        {"archive": "archive", "writer": "writer"},
    )

    g.add_conditional_edges(
        "writer",
        _after_writer,
        {"archive": "archive", "writer": "writer", "approval_gate": "approval_gate"},
    )

    g.add_conditional_edges(
        "approval_gate",
        _after_approval,
        {"sender": "sender", "archive": "archive", "wait": END},
    )

    g.add_edge("sender", END)
    g.add_edge("archive", END)

    return g


def create_pipeline(checkpointer=None):
    """
    Compila il grafo con:
    - interrupt_before=["sender"]: pausa obbligatoria per approval umano
    - checkpointer per persistenza su PostgreSQL (o MemorySaver in dev)
    """
    graph = build_graph()
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["sender"],
    )
