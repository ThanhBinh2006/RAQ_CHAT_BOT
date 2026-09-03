"""
Main assistant graph — Agent ⇄ Tools (ReAct loop using LangGraph).
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import tools_condition
from langchain_core.messages import SystemMessage, ToolMessage

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
    model_config = state.get("model_config") or {}
    supervisor_model = model_config.get("supervisor", "deepseek-ai/deepseek-v4-pro-0813")

    llm = get_llm(supervisor_model, state.get("api_keys") or {})
    llm_with_tools = llm.bind_tools(TOOLS)

    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    response = llm_with_tools.invoke(messages)
    print(response)
    return {"messages": [response]}


async def custom_tool_node(state: AgentState):
    """
    Custom tool node to execute tools manually and update the state (citations, quiz_draft).
    This avoids issues with LangGraph Command and InjectedToolCallId.
    """
    last_message = state["messages"][-1]
    update = {"messages": []}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]

        try:
            if tool_name == "search_documents":
                query_val = args.get("query", "")
                res = await search_documents.coroutine(
                    query=query_val, 
                    state=state
                )
                update["messages"].append(ToolMessage(
                    content=res.get("context_text", "Không tìm thấy tài liệu phù hợp."), 
                    tool_call_id=tool_call["id"], 
                    name=tool_name
                ))
                if "citations" in res:
                    update["citations"] = res["citations"]

            elif tool_name == "generate_quiz":
                res = await generate_quiz.coroutine(
                    num_questions=args.get("num_questions", 5), 
                    focus_topic=args.get("focus_topic"), 
                    state=state
                )
                update["messages"].append(ToolMessage(
                    content=res.get("message", "Đã sinh câu hỏi."), 
                    tool_call_id=tool_call["id"], 
                    name=tool_name
                ))
                if "quiz_draft" in res:
                    update["quiz_draft"] = res["quiz_draft"]
        except Exception as e:
            print(f"Error executing tool {tool_name}: {e}")
            update["messages"].append(ToolMessage(
                content=f"Không thể thực thi {tool_name}: {str(e)}", 
                tool_call_id=tool_call["id"], 
                name=tool_name
            ))

    return update


def build_assistant_graph(checkpointer=None):
    """
    Build and compile the assistant graph:
    agent → (tools_condition) → tools → agent (loop)
                               → END (direct response)
    """
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", custom_tool_node)
    g.set_entry_point("agent")
    g.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    g.add_edge("tools", "agent")  # After tool runs, go back to agent to synthesize
    return g.compile(checkpointer=checkpointer)
