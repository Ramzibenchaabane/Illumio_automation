# cli_modules/traffic_menu/excel_processor.py
#!/usr/bin/env python3
"""
Module pour l'analyse de trafic via l'importation de fichiers Excel.
"""
import os
import time
import json
from datetime import datetime, timedelta

import pandas as pd

from illumio.utils.directory_manager import get_input_dir, list_files, get_file_path, get_output_dir

from .common import (
    initialize_analyzer,
    print_analysis_header,
    FlowDisplayFormatter
)

def excel_import_analysis():
    """Analyse de trafic par importation d'un fichier Excel."""
    print_analysis_header("ANALYSE DE TRAFIC PAR IMPORTATION DE FICHIER EXCEL")
    
    # Obtenir le dossier d'entrée et la liste des fichiers Excel
    input_dir = get_input_dir()
    excel_files = list_files('input', extension='.xlsx') + list_files('input', extension='.xls')
    
    if not excel_files:
        print(f"Aucun fichier Excel trouvé dans le dossier {input_dir}")
        print("Veuillez y placer un fichier Excel (.xlsx ou .xls) avant de continuer.")
        return
    
    print(f"\nFichiers Excel disponibles dans {input_dir}:")
    for i, file in enumerate(excel_files, 1):
        print(f"{i}. {file}")
    
    print("\n0. Revenir au menu précédent")
    
    # Demander à l'utilisateur de choisir un fichier
    choice = input("\nVotre choix (numéro du fichier): ")
    
    if choice == '0' or not choice:
        return
    
    try:
        file_index = int(choice) - 1
        if file_index < 0 or file_index >= len(excel_files):
            print("Choix invalide.")
            return
        
        file_name = excel_files[file_index]
        file_path = os.path.join(input_dir, file_name)
        
        # Demander si l'analyse de règles approfondie doit être effectuée
        deep_analysis = input("\nEffectuer une analyse de règles approfondie ? (o/N): ").lower()
        perform_deep_analysis = deep_analysis in ('o', 'oui', 'y', 'yes')
        
        # Analyser le fichier et créer une requête d'analyse
        analyze_excel_flows(file_path, perform_deep_analysis)
    
    except ValueError:
        print("Veuillez entrer un nombre valide.")
    except Exception as e:
        print(f"Erreur: {e}")

