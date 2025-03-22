# illumio/traffic_analysis/query_handler.py
"""
Handles traffic query creation and management.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .base_components import TrafficAnalysisBaseComponent

# Importation du formatter de requêtes
from ..formatters.traffic_query_formatter import TrafficQueryFormatter

class TrafficQueryHandler(TrafficAnalysisBaseComponent):
    """
    Manages the creation and processing of traffic analysis queries.
    """
    
    def create_default_query(self, 
                              query_name: Optional[str] = None, 
                              start_date: Optional[str] = None, 
                              end_date: Optional[str] = None,
                              max_results: int = 10000,
                              sources: Optional[List[Dict[str, Any]]] = None,
                              destinations: Optional[List[Dict[str, Any]]] = None,
                              services: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a default traffic analysis query.
        
        Args:
            query_name (str, optional): Name for the query
            start_date (str, optional): Start date for analysis
            end_date (str, optional): End date for analysis
            max_results (int): Maximum number of results to return
            sources (list, optional): Custom source filters
            destinations (list, optional): Custom destination filters
            services (list, optional): Custom service filters
        
        Returns:
            Dict containing the traffic analysis query
        """
        # Déléguer la création de la requête au formatter
        # Pour assurer la compatibilité avec les appels existants, traiter les dates si nécessaires
        start_date, end_date = self._handle_date_range(start_date, end_date)
        
        # Utiliser le formatter pour créer la requête
        if sources or destinations or services:
            return TrafficQueryFormatter.format_custom_query(
                query_name=query_name,
                sources=sources,
                destinations=destinations,
                services=services,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
        else:
            return TrafficQueryFormatter.format_default_query(
                query_name=query_name,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results
            )
    
    def create_specific_flow_query(self, 
                                    source_ip: str, 
                                    dest_ip: str, 
                                    protocol: int, 
                                    port: Optional[int] = None,
                                    days: int = 7) -> Dict[str, Any]:
        """
        Create a query for a specific traffic flow.
        
        Args:
            source_ip (str): Source IP address
            dest_ip (str): Destination IP address
            protocol (int): IP protocol number
            port (int, optional): Port number
            days (int): Number of days to analyze
        
        Returns:
            Dict containing the specific flow query
        """
        # Calculer dates de début et fin sur la base du nombre de jours
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Utiliser le formatter pour construire la requête spécifique à un flux
        return TrafficQueryFormatter.format_specific_flow_query(
            source_ip=source_ip,
            dest_ip=dest_ip,
            protocol=protocol,
            port=port,
            start_date=start_date,
            end_date=end_date
        )