# illumio/utils/response.py
"""
Utilitaires pour standardiser les formats de réponse dans l'application.

Ce module définit une classe de réponse standardisée pour assurer 
la cohérence des retours d'API et des fonctions internes.
"""
from dataclasses import dataclass
from typing import Optional, Any, List, Dict, Union
from functools import wraps


@dataclass
class ApiResponse:
    """Classe pour standardiser les réponses d'API et des fonctions internes."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    message: Optional[str] = None
    
    @classmethod
    def success(cls, data: Any = None, message: Optional[str] = None) -> 'ApiResponse':
        """
        Crée une réponse de succès.
        
        Args:
            data: Données à retourner
            message: Message de succès optionnel
            
        Returns:
            Instance d'ApiResponse avec succès
        """
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error(cls, 
              message: str, 
              code: Optional[int] = None, 
              error_detail: Optional[str] = None) -> 'ApiResponse':
        """
        Crée une réponse d'erreur.
        
        Args:
            message: Message principal d'erreur
            code: Code d'erreur optionnel
            error_detail: Détails techniques de l'erreur
            
        Returns:
            Instance d'ApiResponse avec erreur
        """
        return cls(success=False, error=error_detail, status_code=code, message=message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit la réponse en dictionnaire.
        
        Returns:
            Dictionnaire représentant la réponse
        """
        result = {
            'success': self.success
        }
        
        if self.data is not None:
            result['data'] = self.data
            
        if self.message:
            result['message'] = self.message
            
        if not self.success:
            if self.error:
                result['error'] = self.error
                
            if self.status_code:
                result['status_code'] = self.status_code
                
        return result
    
    def __str__(self) -> str:
        """Représentation sous forme de chaîne."""
        if self.success:
            if self.message:
                return f"Success: {self.message}"
            return "Success"
        
        if self.message:
            if self.error:
                return f"Error: {self.message} ({self.error})"
            return f"Error: {self.message}"
        
        if self.error:
            return f"Error: {self.error}"
        
        return "Error"


def handle_exceptions(func):
    """
    Décorateur pour gérer les exceptions et retourner des ApiResponse.
    
    Args:
        func: Fonction à décorer
        
    Returns:
        Fonction décorée qui retourne toujours une ApiResponse
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # Si le résultat est déjà une ApiResponse, le retourner tel quel
            if isinstance(result, ApiResponse):
                return result
            
            # Sinon, envelopper le résultat dans une ApiResponse de succès
            return ApiResponse.success(data=result)
        except Exception as e:
            # Capturer l'exception et la retourner comme une ApiResponse d'erreur
            import traceback
            error_detail = traceback.format_exc()
            return ApiResponse.error(
                message=str(e),
                error_detail=error_detail
            )
    
    return wrapper