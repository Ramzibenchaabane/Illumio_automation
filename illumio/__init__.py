# illumio/__init__.py
"""
Package principal pour l'automatisation d'Illumio PCE.
Fournit des classes et fonctions pour interagir avec l'API Illumio.
"""
from .api_core import IllumioAPICore
from .api import IllumioAPI
from .database import IllumioDatabase
from .sync_manager import IllumioSyncManager
from .traffic_analyzer import IllumioTrafficAnalyzer
from .async_operations import AsyncOperation, TrafficAnalysisOperation
from .exceptions import (
    IllumioAPIError, 
    AuthenticationError, 
    ConfigurationError, 
    APIRequestError,
    TimeoutError,
    AsyncOperationError,
    RetryError
)

__all__ = [
    'IllumioAPICore',
    'IllumioAPI',
    'IllumioDatabase',
    'IllumioSyncManager',
    'IllumioTrafficAnalyzer',
    'AsyncOperation',
    'TrafficAnalysisOperation',
    'IllumioAPIError',
    'AuthenticationError',
    'ConfigurationError',
    'APIRequestError',
    'TimeoutError',
    'AsyncOperationError',
    'RetryError'
]