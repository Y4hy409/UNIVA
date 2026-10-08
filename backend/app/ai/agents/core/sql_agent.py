"""
CLARIUS Backend - SQL Agent (Backward Compatibility Wrapper)

Re-exports SQLService for backward compatibility across legacy modules.
"""

from app.ai.services.sql_service import SQLService

class SQLAgent(SQLService):
    """Backward compatibility subclass delegating to SQLService."""
    pass
