
from taskflow.adapters.llm.gemini_provider import GeminiProvider
from taskflow.adapters.llm.ollama_provider import OllamaProvider
from taskflow.domain.ports.ports import EmbeddingProvider, LLMProvider


def create_llm_provider(
    provider_type: str,
    api_key: str | None = None,
    ollama_url: str = "http://localhost:11434",
    ollama_model: str | None = None,
) -> LLMProvider:
    """Fábrica de provedores LLM.
    
    Args:
        provider_type: 'gemini' ou 'ollama'.
        api_key: Chave da API caso provider_type seja 'gemini'.
        ollama_url: URL base caso provider_type seja 'ollama'.
        ollama_model: Modelo do ollama (usa OLLAMA_MODEL do .env se não informado).
    """
    if provider_type.lower() == "gemini":
        return GeminiProvider(api_key=api_key)
    elif provider_type.lower() == "ollama":
        if not ollama_model:
            from taskflow.config.settings import get_settings
            ollama_model = get_settings().OLLAMA_MODEL
        return OllamaProvider(base_url=ollama_url, model_name=ollama_model)
    elif provider_type.lower() in ("chatgpt_subscription", "chatgpt_oauth", "openai_subscription"):
        from taskflow.adapters.llm.chatgpt_subscription import ChatGPTSubscriptionLLMProvider
        return ChatGPTSubscriptionLLMProvider(access_token=api_key)
    elif provider_type.lower() in ("copilot_web", "copilot", "m365_copilot"):
        from taskflow.adapters.llm.copilot_web_provider import CopilotWebLLMProvider
        return CopilotWebLLMProvider()
    else:
        raise ValueError(f"Provedor LLM não suportado: {provider_type}")


def create_embedding_provider(
    provider_type: str,
    api_key: str | None = None,
    ollama_url: str = "http://localhost:11434",
) -> EmbeddingProvider:
    """Fábrica de provedores de Embedding."""
    if provider_type.lower() == "gemini":
        return GeminiProvider(api_key=api_key)
    elif provider_type.lower() == "ollama":
        return OllamaProvider(base_url=ollama_url)
    else:
        raise ValueError(f"Provedor de Embedding não suportado: {provider_type}")
