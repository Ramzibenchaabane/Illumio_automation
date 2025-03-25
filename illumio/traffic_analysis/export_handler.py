# illumio/traffic_analysis/export_handler.py
"""
Handles exporting traffic analysis results to various formats.
"""
import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from illumio.utils.directory_manager import get_output_dir, get_file_path

from .base_components import TrafficAnalysisBaseComponent
from .result_processing import TrafficResultProcessor

# Importation des parseurs
from ..parsers.rule_parser import RuleParser
from ..parsers.label_parser import LabelParser
from ..parsers.workload_parser import WorkloadParser
from ..parsers.ip_list_parser import IPListParser
from ..parsers.service_parser import ServiceParser

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
            format_type (str): Export format ('json', 'csv', or 'excel')
        
        Returns:
            bool: True if export successful, False otherwise
        """
        # Ensure filename has correct extension
        if not filename.endswith(('.json', '.csv', '.xlsx')):
            if format_type.lower() == 'json':
                filename += '.json'
            elif format_type.lower() == 'csv':
                filename += '.csv'
            elif format_type.lower() in ('excel', 'xlsx'):
                filename += '.xlsx'
        
        # If the filename is not an absolute path, put it in the outputs directory
        if not os.path.isabs(filename):
            filename = get_file_path(os.path.basename(filename), 'output')
        
        # Process raw flows for export - utiliser le parseur pour normaliser les données
        processed_flows = TrafficResultProcessor.process_raw_flows(flows)
        
        try:
            if format_type.lower() == 'json':
                return self._export_to_json(processed_flows, filename)
            elif format_type.lower() in ('excel', 'xlsx'):
                # Extract rule hrefs
                rule_hrefs = self.extract_rule_hrefs(processed_flows)
                # Get detailed rule information
                rule_details = self.get_detailed_rules(rule_hrefs)
                
                # Export to Excel with both sheets
                return self._export_to_excel(processed_flows, filename, rule_details)
            else:
                print(f"Format non supporté: {format_type}")
                return False
        except Exception as e:
            print(f"Erreur lors de l'export: {e}")
            import traceback
            traceback.print_exc()
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
                filename = filename.replace('.json', '.xlsx')
                if not filename.endswith('.xlsx'):
                    filename += '.xlsx'
            
            # Create a DataFrame for the flows
            flow_rows = []
            for flow in flows:
                # Get detailed workload information for source and destination
                src_workload_name = self._get_workload_hostname(flow.get('src_workload_id'))
                dst_workload_name = self._get_workload_hostname(flow.get('dst_workload_id'))
                
                flow_row = {
                    'Source IP': flow.get('src_ip'),
                    'Source Workload': src_workload_name,
                    'Destination IP': flow.get('dst_ip'),
                    'Destination Workload': dst_workload_name,
                    'Service': flow.get('service_name'),
                    'Port': flow.get('service_port'),
                    'Protocol': self._protocol_to_name(flow.get('service_protocol')),
                    'Décision': flow.get('policy_decision'),
                    'Direction': flow.get('flow_direction'),
                    'Connexions': flow.get('num_connections'),
                    'Première détection': flow.get('first_detected'),
                    'Dernière détection': flow.get('last_detected'),
                    'Règle': flow.get('rule_name'),
                    'ID Règle': flow.get('rule_href', '').split('/')[-1] if flow.get('rule_href') else ''
                }
                
                # Add any Excel metadata if present
                if 'excel_metadata' in flow:
                    meta = flow['excel_metadata']
                    flow_row.update({
                        'Source Excel IP': meta.get('source_ip'),
                        'Destination Excel IP': meta.get('dest_ip'),
                        'Excel Protocol': self._protocol_to_name(meta.get('protocol')),
                        'Excel Port': meta.get('port'),
                        'Excel Row': meta.get('excel_row')
                    })
                
                flow_rows.append(flow_row)
            
            flows_df = pd.DataFrame(flow_rows)
            
            # Prepare the rules for the second sheet
            rule_rows = []
            for rule in rule_details:
                rule_row = self._format_rule_for_excel(rule)
                if rule_row:
                    rule_rows.append(rule_row)
            
            rules_df = pd.DataFrame(rule_rows) if rule_rows else None
            
            # Create the Excel file with both sheets
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Write the flows to the first sheet
                flows_df.to_excel(writer, sheet_name='Flux de trafic', index=False)
                
                # Write the rules to the second sheet if available
                if rules_df is not None and not rules_df.empty:
                    rules_df.to_excel(writer, sheet_name='Règles', index=False)
                    print(f"✅ {len(rule_rows)} règles exportées dans la feuille 'Règles'")
                else:
                    print("ℹ️ Aucune règle détaillée n'a pu être exportée")
            
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
    
    def _format_rule_for_excel(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Format a rule for Excel export, with detailed object information.
        
        Args:
            rule (dict): Rule to format
            
        Returns:
            Dictionary ready for Excel writing or None if formatting fails
        """
        try:
            if not rule:
                return None
                
            # Basic rule information
            rule_id = rule.get('id', '')
            if not rule_id and 'href' in rule:
                rule_id = rule['href'].split('/')[-1]
                
            rule_row = {
                'ID Règle': rule_id,
                'Nom Règle': rule.get('name', ''),
                'Description': rule.get('description', 'Sans description'),
                'Activée': 'Oui' if rule.get('enabled', False) else 'Non',
            }
            
            # Format providers (sources)
            providers = rule.get('providers', [])
            if providers:
                provider_str = self._format_actors(providers)
                rule_row['Sources'] = provider_str
            else:
                rule_row['Sources'] = 'Toutes'
                
            # Format consumers (destinations)
            consumers = rule.get('consumers', [])
            if consumers:
                consumer_str = self._format_actors(consumers)
                rule_row['Destinations'] = consumer_str
            else:
                rule_row['Destinations'] = 'Toutes'
                
            # Format services
            services = rule.get('services', []) or rule.get('ingress_services', [])
            if services:
                service_str = self._format_services(services)
                rule_row['Services'] = service_str
            else:
                rule_row['Services'] = 'Tous'
            
            # Format scopes if available
            scopes = rule.get('scopes', [])
            if scopes:
                scope_str = self._format_scopes(scopes)
                rule_row['Scopes'] = scope_str
                
            # Additional rule properties
            rule_row['Resolve Labels As'] = rule.get('resolve_labels_as', 'N/A')
            rule_row['SecConnect'] = 'Oui' if rule.get('sec_connect', False) else 'Non'
            rule_row['Unscoped Consumers'] = 'Oui' if rule.get('unscoped_consumers', False) else 'Non'
            
            return rule_row
            
        except Exception as e:
            print(f"Erreur lors du formatage de la règle {rule.get('id', 'inconnue')}: {e}")
            return None

    def _format_scopes(self, scopes: List[List[Dict[str, Any]]]) -> str:
        """
        Format scope objects for display.
        
        Args:
            scopes (list): List of scope groups with labels
            
        Returns:
            Formatted string of scope information
        """
        if not scopes:
            return "Aucun"
        
        scope_groups = []
        for scope_group in scopes:
            label_descriptions = []
            for label in scope_group:
                # Extraction directe des valeurs clé/valeur du label
                key = label.get('key')
                value = label.get('value')
                
                if key is not None and value is not None:
                    # Vérifier si c'est une exclusion
                    if label.get('exclusion'):
                        label_descriptions.append(f"NON {key}:{value}")
                    else:
                        label_descriptions.append(f"{key}:{value}")
            
            if label_descriptions:
                scope_groups.append(" ET ".join(label_descriptions))
        
        return " OU ".join(scope_groups) if scope_groups else "Aucun"
    
    def _format_actors(self, actors: List[Dict[str, Any]]) -> str:
        """
        Format actor objects (providers or consumers) to display names instead of hrefs.
        Récupère les informations des labels directement depuis la base de données si nécessaire.
        
        Args:
            actors (list): List of actor objects
            
        Returns:
            Formatted string of actor names
        """
        if not actors:
            return "Aucun"
            
        actor_descriptions = []
        for actor in actors:
            actor_type = actor.get('type')
            
            if not actor_type:
                continue
                
            value = actor.get('value', '')
            
            if actor_type == 'label':
                # Extraire le href du label pour le rechercher dans la base de données
                label_href = None
                
                # Option 1: Récupérer le href directement depuis l'acteur
                if 'href' in actor:
                    label_href = actor['href']
                
                # Option 2: Extraire le href depuis raw_data
                elif 'raw_data' in actor and isinstance(actor['raw_data'], dict):
                    raw_data = actor['raw_data']
                    if 'label' in raw_data and isinstance(raw_data['label'], dict):
                        label_href = raw_data['label'].get('href')
                
                if label_href:
                    # Extraire l'ID à partir du href
                    label_id = label_href.split('/')[-1] if label_href else None
                    
                    if label_id:
                        # Rechercher le label dans la base de données
                        label_info = self._get_label_info(label_id)
                        if label_info and label_info.get('key') and label_info.get('value'):
                            actor_descriptions.append(f"Label: {label_info['key']}:{label_info['value']}")
                            continue
                
                # Si on n'a pas pu récupérer les informations du label, utiliser une valeur de secours
                actor_descriptions.append(f"Label: {value or 'Non spécifié'}")
            
            elif actor_type == 'label_group':
                # Récupérer le nom directement depuis l'acteur
                name = actor.get('name')
                if name:
                    actor_descriptions.append(f"Groupe: {name}")
                else:
                    # Fallback: Get label group from database
                    label_group_name = self._get_label_group_name(value)
                    actor_descriptions.append(f"Groupe: {label_group_name}")
            
            elif actor_type == 'workload':
                # Récupérer le hostname directement depuis l'acteur
                hostname = actor.get('hostname')
                if hostname:
                    actor_descriptions.append(f"Workload: {hostname}")
                else:
                    # Fallback: Get workload hostname
                    workload_hostname = self._get_workload_hostname_from_value(value)
                    actor_descriptions.append(f"Workload: {workload_hostname}")
            
            elif actor_type == 'ip_list':
                # Récupérer le nom directement depuis l'acteur
                name = actor.get('name')
                if name:
                    actor_descriptions.append(f"IP List: {name}")
                else:
                    # Fallback: Get IP list name
                    ip_list_name = self._get_ip_list_name(value)
                    actor_descriptions.append(f"IP List: {ip_list_name}")
            
            elif actor_type == 'ams':
                actor_descriptions.append("Tous les systèmes gérés")
            
            else:
                actor_descriptions.append(f"{actor_type}: {value}")
        
        return " | ".join(actor_descriptions) if actor_descriptions else "Aucun"
        
    def _get_label_info(self, label_id: str) -> Dict[str, str]:
        """
        Récupère les informations d'un label depuis la base de données.
        
        Args:
            label_id (str): ID du label
            
        Returns:
            dict: Information du label avec 'key' et 'value'
        """
        if not label_id:
            return {}
            
        try:
            # Récupérer le label depuis la base de données
            conn, cursor = self.db.connect()
            
            cursor.execute('''
            SELECT key, value FROM labels WHERE id = ?
            ''', (label_id,))
            
            row = cursor.fetchone()
            self.db.close(conn)
            
            if row:
                return {
                    'key': row['key'],
                    'value': row['value']
                }
                
            return {}
            
        except Exception as e:
            print(f"Erreur lors de la récupération du label {label_id}: {e}")
            return {}
    
    def _format_services(self, services: List[Dict[str, Any]]) -> str:
        """
        Format service objects to display names and port information.
        
        Args:
            services (list): List of service objects
            
        Returns:
            Formatted string of service information
        """
        if not services:
            return "Aucun"
            
        service_descriptions = []
        for service in services:
            service_type = service.get('type')
            
            if service_type == 'service':
                # Get service name from database or use fallback
                service_name = self._get_service_name(service.get('id')) or service.get('name', service.get('id', 'N/A'))
                service_descriptions.append(f"Service: {service_name}")
                
            elif service_type == 'proto':
                # Format protocol and port
                proto = service.get('proto')
                proto_name = self._protocol_to_name(proto)
                port = service.get('port')
                to_port = service.get('to_port')
                
                if port and to_port and port != to_port:
                    service_descriptions.append(f"{proto_name}: {port}-{to_port}")
                elif port:
                    service_descriptions.append(f"{proto_name}: {port}")
                else:
                    service_descriptions.append(f"{proto_name}")
                    
            else:
                # Default format for unknown services
                service_descriptions.append(str(service))
                
        return " | ".join(service_descriptions) if service_descriptions else "Aucun"
    
    def _protocol_to_name(self, proto: Optional[int]) -> str:
        """
        Convert protocol number to protocol name.
        
        Args:
            proto (int): Protocol number
            
        Returns:
            Protocol name or the original number as string
        """
        if proto is None:
            return "N/A"
            
        protocol_map = {
            1: "ICMP",
            6: "TCP",
            17: "UDP"
        }
        
        return protocol_map.get(proto, str(proto))
    
    def _get_workload_hostname(self, workload_id: Optional[str]) -> str:
        """
        Get workload hostname from workload ID.
        
        Args:
            workload_id (str): Workload ID
            
        Returns:
            Workload hostname or ID if not found
        """
        if not workload_id:
            return "N/A"
            
        try:
            # Try to get workload from database
            conn, cursor = self.db.connect()
            
            cursor.execute('''
            SELECT hostname, name FROM workloads WHERE id = ?
            ''', (workload_id,))
            
            row = cursor.fetchone()
            self.db.close(conn)
            
            if row:
                # Prefer hostname over name
                if row['hostname']:
                    return row['hostname']
                elif row['name']:
                    return row['name']
                
            return workload_id
            
        except Exception as e:
            print(f"Erreur lors de la récupération du workload {workload_id}: {e}")
            return workload_id

    def _get_workload_hostname_from_value(self, value: str) -> str:
        """
        Get workload hostname from value which might be href or ID.
        
        Args:
            value (str): Workload value from actor (href or ID)
            
        Returns:
            Workload hostname or original value if not found
        """
        # Extract ID from href if necessary
        workload_id = value
        if '/' in value:
            workload_id = value.split('/')[-1]
            
        return self._get_workload_hostname(workload_id)
    
    def _get_label_group_name(self, value: str) -> str:
        """
        Get label group name from value which might be href or ID.
        
        Args:
            value (str): Label group value from actor (href or ID)
            
        Returns:
            Label group name or original value if not found
        """
        if not value:
            return "N/A"
            
        # Extract ID from href if necessary
        label_group_id = value
        if '/' in value:
            label_group_id = value.split('/')[-1]
            
        try:
            # Try to get label group from database
            conn, cursor = self.db.connect()
            
            cursor.execute('''
            SELECT name FROM label_groups WHERE id = ?
            ''', (label_group_id,))
            
            row = cursor.fetchone()
            self.db.close(conn)
            
            if row and row['name']:
                return row['name']
                
            return value
            
        except Exception as e:
            print(f"Erreur lors de la récupération du groupe de labels {label_group_id}: {e}")
            return value
    
    def _get_ip_list_name(self, value: str) -> str:
        """
        Get IP list name from value which might be href or ID.
        
        Args:
            value (str): IP List value from actor (href or ID)
            
        Returns:
            IP list name or original value if not found
        """
        if not value:
            return "N/A"
            
        # Extract ID from href if necessary
        ip_list_id = value
        if '/' in value:
            ip_list_id = value.split('/')[-1]
            
        try:
            # Try to get IP list from database
            conn, cursor = self.db.connect()
            
            cursor.execute('''
            SELECT name FROM ip_lists WHERE id = ?
            ''', (ip_list_id,))
            
            row = cursor.fetchone()
            self.db.close(conn)
            
            if row and row['name']:
                return row['name']
                
            return value
            
        except Exception as e:
            print(f"Erreur lors de la récupération de l'IP list {ip_list_id}: {e}")
            return value
    
    def _get_service_name(self, service_id: Optional[str]) -> Optional[str]:
        """
        Get service name from service ID.
        
        Args:
            service_id (str): Service ID
            
        Returns:
            Service name or None if not found
        """
        if not service_id:
            return None
            
        try:
            # Try to get service from database
            conn, cursor = self.db.connect()
            
            cursor.execute('''
            SELECT name FROM services WHERE id = ?
            ''', (service_id,))
            
            row = cursor.fetchone()
            self.db.close(conn)
            
            if row and row['name']:
                return row['name']
                
            return None
            
        except Exception as e:
            print(f"Erreur lors de la récupération du service {service_id}: {e}")
            return None
    
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
    
    def get_detailed_rules(self, rule_hrefs: List[str]) -> List[Dict[str, Any]]:
        """
        Récupère les détails complets des règles à partir de leurs hrefs depuis la base de données locale.
        Cette version mise à jour s'assure que les informations de label sont correctement préservées.
        
        Args:
            rule_hrefs (list): Liste des hrefs des règles
            
        Returns:
            list: Liste des règles avec détails complets
        """
        if not rule_hrefs:
            return []
        
        # Ne récupérer les règles que depuis la base de données locale
        detailed_rules = []
        
        try:
            # Récupérer toutes les règles par leurs hrefs en une seule opération
            if hasattr(self.db, 'get_rules_by_hrefs'):
                rules = self.db.get_rules_by_hrefs(rule_hrefs)
                
                # Transformation finale des règles pour l'affichage
                for rule in rules:
                    try:
                        # Vérifier si la règle contient des données brutes
                        if 'raw_data' in rule and rule['raw_data']:
                            # Si raw_data est une chaîne JSON, la parser
                            if isinstance(rule['raw_data'], str):
                                try:
                                    raw_data = json.loads(rule['raw_data'])
                                    
                                    # Utilisation directe des données brutes pour le parsing
                                    normalized_rule = RuleParser.parse_rule(raw_data)
                                    
                                    if normalized_rule:
                                        detailed_rules.append(normalized_rule)
                                except json.JSONDecodeError as e:
                                    normalized_rule = RuleParser.parse_rule(rule)
                                    if normalized_rule:
                                        detailed_rules.append(normalized_rule)
                            else:
                                # Si raw_data est déjà un objet
                                normalized_rule = RuleParser.parse_rule(rule['raw_data'])
                                if normalized_rule:
                                    detailed_rules.append(normalized_rule)
                        else:
                            # Si pas de raw_data, utiliser la règle directement
                            normalized_rule = RuleParser.parse_rule(rule)
                            if normalized_rule:
                                detailed_rules.append(normalized_rule)
                    except Exception as e:
                        print(f"Erreur lors du traitement de la règle {rule.get('id', 'unknown')}: {e}")
            else:
                print("Warning: Database doesn't support get_rules_by_hrefs method")
        except Exception as e:
            import traceback
            print(f"Error retrieving rules from database: {e}")
            traceback.print_exc()
            
        return detailed_rules
    
    def export_query_results(self, 
                             query_id: str, 
                             format_type: str = 'json', 
                             output_file: Optional[str] = None) -> bool:
        """
        Export results for a specific traffic query.
        
        Args:
            query_id (str): ID of the traffic query
            format_type (str): Export format ('json', 'csv', or 'excel')
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
        
        # For Excel exports, we need rule details
        if format_type.lower() in ('excel', 'xlsx') or output_file.endswith('.xlsx'):
            # Extract rule hrefs
            rule_hrefs = self.extract_rule_hrefs(processed_flows)
            # Get detailed rule information from the database
            rule_details = self.get_detailed_rules(rule_hrefs)
            
            # Export to Excel with both sheets
            return self._export_to_excel(processed_flows, output_file, rule_details)
        else:
            # Export to other formats
            return self.export_flows(processed_flows, output_file, format_type)