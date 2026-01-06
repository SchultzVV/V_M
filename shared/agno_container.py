# Compatibility wrapper for legacy imports
# The actual implementation is in langchain_container.py
from shared.langchain_container import LangChainContainer as agno_container

__all__ = ['agno_container']
