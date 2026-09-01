"""
Main assistant graph — Agent ⇄ Tools (ReAct loop using LangGraph prebuilt).
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from app.llm.llm_factory import get_llm
from .state import AgentState
from .prompts import SYSTEM_PROMPT
from .tools.search_documents import search_documents
from .tools.generate_quiz.tool import generate_quiz

TOOLS = [search_documents, generate_quiz]


def agent_node(state: AgentState):
    """
    The main agent node that:
    1. Gets the LLM with tools bound
    2. Prepends system prompt
    3. Invokes LLM to decide: call tool or respond directly
    """
    model_config = state.get("model_config", {})
    supervisor_model = model_config.get("supervisor", "gemini-2.5-flash")

    llm = get_llm(supervisor_model, state.get("api_keys"))
    llm_with_tools = llm.bind_tools(TOOLS)

    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


def build_assistant_graph(checkpointer=None):
    """
    Build and compile the assistant graph:
    agent → (tools_condition) → tools → agent (loop)
                               → END (direct response)
    """
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(TOOLS))
    g.set_entry_point("agent")
    g.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    g.add_edge("tools", "agent")  # After tool runs, go back to agent to synthesize
    return g.compile(checkpointer=checkpointer)
