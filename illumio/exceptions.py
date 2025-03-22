# illumio/exceptions.py
"""
Exceptions personnalisées pour l'application Illumio Toolbox.

Ce module définit une hiérarchie d'exceptions typées pour identifier
précisément la nature des erreurs rencontrées lors de l'exécution.
"""


class IllumioAPIError(Exception):
    """Exception de base pour les erreurs d'API Illumio."""
    pass


class ConfigurationError(IllumioAPIError):
    """Erreur liée à la configuration de l'application."""
    pass


class AuthenticationError(IllumioAPIError):
    """Erreur d'authentification auprès de l'API Illumio."""
    pass


class APIRequestError(IllumioAPIError):
    """Erreur lors d'une requête à l'API Illumio."""
    
    def __init__(self, status_code: int, message: str):
        """
        Initialise l'exception avec un code de statut et un message.
        
        Args:
            status_code: Code de statut HTTP de l'erreur
            message: Message d'erreur détaillé
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class TimeoutError(IllumioAPIError):
    """Erreur de délai d'attente dépassé pour une opération."""
    pass


class AsyncOperationError(IllumioAPIError):
    """Erreur lors d'une opération asynchrone avec l'API Illumio."""
    
    def __init__(self, operation_id: str, status: str, message: str):
        """
        Initialise l'exception avec les détails de l'opération asynchrone.
        
        Args:
            operation_id: Identifiant de l'opération asynchrone
            status: Statut de l'opération au moment de l'erreur
            message: Message d'erreur détaillé
        """
        self.operation_id = operation_id
        self.status = status
        self.message = message
        super().__init__(f"Async Operation Error (ID: {operation_id}, Status: {status}): {message}")


class RetryError(IllumioAPIError):
    """Erreur après plusieurs tentatives de retry d'une opération."""
    
    def __init__(self, attempts: int, original_error: Exception):
        """
        Initialise l'exception avec le nombre de tentatives et l'erreur originale.
        
        Args:
            attempts: Nombre de tentatives effectuées
            original_error: Exception originale ayant causé l'échec
        """
        self.attempts = attempts
        self.original_error = original_error
        super().__init__(f"Opération échouée après {attempts} tentatives: {original_error}")


# Exceptions de parsing
class ParsingError(Exception):
    """Exception de base pour les erreurs de parsing."""
    pass


class RuleParsingError(ParsingError):
    """Erreur lors du parsing des règles de sécurité."""
    pass


class TrafficFlowParsingError(ParsingError):
    """Erreur lors du parsing des flux de trafic."""
    pass


class WorkloadParsingError(ParsingError):
    """Erreur lors du parsing des workloads."""
    pass


class LabelParsingError(ParsingError):
    """Erreur lors du parsing des labels."""
    pass


# Exceptions de conversion
class ConversionError(Exception):
    """Exception de base pour les erreurs de conversion."""
    pass


class EntityConversionError(ConversionError):
    """Erreur lors de la conversion entre formats d'entité."""
    pass


class DatabaseConversionError(ConversionError):
    """Erreur lors de la conversion entre base de données et objets."""
    pass


# Exceptions de base de données
class DatabaseError(Exception):
    """Exception de base pour les erreurs de base de données."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Erreur de connexion à la base de données."""
    pass


class DatabaseQueryError(DatabaseError):
    """Erreur lors de l'exécution d'une requête SQL."""
    
    def __init__(self, query: str, error: Exception):
        """
        Initialise l'exception avec la requête et l'erreur originale.
        
        Args:
            query: Requête SQL ayant échoué (anonymisée si nécessaire)
            error: Exception originale de la base de données
        """
        self.query = query
        self.error = error
        super().__init__(f"Database Query Error: {error} (Query: {query})")


class DatabaseLockError(DatabaseError):
    """Erreur de verrou sur la base de données."""
    pass


# Exceptions de validation
class ValidationError(Exception):
    """Exception de base pour les erreurs de validation."""
    pass


class InputValidationError(ValidationError):
    """Erreur de validation des entrées utilisateur."""
    pass


class SchemaValidationError(ValidationError):
    """Erreur de validation de schéma."""
    pass