"""Runtime construction isolated from provider-specific implementations."""

from geoops_api.agent.runtime import AgentRuntime, LocalAgentRuntime
from geoops_api.agent.tools import AgentToolRegistry
from geoops_api.config import Settings


def build_agent_runtime(settings: Settings, registry: AgentToolRegistry) -> AgentRuntime:
    if settings.model_provider == "local":
        return LocalAgentRuntime(registry, model_name=settings.model_name)

    from geoops_api.agent.google_adk import GoogleAdkRuntime

    return GoogleAdkRuntime(
        registry,
        provider=settings.model_provider,
        model_name=settings.model_name,
        api_key=(settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None),
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )
