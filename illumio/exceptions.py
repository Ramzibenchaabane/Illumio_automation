class IllumioAPIError(Exception):
    """Exception de base pour les erreurs d'API Illumio."""
    pass

class ConfigurationError(IllumioAPIError):
    """Erreur liée à la configuration."""
    pass

class AuthenticationError(IllumioAPIError):
    """Erreur d'authentification."""
    pass

class APIRequestError(IllumioAPIError):
    """Erreur de requête API."""
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")

class TimeoutError(IllumioAPIError):
    """Erreur de délai d'attente dépassé pour une opération."""
    pass

class AsyncOperationError(IllumioAPIError):
    """Erreur lors d'une opération asynchrone."""
    def __init__(self, operation_id, status, message):
        self.operation_id = operation_id
        self.status = status
        self.message = message
        super().__init__(f"Async Operation Error (ID: {operation_id}, Status: {status}): {message}")

class RetryError(IllumioAPIError):
    """Erreur après plusieurs tentatives de retry."""
    def __init__(self, attempts, original_error):
        self.attempts = attempts
        self.original_error = original_error
        super().__init__(f"Opération échouée après {attempts} tentatives: {original_error}")