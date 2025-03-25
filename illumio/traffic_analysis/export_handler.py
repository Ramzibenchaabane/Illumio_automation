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
            elif format_type.lower() == 'csv':
                return self._export_to_csv(processed_flows, filename)
            elif format_type.lower() in ('excel', 'xlsx'):
                # Extract rule hrefs to get detailed rules information
                rule_hrefs = self.extract_rule_hrefs(processed_flows)
                # Get detailed rule information with all associated objects
                rule_details = self.get_detailed_rules(rule_hrefs)
                
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
                filename = filename.replace('.json', '.xlsx')
                if not filename.endswith('.xlsx'):
                    filename += '.xlsx'
            
            # Create a DataFrame for the flows
            flow_rows = []
            for flow in flows:
                flow_row = {
                    'Source IP': flow.get('src_ip'),
                    'Source Workload': self._get_workload_name(flow.get('src_workload_id')),
                    'Destination IP': flow.get('dst_ip'),
                    'Destination Workload': self._get_workload_name(flow.get('dst_workload_id')),
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
                
            # Additional rule properties
            rule_row['Resolve Labels As'] = rule.get('resolve_labels_as', 'N/A')
            rule_row['SecConnect'] = 'Oui' if rule.get('sec_connect', False) else 'Non'
            rule_row['Unscoped Consumers'] = 'Oui' if rule.get('unscoped_consumers', False) else 'Non'
            
            return rule_row
            
        except Exception as e:
            print(f"Erreur lors du formatage de la règle {rule.get('id', 'inconnue')}: {e}")
            return None
    
    def _format_actors(self, actors: List[Dict[str, Any]]) -> str:
        """
        Format actor objects (providers or consumers) to display names instead of hrefs.
        
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
                # Get label key:value
                if ':' in value:
                    actor_descriptions.append(f"Label: {value}")
                else:
                    actor_descriptions.append(f"Label: {value}")
                    
            elif actor_type == 'label_group':
                # Get label group name
                actor_descriptions.append(f"Groupe: {value}")
                
            elif actor_type == 'workload':
                # Get workload name
                actor_descriptions.append(f"Workload: {value}")
                
            elif actor_type == 'ip_list':
                # Get IP list name
                actor_descriptions.append(f"IP List: {value}")
                
            elif actor_type == 'ams':
                actor_descriptions.append("Tous les systèmes gérés")
                
            else:
                actor_descriptions.append(f"{actor_type}: {value}")
                
        return " | ".join(actor_descriptions) if actor_descriptions else "Aucun"
    
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
                # Format service name
                name = service.get('name', service.get('id', 'N/A'))
                service_descriptions.append(f"Service: {name}")
                
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
    
    def _get_workload_name(self, workload_id: Optional[str]) -> str:
        """
        Get workload name from workload ID.
        
        Args:
            workload_id (str): Workload ID
            
        Returns:
            Workload name or ID if not found
        """
        if not workload_id:
            return "N/A"
            
        try:
            # Try to get workload from database
            workload = None
            if hasattr(self.db, 'workloads') and hasattr(self.db.workloads, 'get'):
                response = self.db.workloads.get(workload_id)
                if hasattr(response, 'get'):
                    workload = response.get('data', {}).get('workload', {})
                
            if workload and workload.get('name'):
                return workload.get('name')
            elif workload and workload.get('hostname'):
                return workload.get('hostname')
                
            return workload_id
        except Exception:
            return workload_id
    
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
            # Get detailed rule information
            rule_details = self.get_detailed_rules(rule_hrefs)
            
            # Export to Excel with both sheets
            return self._export_to_excel(processed_flows, output_file, rule_details)
        else:
            # Export to other formats
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
    
    def get_detailed_rules(self, rule_hrefs: List[str]) -> List[Dict[str, Any]]:
        """
        Récupère les détails complets des règles, y compris les objets associés (labels, workloads, etc.).
        
        Args:
            rule_hrefs (list): Liste des hrefs des règles
            
        Returns:
            list: Liste des règles avec les détails des objets
        """
        # Récupérer les règles de base
        basic_rules = self.get_rule_details(rule_hrefs)
        detailed_rules = []
        
        for rule in basic_rules:
            try:
                # Convertir la règle en un format normalisé
                if 'raw_data' in rule and rule['raw_data']:
                    # Si raw_data est une chaîne JSON, la convertir en dictionnaire
                    if isinstance(rule['raw_data'], str):
                        try:
                            rule_data = json.loads(rule['raw_data'])
                        except json.JSONDecodeError:
                            rule_data = rule
                    else:
                        rule_data = rule['raw_data']
                else:
                    rule_data = rule
                
                # Utiliser le parseur pour normaliser la règle
                normalized_rule = RuleParser.parse_rule(rule_data)
                
                # Enrichir les acteurs (providers et consumers) avec les noms d'objets
                if 'providers' in normalized_rule:
                    normalized_rule['providers'] = self._enrich_actors(normalized_rule['providers'])
                
                if 'consumers' in normalized_rule:
                    normalized_rule['consumers'] = self._enrich_actors(normalized_rule['consumers'])
                
                # Enrichir les services avec plus de détails
                if 'services' in normalized_rule:
                    normalized_rule['services'] = self._enrich_services(normalized_rule['services'])
                
                detailed_rules.append(normalized_rule)
            except Exception as e:
                print(f"Erreur lors de l'enrichissement de la règle {rule.get('id', 'inconnue')}: {e}")
                # Ajouter la règle non enrichie
                detailed_rules.append(rule)
        
        return detailed_rules
    
    def _enrich_actors(self, actors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrichit les acteurs (providers ou consumers) avec les noms d'objets.
        
        Args:
            actors (list): Liste des acteurs
            
        Returns:
            list: Liste des acteurs enrichis
        """
        enriched_actors = []
        
        for actor in actors:
            actor_type = actor.get('type')
            
            if actor_type == 'label':
                # Enrichir avec les détails du label
                if hasattr(self.db, 'labels') and hasattr(self.db.labels, 'get_by_key_value'):
                    try:
                        if ':' in actor.get('value', ''):
                            key, value = actor['value'].split(':', 1)
                            response = self.db.labels.get_by_key_value(key, value)
                            if hasattr(response, 'get'):
                                label = response.get('data', {}).get('label', {})
                                if label:
                                    actor['label_details'] = label
                    except Exception:
                        pass
            
            elif actor_type == 'label_group':
                # Enrichir avec les détails du groupe de labels
                if hasattr(self.db, 'label_groups') and hasattr(self.db.label_groups, 'get'):
                    try:
                        label_group_id = actor.get('value', '').split('/')[-1] if '/' in actor.get('value', '') else actor.get('value', '')
                        label_group = self.db.label_groups.get(label_group_id)
                        if label_group:
                            actor['label_group_details'] = label_group
                    except Exception:
                        pass
            
            elif actor_type == 'workload':
                # Enrichir avec les détails du workload
                if hasattr(self.db, 'workloads') and hasattr(self.db.workloads, 'get'):
                    try:
                        workload_id = actor.get('value', '').split('/')[-1] if '/' in actor.get('value', '') else actor.get('value', '')
                        response = self.db.workloads.get(workload_id)
                        if hasattr(response, 'get'):
                            workload = response.get('data', {}).get('workload', {})
                            if workload:
                                actor['workload_details'] = workload
                    except Exception:
                        pass
            
            elif actor_type == 'ip_list':
                # Enrichir avec les détails de la liste d'IPs
                if hasattr(self.db, 'ip_lists') and hasattr(self.db.ip_lists, 'get'):
                    try:
                        ip_list_id = actor.get('value', '').split('/')[-1] if '/' in actor.get('value', '') else actor.get('value', '')
                        response = self.db.ip_lists.get(ip_list_id)
                        if hasattr(response, 'get'):
                            ip_list = response.get('data', {}).get('ip_list', {})
                            if ip_list:
                                actor['ip_list_details'] = ip_list
                    except Exception:
                        pass
            
            enriched_actors.append(actor)
        
        return enriched_actors
    
    def _enrich_services(self, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrichit les services avec plus de détails.
        
        Args:
            services (list): Liste des services
            
        Returns:
            list: Liste des services enrichis
        """
        enriched_services = []
        
        for service in services:
            service_type = service.get('type')
            
            if service_type == 'service':
                # Enrichir avec les détails du service
                if hasattr(self.db, 'services') and hasattr(self.db.services, 'get'):
                    try:
                        service_id = service.get('id', '')
                        service_details = self.db.services.get(service_id)
                        if service_details:
                            service['service_details'] = service_details
                    except Exception:
                        pass
            
            enriched_services.append(service)
        
        return enriched_services