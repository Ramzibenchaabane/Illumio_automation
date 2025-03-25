# illumio/traffic_analysis/export_handler.py
"""
Handles exporting traffic analysis results to various formats.
"""
import os
import csv
import json
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
        
        # Vérifier s'il y a des import CSV qui manquent
        if format_type.lower() == 'csv':
            import csv
        
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
    
    def _extract_actor_display_value(self, actor: Dict[str, Any]) -> str:
        """
        Extrait la valeur d'affichage la plus appropriée pour un acteur (provider ou consumer).
        
        Args:
            actor (dict): L'acteur dont on veut extraire la valeur d'affichage
            
        Returns:
            str: La valeur d'affichage
        """
        actor_type = actor.get('type')
        
        # Si une valeur d'affichage a déjà été déterminée, l'utiliser
        if 'display_value' in actor:
            return actor['display_value']
        
        # Sinon, extraire la valeur appropriée selon le type d'acteur
        if actor_type == 'label':
            # Pour les labels, utiliser key:value ou la valeur
            value = actor.get('value', '')
            if 'label_details' in actor:
                key = actor['label_details'].get('key', '')
                label_value = actor['label_details'].get('value', '')
                if key and label_value:
                    return f"{key}:{label_value}"
            return value
        
        elif actor_type == 'label_group':
            # Pour les groupes de labels, utiliser le nom si disponible
            if 'label_group_details' in actor and actor['label_group_details'].get('name'):
                return actor['label_group_details']['name']
            return actor.get('value', '')
        
        elif actor_type == 'workload':
            # Pour les workloads, priorité : hostname > name > id
            if 'workload_details' in actor:
                hostname = actor['workload_details'].get('hostname')
                name = actor['workload_details'].get('name')
                if hostname:
                    return hostname
                if name:
                    return name
            return actor.get('value', '')
        
        elif actor_type == 'ip_list':
            # Pour les listes d'IPs, utiliser le nom si disponible
            if 'ip_list_details' in actor and actor['ip_list_details'].get('name'):
                return actor['ip_list_details']['name']
            return actor.get('value', '')
        
        elif actor_type == 'ams':
            return 'Tous les systèmes gérés'
        
        # Par défaut, utiliser la valeur brute
        return actor.get('value', '')
    
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
                provider_values = []
                for provider in providers:
                    # Utiliser notre nouvelle méthode d'extraction
                    provider_type = provider.get('type', '')
                    display_value = self._extract_actor_display_value(provider)
                    provider_values.append(f"{provider_type}: {display_value}")
                
                rule_row['Sources'] = " | ".join(provider_values)
            else:
                rule_row['Sources'] = 'Toutes'
                
            # Format consumers (destinations)
            consumers = rule.get('consumers', [])
            if consumers:
                consumer_values = []
                for consumer in consumers:
                    # Utiliser notre nouvelle méthode d'extraction
                    consumer_type = consumer.get('type', '')
                    display_value = self._extract_actor_display_value(consumer)
                    consumer_values.append(f"{consumer_type}: {display_value}")
                
                rule_row['Destinations'] = " | ".join(consumer_values)
            else:
                rule_row['Destinations'] = 'Toutes'
                
            # Format services
            services = rule.get('services', []) or rule.get('ingress_services', [])
            if services:
                service_values = []
                for service in services:
                    if hasattr(service, 'get'):
                        service_type = service.get('type', '')
                        
                        if service_type == 'service':
                            # Priorité au nom du service dans service_details
                            if 'service_details' in service and service['service_details'].get('name'):
                                service_values.append(f"Service: {service['service_details'].get('name')}")
                            # Ensuite utiliser le nom directement dans le service
                            elif service.get('name'):
                                service_values.append(f"Service: {service.get('name')}")
                            # Fallback sur l'id
                            else:
                                service_id = service.get('id', 'N/A')
                                service_values.append(f"Service: {service_id}")
                        
                        elif service_type == 'proto':
                            proto = service.get('proto')
                            proto_name = self._protocol_to_name(proto)
                            port = service.get('port')
                            to_port = service.get('to_port')
                            
                            if port is not None and to_port is not None and port != to_port:
                                service_values.append(f"{proto_name}: {port}-{to_port}")
                            elif port is not None:
                                service_values.append(f"{proto_name}: {port}")
                            else:
                                service_values.append(f"{proto_name}")
                        
                        else:
                            # Format par défaut
                            service_values.append(str(service))
                
                rule_row['Services'] = " | ".join(service_values) if service_values else "Tous"
            else:
                rule_row['Services'] = 'Tous'
                
            # Additional rule properties
            rule_row['Resolve Labels As'] = rule.get('resolve_labels_as', 'N/A')
            rule_row['SecConnect'] = 'Oui' if rule.get('sec_connect', False) else 'Non'
            rule_row['Unscoped Consumers'] = 'Oui' if rule.get('unscoped_consumers', False) else 'Non'
            
            return rule_row
            
        except Exception as e:
            print(f"Erreur lors du formatage de la règle {rule.get('id', 'inconnue')}: {e}")
            import traceback
            traceback.print_exc()
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
                
            # Utiliser la méthode d'extraction
            display_value = self._extract_actor_display_value(actor)
                
            # Formater l'acteur avec son type et sa valeur d'affichage
            actor_descriptions.append(f"{actor_type}: {display_value}")
                
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
                # Improved service handling - display name
                name = None
                
                # Priorité au nom du service dans service_details
                if 'service_details' in service and service['service_details'].get('name'):
                    name = service['service_details'].get('name')
                # Ensuite utiliser le nom directement dans le service
                elif service.get('name'):
                    name = service.get('name')
                # Fallback sur l'id
                else:
                    service_id = service.get('id', 'N/A')
                    name = f"Service {service_id}"
                    
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
                    workload_data = response.get('data', {})
                    workload = workload_data.get('workload', {})
                
            if workload and workload.get('hostname'):
                return workload.get('hostname')
            elif workload and workload.get('name'):
                return workload.get('name')
                
            return workload_id
        except Exception:
            return workload_id
    
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
                # Amélioré pour récupérer la valeur du label
                if isinstance(actor.get('value'), str) and ':' in actor.get('value', ''):
                    key, value = actor['value'].split(':', 1)
                    
                    # Check database for label details
                    if hasattr(self.db, 'labels') and hasattr(self.db.labels, 'get_by_key_value'):
                        try:
                            response = self.db.labels.get_by_key_value(key, value)
                            if hasattr(response, 'get'):
                                label_data = response.get('data', {})
                                if 'label' in label_data:
                                    label = label_data.get('label', {})
                                    if label:
                                        actor['label_details'] = label
                                        # Store the actual value for display
                                        actor['display_value'] = label.get('value', value)
                        except Exception:
                            pass
            
            elif actor_type == 'label_group':
                # Amélioré pour récupérer le nom du groupe de labels
                if hasattr(self.db, 'label_groups') and hasattr(self.db.label_groups, 'get'):
                    try:
                        label_group_id = actor.get('value', '').split('/')[-1] if '/' in actor.get('value', '') else actor.get('value', '')
                        response = self.db.label_groups.get(label_group_id)
                        if response:
                            actor['label_group_details'] = response
                            # Store the name for display
                            if 'name' in response:
                                actor['display_value'] = response.get('name', actor.get('value', ''))
                    except Exception:
                        pass
            
            elif actor_type == 'workload':
                # Amélioré pour récupérer le hostname du workload
                if hasattr(self.db, 'workloads') and hasattr(self.db.workloads, 'get'):
                    try:
                        workload_id = actor.get('value', '').split('/')[-1] if '/' in actor.get('value', '') else actor.get('value', '')
                        response = self.db.workloads.get(workload_id)
                        if hasattr(response, 'get'):
                            workload_data = response.get('data', {})
                            workload = workload_data.get('workload', {})
                            if workload:
                                actor['workload_details'] = workload
                                # Store the hostname for display
                                hostname = workload.get('hostname')
                                if hostname:
                                    actor['display_value'] = hostname
                    except Exception:
                        pass
            
            elif actor_type == 'ip_list':
                # Amélioré pour récupérer le nom de la liste d'IPs
                if hasattr(self.db, 'ip_lists') and hasattr(self.db.ip_lists, 'get'):
                    try:
                        ip_list_id = actor.get('value', '').split('/')[-1] if '/' in actor.get('value', '') else actor.get('value', '')
                        response = self.db.ip_lists.get(ip_list_id)
                        if hasattr(response, 'get'):
                            ip_list_data = response.get('data', {})
                            ip_list = ip_list_data.get('ip_list', {})
                            if ip_list:
                                actor['ip_list_details'] = ip_list
                                # Store the name for display
                                name = ip_list.get('name')
                                if name:
                                    actor['display_value'] = name
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
                        response = self.db.services.get(service_id)
                        
                        if hasattr(response, 'get'):
                            service_data = response.get('data', {})
                            if 'service' in service_data:
                                service_details = service_data.get('service', {})
                                if service_details:
                                    service['service_details'] = service_details
                                    # Ajouter explicitement le nom pour affichage
                                    if 'name' in service_details:
                                        service['name'] = service_details['name']
                        else:
                            # Si response n'a pas de méthode get, essayer de l'utiliser directement
                            if isinstance(response, dict):
                                service['service_details'] = response
                                if 'name' in response:
                                    service['name'] = response['name']
                    except Exception as e:
                        print(f"Erreur lors de la récupération des détails du service {service_id}: {e}")
            
            enriched_services.append(service)
        
        return enriched_services
    
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