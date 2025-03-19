# illumio/async_operations.py
"""
Module de gestion des opérations asynchrones pour l'API Illumio.
Centralise la logique de soumission, surveillance et récupération des résultats des opérations asynchrones.
"""
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional, List, Tuple
from .exceptions import APIRequestError, TimeoutError, AsyncOperationError

class AsyncOperation(ABC):
    """Classe abstraite pour les opérations asynchrones avec l'API Illumio."""
    
    def __init__(self, api, polling_interval: int = 5, max_attempts: int = 60, 
                 status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        """
        Initialise une opération asynchrone.
        
        Args:
            api: Instance d'IllumioAPI pour communiquer avec l'API
            polling_interval: Intervalle en secondes entre les vérifications d'état
            max_attempts: Nombre maximal de tentatives de vérification
            status_callback: Fonction de rappel pour recevoir les mises à jour d'état
        """
        self.api = api
        self.polling_interval = polling_interval
        self.max_attempts = max_attempts
        self.status_callback = status_callback
        self.operation_id = None
        self.last_status = None
        self.last_response = None
    
    @abstractmethod
    def submit(self, data: Dict[str, Any]) -> str:
        """
        Soumet une opération asynchrone à l'API.
        
        Args:
            data: Données pour l'opération
            
        Returns:
            ID de l'opération asynchrone
            
        Raises:
            APIRequestError: En cas d'erreur lors de la soumission
        """
        pass
    
    @abstractmethod
    def get_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Récupère l'état actuel d'une opération asynchrone.
        
        Args:
            operation_id: Identifiant de l'opération
            
        Returns:
            Réponse complète de l'API contenant l'état
            
        Raises:
            APIRequestError: En cas d'erreur lors de la récupération de l'état
        """
        pass
    
    @abstractmethod
    def get_results(self, operation_id: str) -> Any:
        """
        Récupère les résultats d'une opération asynchrone terminée.
        
        Args:
            operation_id: Identifiant de l'opération
            
        Returns:
            Résultats de l'opération
            
        Raises:
            APIRequestError: En cas d'erreur lors de la récupération des résultats
        """
        pass
    
    @abstractmethod
    def extract_status(self, response: Dict[str, Any]) -> str:
        """
        Extrait l'état d'une réponse d'API.
        
        Args:
            response: Réponse de l'API
            
        Returns:
            État de l'opération (ex: 'created', 'running', 'completed', 'failed')
        """
        pass
    
    @abstractmethod
    def is_completed(self, status: str) -> bool:
        """
        Vérifie si l'état indique que l'opération est terminée avec succès.
        
        Args:
            status: État actuel de l'opération
            
        Returns:
            True si l'opération est terminée avec succès, False sinon
        """
        pass
    
    @abstractmethod
    def is_failed(self, status: str) -> bool:
        """
        Vérifie si l'état indique que l'opération a échoué.
        
        Args:
            status: État actuel de l'opération
            
        Returns:
            True si l'opération a échoué, False sinon
        """
        pass
    
    def execute(self, data: Dict[str, Any]) -> Any:
        """
        Exécute une opération asynchrone complète: soumission, surveillance et récupération des résultats.
        
        Args:
            data: Données pour l'opération
            
        Returns:
            Résultats de l'opération
            
        Raises:
            APIRequestError: En cas d'erreur lors de l'opération
            TimeoutError: Si l'opération n'est pas terminée dans le délai imparti
        """
        # Soumettre l'opération
        self.operation_id = self.submit(data)
        
        if not self.operation_id:
            raise APIRequestError(0, "Impossible d'obtenir l'ID de l'opération asynchrone")
        
        # Surveiller l'état de l'opération
        attempts = 0
        while attempts < self.max_attempts:
            self.last_response = self.get_status(self.operation_id)
            status = self.extract_status(self.last_response)
            
            # Si le statut a changé, appeler le callback
            if status != self.last_status:
                self.last_status = status
                if self.status_callback:
                    self.status_callback(status, self.last_response)
            
            # Vérifier si l'opération est terminée ou a échoué
            if self.is_completed(status):
                return self.get_results(self.operation_id)
            
            if self.is_failed(status):
                error_message = self.extract_error_message(self.last_response)
                raise APIRequestError(0, f"L'opération asynchrone a échoué: {error_message}")
            
            # Attendre avant la prochaine vérification
            time.sleep(self.polling_interval)
            attempts += 1
        
        raise TimeoutError(f"L'opération asynchrone n'a pas été complétée après {self.max_attempts * self.polling_interval} secondes")
    
    def extract_error_message(self, response: Dict[str, Any]) -> str:
        """
        Extrait le message d'erreur d'une réponse d'API en cas d'échec.
        
        Args:
            response: Réponse de l'API
            
        Returns:
            Message d'erreur ou 'Raison inconnue' si non disponible
        """
        return response.get('error_message', 'Raison inconnue')
    
    def retry_with_backoff(self, func: Callable, *args, max_retries: int = 3, 
                           initial_delay: float = 1.0, backoff_factor: float = 2.0, 
                           **kwargs) -> Any:
        """
        Exécute une fonction avec une stratégie de retry et backoff exponentiel.
        
        Args:
            func: Fonction à exécuter
            *args: Arguments positionnels pour la fonction
            max_retries: Nombre maximal de tentatives
            initial_delay: Délai initial en secondes
            backoff_factor: Facteur d'augmentation du délai à chaque tentative
            **kwargs: Arguments nommés pour la fonction
            
        Returns:
            Résultat de la fonction
            
        Raises:
            Exception: La dernière exception rencontrée après épuisement des tentatives
        """
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    raise last_exception


class TrafficAnalysisOperation(AsyncOperation):
    """Classe spécifique pour les opérations d'analyse de trafic asynchrones."""
    
    def submit(self, data: Dict[str, Any]) -> str:
        """
        Soumet une requête d'analyse de trafic asynchrone.
        
        Args:
            data: Données de la requête d'analyse de trafic
            
        Returns:
            ID de la requête asynchrone
        """
        response = self.api.create_async_traffic_query(data)
        
        # CORRECTION: Extraire l'ID depuis l'URL dans le champ href
        # Format typique: "/api/v2/orgs/1/traffic_flows/async_queries/123456"
        href = response.get('href', '')
        if not href:
            print("Erreur: Aucun attribut 'href' dans la réponse de l'API")
            print(f"Réponse complète: {response}")
            return None
            
        # Extraire l'ID à la fin de l'URL
        query_id = href.split('/')[-1]
        if not query_id:
            print(f"Erreur: Impossible d'extraire l'ID depuis l'URL: {href}")
            return None
            
        # CORRECTION: Supprimer le doublon dans l'affichage du message
        print(f"Requête asynchrone créée avec l'ID: {query_id}")
        return query_id
    
    def get_status(self, operation_id: str) -> Dict[str, Any]:
        """
        Récupère l'état actuel d'une requête d'analyse de trafic.
        
        Args:
            operation_id: Identifiant de la requête
            
        Returns:
            Réponse complète de l'API contenant l'état
        """
        return self.api.get_async_traffic_query_status(operation_id)
    
    def get_results(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Récupère les résultats d'une requête d'analyse de trafic terminée.
        
        Args:
            operation_id: Identifiant de la requête
            
        Returns:
            Résultats de l'analyse de trafic
        """
        return self.api.get_async_traffic_query_results(operation_id)
    
    def extract_status(self, response: Dict[str, Any]) -> str:
        """
        Extrait l'état d'une réponse de requête d'analyse de trafic.
        
        Args:
            response: Réponse de l'API
            
        Returns:
            État de la requête
        """
        return response.get('status', 'unknown')
    
    def is_completed(self, status: str) -> bool:
        """
        Vérifie si la requête est terminée avec succès.
        
        Args:
            status: État actuel de la requête
            
        Returns:
            True si la requête est terminée avec succès, False sinon
        """
        return status == 'completed'
    
    def is_failed(self, status: str) -> bool:
        """
        Vérifie si la requête a échoué.
        
        Args:
            status: État actuel de la requête
            
        Returns:
            True si la requête a échoué, False sinon
        """
        return status == 'failed'
    
    def create_default_query(self, query_name: str, 
                           start_date: Optional[str] = None, 
                           end_date: Optional[str] = None,
                           max_results: int = 10000) -> Dict[str, Any]:
        """
        Crée une requête de trafic par défaut.
        
        Args:
            query_name: Nom de la requête
            start_date: Date de début (format YYYY-MM-DD), par défaut 7 jours avant aujourd'hui
            end_date: Date de fin (format YYYY-MM-DD), par défaut aujourd'hui
            max_results: Nombre maximum de résultats
            
        Returns:
            Dictionnaire contenant la requête par défaut
        """
        from datetime import datetime, timedelta
        
        # Définir les dates par défaut si non fournies
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Structure de base d'une requête de trafic
        return {
            "query_name": query_name,
            "start_date": start_date,
            "end_date": end_date,
            "sources_destinations_query_op": "and",
            "sources": {
                "include": [
                    [{"actors": "ams"}]  # All Managed Systems - CORRIGÉ: tableau imbriqué
                ],
                "exclude": []
            },
            "destinations": {
                "include": [
                    [{"actors": "ams"}]  # All Managed Systems - CORRIGÉ: tableau imbriqué
                ],
                "exclude": []
            },
            "services": {
                "include": [],
                "exclude": []
            },
            "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
            "max_results": max_results,
            "exclude_workloads_from_ip_list_query": True
        }
        
    def start_deep_rule_analysis(self, operation_id: str, label_based_rules: bool = False,
                                offset: int = 0, limit: int = 100) -> bool:
        """
        Lance une analyse de règles approfondie pour une opération terminée.
        
        Args:
            operation_id: Identifiant de l'opération
            label_based_rules: Si vrai, utilise les règles basées sur les labels
            offset: Index de départ pour les résultats
            limit: Nombre maximum de résultats
            
        Returns:
            True si l'analyse a été lancée avec succès, False sinon
        """
        return self.api.start_deep_rule_analysis(
            query_id=operation_id,
            label_based_rules=label_based_rules,
            offset=offset,
            limit=limit
        )
    
    def get_deep_rule_analysis_results(self, operation_id: str, offset: int = 0, limit: int = 5000) -> List[Dict[str, Any]]:
        """
        Récupère les résultats d'une analyse de règles approfondie.
        
        Args:
            operation_id: Identifiant de l'opération
            offset: Index de départ pour les résultats
            limit: Nombre maximum de résultats
            
        Returns:
            Résultats de l'analyse de règles
        """
        return self.api.get_deep_rule_analysis_results(
            query_id=operation_id,
            offset=offset,
            limit=limit
        )
    
    def monitor_deep_rule_analysis(self, operation_id: str) -> Dict[str, Any]:
        """
        Surveille l'état d'une analyse de règles approfondie.
        
        Args:
            operation_id: Identifiant de l'opération
            
        Returns:
            Statut actuel de l'analyse de règles
        """
        # Cette méthode utilise la même API que pour vérifier l'état de la requête initiale
        status_response = self.get_status(operation_id)
        
        # Extraire spécifiquement les informations sur l'analyse de règles
        rules_info = status_response.get('rules', {})
        rules_status = rules_info.get('status', 'unknown')
        
        return {
            'operation_id': operation_id,
            'rules_status': rules_status,
            'rules_info': rules_info,
            'full_response': status_response
        }