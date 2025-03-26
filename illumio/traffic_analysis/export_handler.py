# illumio/traffic_analysis/export_handler.py
"""
Handles exporting traffic analysis results to various formats.
"""
import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple, Union
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
# Import du nouveau parser pour les groupes de labels
from ..parsers.label_group_parser import LabelGroupParser

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
                # Get detailed workload information for source and destination using our unified method
                src_workload_info = self._get_entity_details('workload', flow.get('src_workload_id'))
                dst_workload_info = self._get_entity_details('workload', flow.get('dst_workload_id'))
                
                # Get display names using the workload parser
                src_workload_name = WorkloadParser.get_workload_display_name(src_workload_info)
                dst_workload_name = WorkloadParser.get_workload_display_name(dst_workload_info)
                
                # Préparer les informations de règles (nouveau: format liste)
                rule_names = []
                rule_ids = []
                
                # Option 1: Règles au format liste (nouveau format)
                if 'rules' in flow and isinstance(flow['rules'], list):
                    for rule in flow['rules']:
                        if isinstance(rule, dict):
                            if rule.get('name'):
                                rule_names.append(rule.get('name'))
                            
                            if rule.get('href'):
                                rule_id = rule.get('href', '').split('/')[-1]
                                if rule_id:
                                    rule_ids.append(rule_id)
                
                # Option 2: Règle unique (format legacy pour compatibilité)
                elif flow.get('rule_name') or flow.get('rule_href'):
                    if flow.get('rule_name'):
                        rule_names.append(flow.get('rule_name'))
                    
                    if flow.get('rule_href'):
                        rule_id = flow.get('rule_href', '').split('/')[-1]
                        if rule_id:
                            rule_ids.append(rule_id)
                
                # Joindre les noms et IDs avec des séparateurs pour l'affichage
                rule_names_str = " | ".join(rule_names) if rule_names else ""
                rule_ids_str = " | ".join(rule_ids) if rule_ids else ""
                
                flow_row = {
                    'Source IP': flow.get('src_ip'),
                    'Source Workload': src_workload_name,
                    'Destination IP': flow.get('dst_ip'),
                    'Destination Workload': dst_workload_name,
                    'Service': flow.get('service_name'),
                    'Port': flow.get('service_port'),
                    'Protocol': ServiceParser.protocol_to_name(flow.get('service_protocol')),
                    'Décision': flow.get('policy_decision'),
                    'Direction': flow.get('flow_direction'),
                    'Connexions': flow.get('num_connections'),
                    'Première détection': flow.get('first_detected'),
                    'Dernière détection': flow.get('last_detected'),
                    'Règles': rule_names_str,
                    'IDs Règles': rule_ids_str
                }
                
                # Add any Excel metadata if present
                if 'excel_metadata' in flow:
                    meta = flow['excel_metadata']
                    flow_row.update({
                        'Source Excel IP': meta.get('source_ip'),
                        'Destination Excel IP': meta.get('dest_ip'),
                        'Excel Protocol': ServiceParser.protocol_to_name(meta.get('protocol')),
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
                        # Récupérer les informations du label via la méthode unifiée
                        label_info = self._get_entity_details('label', label_id)
                        
                        # Utiliser le parseur pour formater l'affichage
                        display_text = LabelParser.format_label_for_display(label_info)
                        actor_descriptions.append(f"Label: {display_text}")
                        continue
                
                    # Si on n'a pas pu récupérer les informations du label, utiliser une valeur de secours
                actor_descriptions.append(f"Label: {value or 'Non spécifié'}")
            
            elif actor_type == 'label_group':
                # Récupérer le nom directement depuis l'acteur
                name = actor.get('name')
                if name:
                    actor_descriptions.append(f"Groupe: {name}")
                else:
                    # Extraire l'ID à partir du href ou utiliser la valeur directe
                    label_group_id = None
                    if 'href' in actor:
                        label_group_id = actor['href'].split('/')[-1]
                    else:
                        label_group_id = value
                    
                    # Récupérer les informations du groupe de labels via la méthode unifiée
                    label_group_info = self._get_entity_details('label_group', label_group_id)
                    
                    # Utiliser le parseur pour formater l'affichage
                    display_text = LabelGroupParser.get_label_group_display_name(label_group_info)
                    actor_descriptions.append(f"Groupe: {display_text}")
            
            elif actor_type == 'workload':
                # Récupérer le hostname directement depuis l'acteur
                hostname = actor.get('hostname')
                if hostname:
                    actor_descriptions.append(f"Workload: {hostname}")
                else:
                    # Extraire l'ID à partir du href ou utiliser la valeur directe
                    workload_id = None
                    if 'href' in actor:
                        workload_id = actor['href'].split('/')[-1]
                    else:
                        workload_id = value
                    
                    # Récupérer les informations du workload via la méthode unifiée
                    workload_info = self._get_entity_details('workload', workload_id)
                    
                    # Utiliser le parseur pour formater l'affichage
                    display_text = WorkloadParser.get_workload_display_name(workload_info)
                    actor_descriptions.append(f"Workload: {display_text}")
            
            elif actor_type == 'ip_list':
                # Récupérer le nom directement depuis l'acteur
                name = actor.get('name')
                if name:
                    actor_descriptions.append(f"IP List: {name}")
                else:
                    # Extraire l'ID à partir du href ou utiliser la valeur directe
                    ip_list_id = None
                    if 'href' in actor:
                        ip_list_id = actor['href'].split('/')[-1]
                    else:
                        ip_list_id = value
                    
                    # Récupérer les informations de la liste d'IP via la méthode unifiée
                    ip_list_info = self._get_entity_details('ip_list', ip_list_id)
                    
                    # Utiliser le parseur pour formater l'affichage
                    display_text = IPListParser.get_ip_list_display_name(ip_list_info)
                    actor_descriptions.append(f"IP List: {display_text}")
            
            elif actor_type == 'ams':
                actor_descriptions.append("Tous les systèmes gérés")
            
            else:
                actor_descriptions.append(f"{actor_type}: {value}")
        
        return " | ".join(actor_descriptions) if actor_descriptions else "Aucun"
    
    def _get_entity_details(self, entity_type: str, entity_id: Optional[str]) -> Union[Dict[str, Any], str, None]:
        """
        Récupère les détails d'une entité en fonction de son type et de son ID.
        Utilise les parseurs appropriés pour normaliser les données.
        
        Args:
            entity_type (str): Type d'entité ('label', 'workload', 'service', 'ip_list', 'label_group')
            entity_id (str): ID de l'entité
            
        Returns:
            Union[Dict[str, Any], str, None]: Détails de l'entité ou valeur par défaut
        """
        if not entity_id:
            return "N/A" if entity_type == 'workload' else None
        
        try:
            # Utiliser le parseur approprié en fonction du type d'entité
            if entity_type == 'label':
                return LabelParser.get_label_info_from_database(self.db, entity_id)
                
            elif entity_type == 'workload':
                return WorkloadParser.get_workload_info_from_database(self.db, entity_id)
                
            elif entity_type == 'service':
                return ServiceParser.get_service_info_from_database(self.db, entity_id)
                
            elif entity_type == 'ip_list':
                return IPListParser.get_ip_list_info_from_database(self.db, entity_id)
                
            elif entity_type == 'label_group':
                return LabelGroupParser.get_label_group_info_from_database(self.db, entity_id)
            
            # Type d'entité non pris en charge
            return None
            
        except Exception as e:
            print(f"Erreur lors de la récupération de l'entité {entity_type} {entity_id}: {e}")
            if entity_type == 'workload':
                return entity_id
            return None
        
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
                # Extraire l'ID du service
                service_id = service.get('id')
                if not service_id and 'href' in service:
                    service_id = service['href'].split('/')[-1]
                
                # Récupérer les informations du service via la méthode unifiée
                service_info = self._get_entity_details('service', service_id)
                
                # Utiliser le parseur pour formater l'affichage
                display_text = ServiceParser.get_service_display_name(service_info)
                service_descriptions.append(f"Service: {display_text}")
                
            elif service_type == 'proto':
                # Format protocol and port
                proto = service.get('proto')
                proto_name = ServiceParser.protocol_to_name(proto)
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