def analyze_excel_flows(file_path, perform_deep_analysis=False):
    """
    Analyse les flux spécifiés dans un fichier Excel en traitant chaque ligne individuellement.
    
    Args:
        file_path (str): Chemin vers le fichier Excel
        perform_deep_analysis (bool): Si True, effectuer analyse de règles approfondie
    """
    try:
        print("\nChargement du fichier Excel...")
        
        # Lire le fichier Excel
        df = pd.read_excel(file_path)
        
        # Vérifier que les colonnes requises sont présentes
        required_columns = ['source', 'destination', 'protocol']
        for col in required_columns:
            if col not in df.columns:
                print(f"Erreur: La colonne '{col}' est manquante dans le fichier Excel.")
                print(f"Colonnes trouvées: {', '.join(df.columns)}")
                return
        
        # Convertir les protocoles textuels en numéros
        protocol_map = {
            'TCP': 6,
            'UDP': 17,
            'ICMP': 1
        }
        
        # Initialiser une liste pour stocker les flux à analyser
        flows = []
        
        # Parcourir les lignes du DataFrame
        for _, row in df.iterrows():
            source = str(row['source']).strip()
            destination = str(row['destination']).strip()
            
            # Gérer le protocole (texte ou nombre)
            protocol = row['protocol']
            if isinstance(protocol, str):
                protocol = protocol.upper().strip()
                protocol = protocol_map.get(protocol, None)
                if protocol is None:
                    try:
                        protocol = int(row['protocol'])
                    except ValueError:
                        print(f"Protocole invalide '{row['protocol']}' pour {source}->{destination}, ignoré.")
                        continue
            
            # Gérer le port s'il est présent
            port = None
            if 'port' in df.columns:
                try:
                    if not pd.isna(row['port']):
                        port = int(row['port'])
                        if port < 1 or port > 65535:
                            print(f"Port hors limites {port} pour {source}->{destination}, port ignoré.")
                            port = None
                except (ValueError, TypeError):
                    print(f"Port invalide '{row['port']}' pour {source}->{destination}, port ignoré.")
            
            # Ajouter ce flux à la liste
            flows.append({
                'source': source,
                'destination': destination,
                'protocol': protocol,
                'port': port
            })
        
        if not flows:
            print("Aucun flux valide trouvé dans le fichier Excel.")
            return
        
        print(f"{len(flows)} flux ont été identifiés dans le fichier Excel.")
        
        # Demander confirmation
        confirm = input("Voulez-vous lancer l'analyse de ces flux? (o/n): ").lower()
        if confirm not in ('o', 'oui', 'y', 'yes'):
            print("Analyse annulée.")
            return
        
        # Initialiser l'analyseur de trafic
        analyzer = initialize_analyzer()
        if not analyzer:
            return
        
        # Créer un timestamp unique pour cette analyse
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        all_results = []  # Pour stocker tous les résultats
        
        # Dates d'analyse définies
        start_date = "2020-03-02T01:59:41.557Z"
        # Format ISO 8601 pour end_date
        end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        print(f"\nPériode d'analyse: {start_date} à {end_date}")
        if perform_deep_analysis:
            print("L'analyse de règles approfondie sera effectuée pour chaque flux.")
        
        print("\nDémarrage de l'analyse individuelle des flux Excel...")
        
        # Analyser chaque flux individuellement comme dans l'analyse manuelle
        total_flows = len(flows)
        successful_flows = 0
        failed_flows = 0
        total_results = 0
        
        start_time = time.time()
        
        for i, flow in enumerate(flows, 1):
            source_ip = flow['source']
            dest_ip = flow['destination']
            protocol = flow['protocol']
            port = flow['port']
            
            print(f"\nAnalyse du flux {i}/{total_flows}: {source_ip} -> {dest_ip}, protocole {protocol}{f', port {port}' if port else ''}")
            
            # Créer un nom de requête spécifique
            query_name = f"Excel_{timestamp}_Flow{i}_{source_ip}_to_{dest_ip}_{protocol}"
            if port:
                query_name += f"_port{port}"
            
            # Créer une requête d'analyse pour ce flux spécifique
            query_data = {
                "query_name": query_name,
                "start_date": start_date,
                "end_date": end_date,
                "sources_destinations_query_op": "and",
                "sources": {
                    "include": [
                        [{"ip_address": source_ip}]  # Tableaux imbriqués comme requis par le schéma
                    ],
                    "exclude": []
                },
                "destinations": {
                    "include": [
                        [{"ip_address": dest_ip}]  # Tableaux imbriqués comme requis par le schéma
                    ],
                    "exclude": []
                },
                "services": {
                    "include": [
                        {
                            "proto": protocol,
                            "port": port
                        } if port else {"proto": protocol}
                    ],
                    "exclude": []
                },
                "policy_decisions": ["allowed", "potentially_blocked", "blocked"],
                "max_results": 1000
            }
            
            # Exécuter l'analyse pour ce flux
            try:
                results = analyzer.analyze(query_data=query_data, perform_deep_analysis=perform_deep_analysis)
                
                if results:
                    successful_flows += 1
                    results_count = len(results)
                    total_results += results_count
                    print(f"✅ {results_count} flux correspondants trouvés.")
                    
                    # Ajouter à notre liste de résultats globale
                    for result in results:
                        # Ajouter des métadonnées sur la requête source
                        result['excel_metadata'] = {
                            'source_ip': source_ip,
                            'dest_ip': dest_ip,
                            'protocol': protocol,
                            'port': port,
                            'excel_row': i
                        }
                        all_results.append(result)
                else:
                    failed_flows += 1
                    print(f"❌ Aucun résultat pour ce flux.")
            except Exception as e:
                failed_flows += 1
                print(f"❌ Erreur lors de l'analyse: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Résumé de l'analyse
        print("\n" + "=" * 60)
        print(f"RÉSUMÉ DE L'ANALYSE EXCEL ({duration:.2f} secondes)")
        print("=" * 60)
        print(f"Total des flux analysés     : {total_flows}")
        print(f"Flux avec des résultats     : {successful_flows}")
        print(f"Flux sans résultat          : {failed_flows}")
        print(f"Total des résultats trouvés : {total_results}")
        
        # Si nous avons des résultats, les exporter et afficher un aperçu
        if all_results:
            # Créer un nom de fichier pour l'export
            base_filename = f"excel_analysis_{timestamp}"
            export_excel_results(all_results, base_filename)
            
            # Afficher un aperçu des résultats
            print("\nAperçu des résultats:")
            FlowDisplayFormatter.format_flow_table(all_results, min(20, len(all_results)))
        else:
            print("\nAucun résultat trouvé pour tous les flux analysés.")
    
    except ImportError:
        print("❌ Erreur: Module pandas non disponible.")
        print("   Installez-le avec: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse du fichier Excel: {e}")
        import traceback
        print(traceback.format_exc())

def export_excel_results(results, base_filename):
    """
    Exporte les résultats d'analyse Excel dans des fichiers au format CSV et JSON.
    Ajoute également une feuille avec les détails des règles identifiées.
    
    Args:
        results (list): Liste des résultats d'analyse
        base_filename (str): Nom de base pour les fichiers d'export
    """
    output_dir = get_output_dir()
    
    # Exporter au format JSON
    json_filename = f"{base_filename}.json"
    json_path = get_file_path(json_filename, 'output')
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Résultats exportés au format JSON: {json_path}")
    except Exception as e:
        print(f"❌ Erreur lors de l'export JSON: {e}")
    
    # Exporter au format CSV
    csv_filename = f"{base_filename}.csv"
    csv_path = get_file_path(csv_filename, 'output')
    
    try:
        # Créer un DataFrame pandas avec les champs principaux
        rows = []
        for result in results:
            # Extraire les données source et destination
            src = result.get('src', {})
            dst = result.get('dst', {})
            service = result.get('service', {})
            excel_metadata = result.get('excel_metadata', {})
            
            # Extraire les informations de règles si disponibles
            rules = result.get('rules', {})
            rule_hrefs = []
            rule_names = []
            
            # Gérer les deux formats de rules
            if isinstance(rules, dict) and 'sec_policy' in rules:
                # Format ancien (avant update_rules)
                sec_policy = rules.get('sec_policy', {})
                if sec_policy:
                    rule_href = sec_policy.get('href')
                    rule_name = sec_policy.get('name')
                    if rule_href:
                        rule_hrefs.append(rule_href)
                    if rule_name:
                        rule_names.append(rule_name)
            elif isinstance(rules, list) and len(rules) > 0:
                # Format nouveau (après update_rules) - peut contenir plusieurs règles
                for rule in rules:
                    rule_href = rule.get('href')
                    if rule_href:
                        rule_hrefs.append(rule_href)
                        # Extraire le nom de la règle à partir de l'URL si non fourni
                        rule_name = rule.get('name', rule_href.split('/')[-1] if rule_href else None)
                        if rule_name:
                            rule_names.append(rule_name)
            
            # Créer une ligne pour le CSV
            row = {
                # Métadonnées du fichier Excel
                'excel_row': excel_metadata.get('excel_row', ''),
                'excel_source': excel_metadata.get('source_ip', ''),
                'excel_dest': excel_metadata.get('dest_ip', ''),
                'excel_proto': excel_metadata.get('protocol', ''),
                'excel_port': excel_metadata.get('port', ''),
                
                # Données du résultat de l'API
                'src_ip': src.get('ip', ''),
                'dst_ip': dst.get('ip', ''),
                'service_name': service.get('name', ''),
                'service_port': service.get('port', ''),
                'service_proto': service.get('proto', ''),
                'policy_decision': result.get('policy_decision', ''),
                'flow_direction': result.get('flow_direction', ''),
                'num_connections': result.get('num_connections', ''),
                'rule_href': '; '.join(rule_hrefs) if rule_hrefs else '',
                'rule_name': '; '.join(rule_names) if rule_names else ''
            }
            rows.append(row)
        
        # Créer le DataFrame et l'exporter en CSV
        df = pd.DataFrame(rows)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"✅ Résultats exportés au format CSV: {csv_path}")
        
        # ---- NOUVELLE PARTIE : EXPORT EXCEL AVEC FEUILLE DE RÈGLES ----
        # Créer une version Excel avec une deuxième feuille pour les règles
        excel_filename = f"{base_filename}.xlsx"
        excel_path = get_file_path(excel_filename, 'output')
        
        # Exporter d'abord le DataFrame principal
        df.to_excel(excel_path, sheet_name='Flux', index=False)
        
        # Initialiser l'analyseur de trafic pour accéder à l'API et à la base de données
        analyzer = initialize_analyzer()
        if analyzer:
            # Extraire tous les hrefs uniques des règles
            rule_hrefs = []
            for result in results:
                # Extraire les hrefs de règles
                rules = result.get('rules', {})
                
                if isinstance(rules, dict) and 'sec_policy' in rules:
                    sec_policy = rules.get('sec_policy', {})
                    if sec_policy and 'href' in sec_policy:
                        rule_hrefs.append(sec_policy['href'])
                elif isinstance(rules, list):
                    for rule in rules:
                        if isinstance(rule, dict) and 'href' in rule:
                            rule_hrefs.append(rule['href'])
                            
                # Vérifier aussi dans rule_href direct
                if result.get('rule_href'):
                    hrefs = result['rule_href'].split('; ')
                    rule_hrefs.extend([href for href in hrefs if href])
            
            # Supprimer les doublons
            unique_rule_hrefs = list(set(rule_hrefs))
            print(f"\nIdentification de {len(unique_rule_hrefs)} règles uniques...")
            
            if unique_rule_hrefs:
                # Récupérer les détails des règles
                rules = []
                
                for href in unique_rule_hrefs:
                    # Vérifier d'abord dans la base de données
                    if hasattr(analyzer.db, 'get_rule_by_href'):
                        rule = analyzer.db.get_rule_by_href(href)
                        if rule:
                            rules.append(rule)
                        else:
                            # Essayer avec l'API
                            try:
                                api_rule = analyzer.api.get_rule_by_href(href)
                                if api_rule:
                                    rules.append(api_rule)
                            except Exception as e:
                                print(f"Erreur lors de la récupération de la règle {href}: {e}")
                                # Ajouter un placeholder pour cette règle
                                rules.append({
                                    'href': href,
                                    'rule_id': href.split('/')[-1],
                                    'description': 'Règle non disponible'
                                })
                
                # Préparer les données pour le DataFrame des règles
                rule_rows = []
                for rule in rules:
                    # Extraire les données brutes ou utiliser directement le dictionnaire
                    raw_data = rule.get('raw_data', rule)
                    
                    # Créer une ligne pour chaque règle
                    rule_row = {
                        'rule_id': raw_data.get('href', '').split('/')[-1] if raw_data.get('href') else None,
                        'description': raw_data.get('description', ''),
                        'enabled': 'Oui' if raw_data.get('enabled') else 'Non',
                        'href': raw_data.get('href', '')
                    }
                    
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
                    
                    rule_row['providers'] = '; '.join(provider_descriptions)
                    
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
                    
                    rule_row['consumers'] = '; '.join(consumer_descriptions)
                    
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
                    
                    rule_row['services'] = '; '.join(service_descriptions)
                    
                    # Ajouter cette règle aux données
                    rule_rows.append(rule_row)
                
                # Créer un DataFrame pour les règles
                rules_df = pd.DataFrame(rule_rows)
                
                # Ajouter le DataFrame des règles comme une nouvelle feuille dans le fichier Excel
                with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a') as writer:
                    rules_df.to_excel(writer, sheet_name='Règles', index=False)
                
                print(f"✅ {len(rule_rows)} règles exportées dans la feuille 'Règles' du fichier {excel_path}")
            else:
                print("Aucune règle identifiée, pas de feuille 'Règles' ajoutée.")
        else:
            print("Impossible d'initialiser l'analyseur de trafic pour récupérer les règles.")
        
        print(f"✅ Résultats exportés au format Excel: {excel_path}")
        
    except ImportError:
        print("❌ Erreur: Modules pandas ou openpyxl non disponibles.")
        print("   Installez-les avec: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erreur lors de l'export des données: {e}")
        import traceback
        traceback.print_exc()