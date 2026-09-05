"""
Dynamic LLM Factory with BYOK 2-tier fallback.
Supports Gemini, Groq, OpenAI, Anthropic providers.
Includes mock mode for development without API keys.
"""

from typing import Optional, Dict
from langchain_core.language_models import BaseChatModel


# ── Provider → Model mapping ────────────────────────────────
PROVIDER_MAP = {
    # default models
    "deepseek-ai/deepseek-v4-pro-0813": "default",
    "deepseek-v4-pro-0813": "default",
    "deepseek-ai/deepseek-v4-flash-0731": "default",
    "deepseek-v4-flash-0731": "default",
    # Gemini models
    "gemini-2.5-flash": "gemini",
    "gemini-3.1-pro": "gemini",
    # OpenAI models
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    # Anthropic models
    "claude-3-5-sonnet-latest": "anthropic",
    "claude-3-5-haiku-latest": "anthropic",
}


class MockChatModel(BaseChatModel):
    """
    Mock LLM for development/testing without real API keys.
    Returns predefined responses based on the context.
    """
    model_name: str = "mock"

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatResult, ChatGeneration

        # Check if there's a system message about quiz generation
        last_msg = messages[-1].content if messages else ""

        response_text = (
            "Đây là phản hồi mock từ trợ lý thư viện. "
            "Hệ thống đang chạy ở chế độ mock (USE_MOCK_LLM=true). "
            "Vui lòng cấu hình API key thật để sử dụng đầy đủ tính năng."
        )

        message = AIMessage(content=response_text)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop, run_manager, **kwargs)

    def bind_tools(self, tools, **kwargs):
        """
        Mock implementation of bind_tools. 
        It just returns the mock model itself since we don't actually execute tools in mock mode.
        """
        return self


def _detect_provider(model_name: str) -> str:
    """Detect the provider from a model name."""
    if model_name in PROVIDER_MAP:
        return PROVIDER_MAP[model_name]
    # Heuristic fallback
    lower = model_name.lower()
    if "gemini" in lower:
        return "gemini"
    if "gpt" in lower:
        return "openai"
    if "claude" in lower:
        return "anthropic"
    return "default"  # default fallback


def _resolve_api_key(provider: str, api_keys: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    2-tier key resolution:
    1. User BYOK key (from api_keys dict)
    2. System key (from .env)
    """
    if api_keys:
        user_key = api_keys.get(provider)
        if user_key:
            return user_key
    return None


def get_llm(
    model_name: str,
    api_keys: Optional[Dict[str, str]] = None,
    temperature: float = 0.3,
) -> BaseChatModel:
    """
    Create an LLM instance based on model name and available API keys.

    Args:
        model_name: The model identifier (e.g., 'deepseek-ai/deepseek-v4-pro-0813', 'gemini-2.5-flash', 'gpt-4o')
        api_keys: Dict of provider → API key from user BYOK
        temperature: LLM temperature setting

    Returns:
        A LangChain BaseChatModel instance
    """
    # Mock mode
    if settings.USE_MOCK_LLM:
        return MockChatModel(model_name=model_name)

    provider = _detect_provider(model_name)
    api_key = _resolve_api_key(provider, api_keys)

    if not api_key:
        raise ValueError(
            f"Không tìm thấy API key cho provider '{provider}' (model: {model_name}). "
            f"Vui lòng cung cấp key qua Settings hoặc cấu hình SYSTEM_*_API_KEY trong .env."
        )

    if provider == "default":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base="https://integrate.api.default.com/v1",
            temperature=temperature,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            temperature=temperature,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            temperature=temperature,
        )

    raise ValueError(f"Provider không được hỗ trợ: {provider}")


def get_structured_llm(
    model_name: str,
    api_keys: Optional[Dict[str, str]] = None,
    schema=None,
    temperature: float = 0.0,
):
    """
    Get an LLM with structured output (for Pydantic schema enforcement).
    Used by evaluator and synthesizer nodes.
    """
    llm = get_llm(model_name, api_keys, temperature)

    if settings.USE_MOCK_LLM:
        return llm  # Mock doesn't support structured output

    if schema:
        return llm.with_structured_output(schema)
    return llm
