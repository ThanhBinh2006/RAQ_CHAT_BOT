"""
AgentState — Main state for the LangGraph assistant graph.
"""

from typing import TypedDict, Annotated, Optional, List
from langgraph.graph.message import add_messages


class ModelConfig(TypedDict):
    """Model assignment for each role in the system."""
    supervisor: str      # Model for the main chatbot agent
    generator: str       # Model for quiz generator node
    evaluator: str       # Model for quiz evaluator node
    synthesizer: str     # Model for quiz synthesizer node
    embed:str

class ApiKeys(TypedDict, total=False):
    """User BYOK API keys by provider."""
    default: str
    default_embed:str
    gemini: str
    openai: str
    anthropic: str


class AgentState(TypedDict):
    """Main state shared across the assistant graph."""
    messages: Annotated[list, add_messages]
    user_id: str
    library_id: str
    session_id: str
    model_config: ModelConfig
    api_keys: ApiKeys
    citations: Optional[List[dict]]
    quiz_draft: Optional[List[dict]]  # Result from generate_quiz tool → rendered by CopilotKit
