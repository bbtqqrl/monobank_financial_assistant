from app.core.config import DEEPSEEK_API_KEY
from app.services.ai.base import CategorizationAIClient


def get_categorization_ai_client() -> CategorizationAIClient:
    if DEEPSEEK_API_KEY:
        from app.services.ai.deepseek_client import DeepSeekCategorizationAIClient
        return DeepSeekCategorizationAIClient()

    from app.services.ai.mock_client import MockCategorizationAIClient
    return MockCategorizationAIClient()
