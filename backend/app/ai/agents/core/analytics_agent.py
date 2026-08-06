"""
CLARIUS Backend - Analytics Agent (Backward Compatibility Wrapper)

Re-exports AnalyticsService for backward compatibility across legacy modules.
"""

from app.ai.services.analytics_service import AnalyticsService

class AnalyticsAgent(AnalyticsService):
    """Backward compatibility subclass delegating to AnalyticsService."""
    pass
