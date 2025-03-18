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