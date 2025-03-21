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
        
        # If the filename is not an absolute path, put it in the outputs directory
        if not os.path.isabs(filename):
            filename = get_file_path(os.path.basename(filename), 'output')
        
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
            output_dir = get_output_dir()
            output_file = os.path.join(output_dir, f"traffic_analysis_{query_id}_{datetime.now().strftime('%Y%m%d')}")
        
        # Perform export
        return self.export_flows(flows, output_file, format_type)
    
    def extract_rule_hrefs(self, flows):
        """
        Extrait tous les hrefs uniques des règles à partir des flux de trafic.
        
        Args:
            flows (list): Liste des flux de trafic
            
        Returns:
            list: Liste des hrefs uniques des règles
        """
        unique_rule_hrefs = set()
        
        for flow in flows:
            # Différentes façons de trouver les hrefs des règles dans différentes structures
            
            # 1. Chercher dans le champ 'rule_href'
            if isinstance(flow, dict) and 'rule_href' in flow and flow['rule_href']:
                unique_rule_hrefs.add(flow['rule_href'])
            
            # 2. Chercher dans le champ 'rules' contenant sec_policy
            if isinstance(flow, dict) and 'rules' in flow:
                rules = flow['rules']
                if isinstance(rules, dict) and 'sec_policy' in rules:
                    sec_policy = rules['sec_policy']
                    if isinstance(sec_policy, dict) and 'href' in sec_policy:
                        unique_rule_hrefs.add(sec_policy['href'])
                
                # 3. Chercher dans le champ 'rules' s'il est une liste
                elif isinstance(rules, list):
                    for rule in rules:
                        if isinstance(rule, dict) and 'href' in rule:
                            unique_rule_hrefs.add(rule['href'])
            
            # 4. Chercher dans raw_data si présent
            if isinstance(flow, dict) and 'raw_data' in flow and flow['raw_data']:
                raw_data = flow['raw_data']
                
                # Si raw_data est une chaîne JSON, la parser
                if isinstance(raw_data, str):
                    try:
                        import json
                        raw_data = json.loads(raw_data)
                    except:
                        raw_data = {}
                
                # Chercher dans rules de raw_data
                if isinstance(raw_data, dict) and 'rules' in raw_data:
                    rules = raw_data['rules']
                    if isinstance(rules, dict) and 'sec_policy' in rules:
                        sec_policy = rules['sec_policy']
                        if isinstance(sec_policy, dict) and 'href' in sec_policy:
                            unique_rule_hrefs.add(sec_policy['href'])
                    elif isinstance(rules, list):
                        for rule in rules:
                            if isinstance(rule, dict) and 'href' in rule:
                                unique_rule_hrefs.add(rule['href'])
        
        # Filtrer les valeurs non valides et les valeurs 'N/A'
        valid_hrefs = [href for href in unique_rule_hrefs if href and href != 'N/A']
        
        return valid_hrefs

    def get_rule_details(self, rule_hrefs):
        """
        Récupère les détails des règles à partir de leurs hrefs.
        
        Args:
            rule_hrefs (list): Liste des hrefs de règles
            
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
                if rule and 'raw_data' in rule and rule['raw_data'] and 'href' in rule['raw_data']:
                    found_hrefs.add(rule['raw_data']['href'])
            
            missing_hrefs = [href for href in rule_hrefs if href not in found_hrefs]
            
            # Récupérer les règles manquantes depuis l'API
            for href in missing_hrefs:
                try:
                    rule = self.api.get_rule_by_href(href)
                    if rule:
                        rules.append({
                            'raw_data': rule,
                            'id': rule.get('href', '').split('/')[-1] if rule.get('href') else None,
                            'description': rule.get('description'),
                            'enabled': rule.get('enabled'),
                            'providers': rule.get('providers'),
                            'consumers': rule.get('consumers'),
                            'ingress_services': rule.get('ingress_services')
                        })
                except Exception as e:
                    print(f"Erreur lors de la récupération de la règle {href}: {e}")
        
        return rules

    def export_rules_to_excel(self, output_file, rules):
        """
        Exporte les règles dans une feuille Excel.
        
        Args:
            output_file (str): Nom du fichier Excel (doit se terminer par .xlsx)
            rules (list): Liste des règles à exporter
            
        Returns:
            bool: True si l'export a réussi, False sinon
        """
        try:
            
            # Vérifier que le fichier est un .xlsx
            if not output_file.endswith('.xlsx'):
                output_file = output_file.replace('.csv', '.xlsx')
                if not output_file.endswith('.xlsx'):
                    output_file += '.xlsx'
            
            # Préparer les données pour le dataframe
            rules_data = []
            
            for rule in rules:
                rule_data = {}
                
                # Récupérer les données brutes ou utiliser directement le dictionnaire
                raw_data = rule.get('raw_data', rule)
                
                # Extraire des informations de base
                rule_data['rule_id'] = raw_data.get('href', '').split('/')[-1] if raw_data.get('href') else None
                rule_data['description'] = raw_data.get('description', '')
                rule_data['enabled'] = 'Oui' if raw_data.get('enabled') else 'Non'
                
                # Traiter les providers (fournisseurs)
                providers = raw_data.get('providers', [])
                provider_descriptions = []
                
                for provider in providers:
                    if 'actors' in provider and provider['actors'] == 'ams':
                        provider_descriptions.append('Tous les systèmes gérés')
                    elif 'label' in provider:
                        label = provider['label']
                        provider_descriptions.append(f"Label: {label.get('key')}:{label.get('value')}")
                    elif 'label_group' in provider:
                        provider_descriptions.append(f"Groupe de labels: {provider['label_group'].get('href', '').split('/')[-1]}")
                    elif 'workload' in provider:
                        provider_descriptions.append(f"Workload: {provider['workload'].get('href', '').split('/')[-1]}")
                    elif 'ip_list' in provider:
                        provider_descriptions.append(f"Liste IP: {provider['ip_list'].get('name', provider['ip_list'].get('href', '').split('/')[-1])}")
                
                rule_data['providers'] = '; '.join(provider_descriptions)
                
                # Traiter les consumers (consommateurs)
                consumers = raw_data.get('consumers', [])
                consumer_descriptions = []
                
                for consumer in consumers:
                    if 'actors' in consumer and consumer['actors'] == 'ams':
                        consumer_descriptions.append('Tous les systèmes gérés')
                    elif 'label' in consumer:
                        label = consumer['label']
                        consumer_descriptions.append(f"Label: {label.get('key')}:{label.get('value')}")
                    elif 'label_group' in consumer:
                        consumer_descriptions.append(f"Groupe de labels: {consumer['label_group'].get('href', '').split('/')[-1]}")
                    elif 'workload' in consumer:
                        consumer_descriptions.append(f"Workload: {consumer['workload'].get('href', '').split('/')[-1]}")
                    elif 'ip_list' in consumer:
                        consumer_descriptions.append(f"Liste IP: {consumer['ip_list'].get('name', consumer['ip_list'].get('href', '').split('/')[-1])}")
                
                rule_data['consumers'] = '; '.join(consumer_descriptions)
                
                # Traiter les services
                services = raw_data.get('ingress_services', [])
                service_descriptions = []
                
                for service in services:
                    if 'href' in service:
                        service_id = service['href'].split('/')[-1]
                        service_descriptions.append(f"Service: {service.get('name', service_id)}")
                    elif 'proto' in service:
                        proto = service['proto']
                        port = service.get('port', '')
                        port_text = f":{port}" if port else ""
                        service_descriptions.append(f"Proto {proto}{port_text}")
                
                rule_data['services'] = '; '.join(service_descriptions)
                
                # Traiter les informations supplémentaires
                rule_data['resolve_labels_as'] = raw_data.get('resolve_labels_as', '')
                rule_data['sec_connect'] = 'Oui' if raw_data.get('sec_connect') else 'Non'
                rule_data['unscoped_consumers'] = 'Oui' if raw_data.get('unscoped_consumers') else 'Non'
                rule_data['href'] = raw_data.get('href', '')
                
                # Ajouter cette règle à la liste
                rules_data.append(rule_data)
            
            # Créer un DataFrame pandas
            rules_df = pd.DataFrame(rules_data)
            
            # Définir l'ordre des colonnes
            columns_order = [
                'rule_id', 'description', 'enabled', 
                'providers', 'consumers', 'services',
                'resolve_labels_as', 'sec_connect', 'unscoped_consumers', 'href'
            ]
            
            # Réorganiser les colonnes et supprimer celles qui n'existent pas
            available_columns = [col for col in columns_order if col in rules_df.columns]
            rules_df = rules_df[available_columns]
            
            try:
                # Essayer de charger le fichier Excel existant
                book = load_workbook(output_file)
                
                # Vérifier si la feuille 'Règles' existe déjà
                if 'Règles' in book.sheetnames:
                    # Supprimer la feuille existante
                    std = book.get_sheet_by_name('Règles')
                    book.remove(std)
                
                # Enregistrer et fermer le classeur
                book.save(output_file)
                
                # Écrire le DataFrame dans une nouvelle feuille
                with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
                    rules_df.to_excel(writer, sheet_name='Règles', index=False)
            
            except FileNotFoundError:
                # Le fichier n'existe pas, créer un nouveau fichier Excel
                rules_df.to_excel(output_file, sheet_name='Règles', index=False)
            
            print(f"✅ {len(rules_data)} règles exportées dans la feuille 'Règles' du fichier {output_file}")
            return True
            
        except ImportError:
            print("❌ Erreur: Modules pandas ou openpyxl non disponibles.")
            print("   Installez-les avec: pip install pandas openpyxl")
            return False
        except Exception as e:
            print(f"❌ Erreur lors de l'export des règles: {e}")
            import traceback
            traceback.print_exc()
            return False