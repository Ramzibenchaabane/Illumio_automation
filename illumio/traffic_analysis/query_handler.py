# illumio/traffic_analysis/query_handler.py
"""
Handles traffic query creation and management.
"""
from datetime import datetime, timedelta
from typing import Dict,List, Any, Optional

from .base_components import TrafficAnalysisBaseComponent

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
        start_date, end_date = self._handle_date_range(start_date, end_date)
        
        # Use defaults if no custom filters provided
        if not query_name:
            query_name = f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        query_data = {
            "query_name": query_name,
            "start_date": start_date,
            "end_date": end_date,
            "sources_destinations_query_op": "and",
            "sources": {
                "include": sources or [[{"actors": "ams"}]],
                "exclude": []
            },
            "destinations": {
                "include": destinations or [[{"actors": "ams"}]],
                "exclude": []
            },
            "services": {
                "include": services or [],
                "exclude": []
            },
            "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
            "max_results": max_results,
            "exclude_workloads_from_ip_list_query": True
        }
        
        return query_data
    
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
        start_date, end_date = self._handle_date_range(days=days)
        
        query_name = f"Flow_{source_ip}_to_{dest_ip}_{protocol}"
        if port:
            query_name += f"_port{port}"
        
        query_data = {
            "query_name": query_name,
            "start_date": start_date,
            "end_date": end_date,
            "sources_destinations_query_op": "and",
            "sources": {
                "include": [[{"ip_address": source_ip}]],
                "exclude": []
            },
            "destinations": {
                "include": [[{"ip_address": dest_ip}]],
                "exclude": []
            },
            "services": {
                "include": [
                    {"proto": protocol, "port": port} if port 
                    else {"proto": protocol}
                ],
                "exclude": []
            },
            "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
            "max_results": 1000
        }
        
        return query_data