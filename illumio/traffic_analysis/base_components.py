# illumio/traffic_analysis/base_components.py
"""
Base components and utility classes for traffic analysis.
"""
import sys
import time
from typing import Dict, Any, Optional, Callable, Union, List, Tuple
from datetime import datetime, timedelta

from ..api import IllumioAPI
from ..database import IllumioDatabase
from ..async_operations import TrafficAnalysisOperation

class TrafficAnalysisBaseComponent:
    """Base class for traffic analysis components."""
    
    def __init__(self, 
                 api: Optional[IllumioAPI] = None, 
                 db: Optional[IllumioDatabase] = None):
        """
        Initialize the base traffic analysis component.
        
        Args:
            api (IllumioAPI, optional): Illumio API instance
            db (IllumioDatabase, optional): Illumio Database instance
        """
        self.api = api or IllumioAPI()
        self.db = db or IllumioDatabase()
        self.save_to_db = bool(self.db)
    
    def _log_status_update(self, 
                            status: str, 
                            response: Dict[str, Any], 
                            external_callback: Optional[Callable] = None) -> None:
        """
        Log and process status updates for async operations.
        
        Args:
            status (str): Current operation status
            response (dict): Full response containing status details
            external_callback (callable, optional): External callback function
        """
        query_id = response.get('id')
        print(f"Statut de la requête {query_id}: {status}")
        
        # Visual progress indicator
        progress_chars = ['|', '/', '-', '\\']
        progress_char = progress_chars[hash(status) % len(progress_chars)]
        print(f"{progress_char} ", end='')
        sys.stdout.flush()
        
        # Update status in database if enabled
        if self.save_to_db and query_id:
            self.db.update_traffic_query_status(query_id, status)
        
        # Call external callback if provided
        if external_callback:
            external_callback(status, response, self.db if self.save_to_db else None)

    def _handle_date_range(self, 
                            start_date: Optional[str] = None, 
                            end_date: Optional[str] = None,
                            days: int = 7) -> Tuple[str, str]:
        """
        Generate standard date range for traffic analysis.
        
        Args:
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
            days (int): Number of days to look back if no dates provided
        
        Returns:
            Tuple of (start_date, end_date)
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        return start_date, end_date