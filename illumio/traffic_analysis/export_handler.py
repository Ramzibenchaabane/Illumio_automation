# illumio/traffic_analysis/export_handler.py
"""
Handles exporting traffic analysis results to various formats.
"""
import os
import json
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook

from illumio.utils.directory_manager import get_output_dir, get_file_path

from .base_components import TrafficAnalysisBaseComponent
from .result_processing import TrafficResultProcessor

# Importation des parseurs
from ..parsers.rule_parser import RuleParser

# Importation des convertisseurs
from ..converters.traffic_flow_converter import TrafficFlowConverter
from ..converters.rule_converter import RuleConverter

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
        if not filename.endswith(('.json', '.csv', '.xlsx')):
            filename += '.json' if format_type.lower() == 'json' else '.csv'
        
        # If the filename is not an absolute path, put it in the outputs directory
        if not os.path.isabs(filename):
            filename = get_file_path(os.path.basename(filename), 'output')
        
        # Process raw flows for export - utiliser le parseur pour normaliser les données
        processed_flows = TrafficResultProcessor.process_raw_flows(flows)
        
        try:
            if format_type.lower() == 'json':
                return self._export_to_json(processed_flows, filename)
            elif format_type.lower() == 'csv':
                return self._export_to_csv(processed_flows, filename)
            elif format_type.lower() == 'excel' or filename.endswith('.xlsx'):
                # Extract rule hrefs to get detailed rules information
                rule_hrefs = self.extract_rule_hrefs(processed_flows)
                rule_details = self.get_rule_details(rule_hrefs)
                
                return self._export_to_excel(processed_flows, filename, rule_details)
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
            # Define CSV columns based on the traffic flow converter's field schema
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
                    # Convertir le flux en format d'export CSV
                    csv_row = self._format_flow_for_csv(flow, fieldnames)
                    writer.writerow(csv_row)
            
            print(f"✅ Export CSV terminé. Fichier sauvegardé: {filename}")
            return True
        except Exception as e:
            print(f"Erreur lors de l'export CSV: {e}")
            return False
            
    def _export_to_excel(self, flows: List[Dict[str, Any]], filename: str, rule_details: List[Dict[str, Any]]) -> bool:
        """
        Export flows to Excel format with rules details in a second sheet.
        
        Args:
            flows (list): Processed traffic flows
            filename (str): Output Excel filename
            rule_details (list): List of detailed rule information
            
        Returns:
            bool: True if export successful
        """
        try:
            # Ensure the filename has the .xlsx extension
            if not filename.endswith('.xlsx'):
                filename = filename.replace('.csv', '.xlsx')
                if not filename.endswith('.xlsx'):
                    filename += '.xlsx'
            
            # Create a DataFrame for the flows
            flow_rows = []
            for flow in flows:
                flow_row = {
                    'Source IP': flow.get('src_ip'),
                    'Source Workload': flow.get('src_workload_id'),
                    'Destination IP': flow.get('dst_ip'),
                    'Destination Workload': flow.get('dst_workload_id'),
                    'Service': flow.get('service_name'),
                    'Port': flow.get('service_port'),
                    'Protocol': flow.get('service_protocol'),
                    'Policy Decision': flow.get('policy_decision'),
                    'Flow Direction': flow.get('flow_direction'),
                    'Connections': flow.get('num_connections'),
                    'First Detected': flow.get('first_detected'),
                    'Last Detected': flow.get('last_detected'),
                    'Rule HREF': flow.get('rule_href'),
                    'Rule Name': flow.get('rule_name')
                }
                
                # Add any Excel metadata if present
                if 'excel_metadata' in flow:
                    meta = flow['excel_metadata']
                    flow_row.update({
                        'Source Excel IP': meta.get('source_ip'),
                        'Destination Excel IP': meta.get('dest_ip'),
                        'Excel Protocol': meta.get('protocol'),
                        'Excel Port': meta.get('port'),
                        'Excel Row': meta.get('excel_row')
                    })
                
                flow_rows.append(flow_row)
            
            flows_df = pd.DataFrame(flow_rows)
            
            # Create a writer for the Excel file
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Write the flows to the first sheet
                flows_df.to_excel(writer, sheet_name='Flux de trafic', index=False)
                
                # Create the rules sheet if we have rule details
                if rule_details:
                    self.export_rules_to_excel_sheet(writer, rule_details)
            
            print(f"✅ Export Excel terminé. Fichier sauvegardé: {filename}")
            return True
            
        except ImportError:
            print("❌ Erreur: Modules pandas ou openpyxl non disponibles.")
            print("   Installez-les avec: pip install pandas openpyxl")
            return False
        except Exception as e:
            print(f"❌ Erreur lors de l'export Excel: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _format_flow_for_csv(self, flow: Dict[str, Any], fieldnames: List[str]) -> Dict[str, Any]:
        """
        Format a flow for CSV export, extracting only the specified fields.
        
        Args:
            flow (dict): Flow to format
            fieldnames (list): List of field names to extract
            
        Returns:
            Dictionary ready for CSV writing
        """
        # Extract only the specified fields
        csv_row = {field: flow.get(field, '') for field in fieldnames}
        return csv_row
    
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
        
        # Process the flows using the parser
        processed_flows = TrafficResultProcessor.process_raw_flows(flows)
        
        # Generate default filename if not provided
        if not output_file:
            output_dir = get_output_dir()
            output_file = os.path.join(output_dir, f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}")
        
        # Extract rule hrefs for enhanced detail if exporting to Excel
        rule_hrefs = []
        rule_details = []
        if format_type.lower() == 'excel' or output_file.endswith('.xlsx'):
            rule_hrefs = self.extract_rule_hrefs(processed_flows)
            rule_details = self.get_rule_details(rule_hrefs)
        
        # Perform export
        if format_type.lower() == 'excel' or output_file.endswith('.xlsx'):
            return self._export_to_excel(processed_flows, output_file, rule_details)
        else:
            return self.export_flows(processed_flows, output_file, format_type)
    
    def extract_rule_hrefs(self, flows: List[Dict[str, Any]]) -> List[str]:
        """
        Extrait tous les hrefs uniques des règles à partir des flux de trafic.
        
        Args:
            flows (list): Liste des flux de trafic
            
        Returns:
            list: Liste des hrefs uniques des règles
        """
        # Utiliser le parseur de règles pour extraire les hrefs
        return RuleParser.extract_rule_hrefs(flows)
    
    def get_rule_details(self, rule_hrefs: List[str]) -> List[Dict[str, Any]]:
        """
        Récupère les détails des règles à partir de leurs hrefs.
        
        Args:
            rule_hrefs (list): Liste des hrefs des règles
            
        Returns:
            list: Liste des détails de règles
        """
        # Essayer d'abord de récupérer les règles depuis la base de données
        rules = []
        
        if hasattr(self.db, 'get_rules_by_hrefs'):
            rules = self.db.get_rules_by_hrefs(rule_hrefs)
        
        # Si certaines règles n'ont pas été trouvées, essayer avec l'API
        if len(rules) < len(rule_hrefs):
            # Déterminer quels hrefs manquent
            found_hrefs = set()
            for rule in rules:
                if rule and 'raw_data' in rule and rule['raw_data']:
                    # Extraire le href en utilisant le parseur
                    href = None
                    if isinstance(rule['raw_data'], str):
                        try:
                            raw_data = json.loads(rule['raw_data'])
                            href = raw_data.get('href')
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(rule['raw_data'], dict):
                        href = rule['raw_data'].get('href')
                    
                    if href:
                        found_hrefs.add(href)
            
            missing_hrefs = [href for href in rule_hrefs if href not in found_hrefs]
            
            # Récupérer les règles manquantes depuis l'API
            for href in missing_hrefs:
                try:
                    raw_rule = self.api.get_rule_by_href(href)
                    if raw_rule:
                        # Convertir la règle en format de base de données
                        rule = RuleConverter.from_dict(raw_rule)
                        rules.append(rule)
                except Exception as e:
                    print(f"Erreur lors de la récupération de la règle {href}: {e}")
        
        return rules
    
    def export_rules_to_excel_sheet(self, writer: pd.ExcelWriter, rules: List[Dict[str, Any]]) -> bool:
        """
        Exporte les règles dans une feuille Excel.
        
        Args:
            writer (ExcelWriter): Writer pandas pour Excel
            rules (list): Liste des règles à exporter
            
        Returns:
            bool: True si l'export a réussi, False sinon
        """
        try:
            # Convertir les règles en format adapté pour Excel en utilisant les parseurs
            rule_rows = []
            for rule in rules:
                # Utiliser le convertisseur de règles pour normaliser les données
                normalized_rule = RuleConverter.from_dict(rule)
                
                # Créer une ligne pour chaque règle
                rule_row = {
                    'rule_id': normalized_rule.get('id', 'N/A'),
                    'description': normalized_rule.get('description', 'Pas de description'),
                    'enabled': 'Oui' if normalized_rule.get('enabled', False) else 'Non',
                    'href': normalized_rule.get('href', 'N/A')
                }
                
                # Formater les providers, consumers et services
                providers = normalized_rule.get('providers', [])
                consumers = normalized_rule.get('consumers', [])
                services = normalized_rule.get('services', [])
                
                provider_descriptions = [f"{p.get('type')}:{p.get('value')}" for p in providers if p.get('type') and p.get('value')]
                consumer_descriptions = [f"{c.get('type')}:{c.get('value')}" for c in consumers if c.get('type') and c.get('value')]
                service_descriptions = []
                
                for service in services:
                    service_type = service.get('type')
                    if service_type == 'service':
                        service_descriptions.append(f"Service: {service.get('name', service.get('id', 'N/A'))}")
                    elif service_type == 'proto':
                        proto = service.get('proto')
                        port = service.get('port')
                        port_text = f":{port}" if port else ""
                        service_descriptions.append(f"Proto {proto}{port_text}")
                
                rule_row['providers'] = '; '.join(provider_descriptions) if provider_descriptions else 'N/A'
                rule_row['consumers'] = '; '.join(consumer_descriptions) if consumer_descriptions else 'N/A'
                rule_row['services'] = '; '.join(service_descriptions) if service_descriptions else 'N/A'
                
                # Ajouter d'autres informations
                rule_row['resolve_labels_as'] = normalized_rule.get('resolve_labels_as', 'N/A')
                rule_row['sec_connect'] = 'Oui' if normalized_rule.get('sec_connect', False) else 'Non'
                rule_row['unscoped_consumers'] = 'Oui' if normalized_rule.get('unscoped_consumers', False) else 'Non'
                
                # Ajouter cette règle aux données
                rule_rows.append(rule_row)
            
            # Vérifier qu'il reste des règles à exporter
            if not rule_rows:
                print("Aucune règle n'a pu être traitée, pas de feuille 'Règles' ajoutée.")
                return False
            
            # Créer un DataFrame pour les règles
            rules_df = pd.DataFrame(rule_rows)
            
            # Définir l'ordre des colonnes
            columns_order = [
                'rule_id', 'description', 'enabled', 
                'providers', 'consumers', 'services',
                'resolve_labels_as', 'sec_connect', 'unscoped_consumers', 'href'
            ]
            
            # Réorganiser les colonnes et supprimer celles qui n'existent pas
            available_columns = [col for col in columns_order if col in rules_df.columns]
            rules_df = rules_df[available_columns]
            
            # Écrire le DataFrame dans une nouvelle feuille
            rules_df.to_excel(writer, sheet_name='Règles', index=False)
            
            print(f"✅ {len(rule_rows)} règles exportées dans la feuille 'Règles'")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'export des règles: {e}")
            import traceback
            traceback.print_exc()
            return False