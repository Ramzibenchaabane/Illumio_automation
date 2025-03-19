# illumio/traffic_analysis/export_handler.py
"""
Handles exporting traffic analysis results to various formats.
"""
import os
import json
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base_components import TrafficAnalysisBaseComponent
from .result_processing import TrafficResultProcessor

class TrafficExportHandler(TrafficAnalysisBaseComponent):
    """
    Manages export of traffic analysis results to different file formats.
    """
    
    def export_flows(self, 
                     flows: List[Dict[str, Any]], 
                     filename: str, 
                     format_type: str = 'json') -> bool:
        """
        Export traffic flows to specified format.
        
        Args:
            flows (list): List of traffic flows to export
            filename (str): Output filename
            format_type (str): Export format ('json' or 'csv')
        
        Returns:
            bool: True if export successful, False otherwise
        """
        # Ensure filename has correct extension
        if not filename.endswith(('.json', '.csv')):
            filename += '.json' if format_type.lower() == 'json' else '.csv'
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Process raw flows for export
        processed_flows = TrafficResultProcessor.process_raw_flows(flows)
        
        try:
            if format_type.lower() == 'json':
                return self._export_to_json(processed_flows, filename)
            elif format_type.lower() == 'csv':
                return self._export_to_csv(processed_flows, filename)
            else:
                print(f"Format non supporté: {format_type}")
                return False
        except Exception as e:
            print(f"Erreur lors de l'export: {e}")
            return False
    
    def _export_to_json(self, flows: List[Dict[str, Any]], filename: str) -> bool:
        """
        Export flows to JSON format.
        
        Args:
            flows (list): Processed traffic flows
            filename (str): Output JSON filename
        
        Returns:
            bool: True if export successful
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(flows, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Export JSON terminé. Fichier sauvegardé: {filename}")
            return True
        except Exception as e:
            print(f"Erreur lors de l'export JSON: {e}")
            return False
    
    def _export_to_csv(self, flows: List[Dict[str, Any]], filename: str) -> bool:
        """
        Export flows to CSV format.
        
        Args:
            flows (list): Processed traffic flows
            filename (str): Output CSV filename
        
        Returns:
            bool: True if export successful
        """
        try:
            # Define CSV columns
            fieldnames = [
                'src_ip', 'src_workload_id', 
                'dst_ip', 'dst_workload_id', 
                'service_name', 'service_port', 'service_protocol', 
                'policy_decision', 'flow_direction', 
                'num_connections', 
                'first_detected', 'last_detected', 
                'rule_href', 'rule_name'
            ]
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for flow in flows:
                    # Extract only the specified fields
                    csv_row = {field: flow.get(field, '') for field in fieldnames}
                    writer.writerow(csv_row)
            
            print(f"✅ Export CSV terminé. Fichier sauvegardé: {filename}")
            return True
        except Exception as e:
            print(f"Erreur lors de l'export CSV: {e}")
            return False
    
    def export_query_results(self, 
                             query_id: str, 
                             format_type: str = 'json', 
                             output_file: Optional[str] = None) -> bool:
        """
        Export results for a specific traffic query.
        
        Args:
            query_id (str): ID of the traffic query
            format_type (str): Export format ('json' or 'csv')
            output_file (str, optional): Custom output filename
        
        Returns:
            bool: True if export successful
        """
        # Retrieve flows for the query
        flows = self.db.get_traffic_flows(query_id)
        
        if not flows:
            print(f"Aucun flux trouvé pour la requête {query_id}.")
            return False
        
        # Generate default filename if not provided
        if not output_file:
            output_file = f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}"
        
        # Perform export
        return self.export_flows(flows, output_file, format_type)