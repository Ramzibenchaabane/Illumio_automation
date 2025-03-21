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
        
        # ---- CRÉATION DU FICHIER EXCEL AVEC FEUILLE DE RÈGLES ----
        # Créer une version Excel avec une deuxième feuille pour les règles
        excel_filename = f"{base_filename}.xlsx"
        excel_path = get_file_path(excel_filename, 'output')
        
        # Exporter d'abord le DataFrame principal
        df.to_excel(excel_path, sheet_name='Flux', index=False)
        
        # Initialiser l'analyseur de trafic pour accéder à la base de données
        analyzer = initialize_analyzer()
        if not analyzer:
            print("Impossible d'initialiser l'analyseur de trafic pour récupérer les règles.")
            return
        
        # Extraire tous les hrefs uniques des règles
        print("\nRecherche des règles dans les résultats...")
        rule_hrefs = set()
        
        # Déboguer l'extraction des règles
        for i, result in enumerate(results):
            try:
                # Vérifier dans les champs directs
                if 'rule_href' in result and result['rule_href']:
                    hrefs = str(result['rule_href']).split('; ')
                    for href in hrefs:
                        if href and href != 'N/A':
                            rule_hrefs.add(href)
                            print(f"  Règle trouvée dans rule_href: {href}")
                
                # Vérifier dans l'objet rules
                if 'rules' in result:
                    rules = result['rules']
                    # Format 1: dictionnaire avec sec_policy
                    if isinstance(rules, dict) and 'sec_policy' in rules:
                        sec_policy = rules['sec_policy']
                        if isinstance(sec_policy, dict) and 'href' in sec_policy:
                            rule_hrefs.add(sec_policy['href'])
                            print(f"  Règle trouvée dans rules.sec_policy: {sec_policy['href']}")
                    # Format 2: liste de règles
                    elif isinstance(rules, list):
                        for rule in rules:
                            if isinstance(rule, dict) and 'href' in rule:
                                rule_hrefs.add(rule['href'])
                                print(f"  Règle trouvée dans rules[]: {rule['href']}")
                
                # Vérifier dans raw_data si c'est une chaîne JSON
                if 'raw_data' in result and isinstance(result['raw_data'], str):
                    try:
                        raw_data = json.loads(result['raw_data'])
                        if isinstance(raw_data, dict) and 'rules' in raw_data:
                            rules = raw_data['rules']
                            if isinstance(rules, dict) and 'sec_policy' in rules:
                                sec_policy = rules['sec_policy']
                                if isinstance(sec_policy, dict) and 'href' in sec_policy:
                                    rule_hrefs.add(sec_policy['href'])
                                    print(f"  Règle trouvée dans raw_data.rules.sec_policy: {sec_policy['href']}")
                            elif isinstance(rules, list):
                                for rule in rules:
                                    if isinstance(rule, dict) and 'href' in rule:
                                        rule_hrefs.add(rule['href'])
                                        print(f"  Règle trouvée dans raw_data.rules[]: {rule['href']}")
                    except json.JSONDecodeError:
                        pass  # Ignorer les erreurs de parsing JSON
            except Exception as e:
                print(f"Erreur lors de l'extraction des règles pour le résultat {i}: {e}")
        
        # Convertir en liste et filtrer les valeurs vides ou invalides
        unique_rule_hrefs = [href for href in rule_hrefs if href and href != 'N/A']
        print(f"\n{len(unique_rule_hrefs)} règles uniques identifiées.")
        
        if not unique_rule_hrefs:
            print("Aucune règle identifiée, pas de feuille 'Règles' ajoutée.")
            return
        
        # Récupérer les détails des règles depuis la base de données uniquement
        rules = []
        for href in unique_rule_hrefs:
            # Extraire l'ID de la règle à partir de l'URL
            try:
                rule_id = href.split('/')[-1]
                print(f"Recherche de la règle {rule_id} dans la base de données...")
                
                # Utiliser directement la méthode get_rule_by_href
                if hasattr(analyzer.db, 'get_rule_by_href'):
                    rule = analyzer.db.get_rule_by_href(href)
                    if rule:
                        print(f"  Règle {rule_id} trouvée dans la base de données")
                        rules.append(rule)
                    else:
                        print(f"  Règle {rule_id} non trouvée dans la base de données")
                        # Ajouter un placeholder pour cette règle
                        rules.append({
                            'raw_data': {'href': href, 'id': rule_id},
                            'rule_id': rule_id,
                            'description': f'Règle {rule_id} non disponible dans la base de données'
                        })
            except Exception as e:
                print(f"Erreur lors de la recherche de la règle {href}: {e}")
        
        if not rules:
            print("Aucune règle récupérée, pas de feuille 'Règles' ajoutée.")
            return
        
        # Préparer les données pour le DataFrame des règles
        print(f"\nPréparation des données pour {len(rules)} règles...")
        rule_rows = []
        for i, rule in enumerate(rules):
            try:
                # Extraire les données brutes
                raw_data = rule.get('raw_data', {})
                if not isinstance(raw_data, dict):
                    if hasattr(raw_data, '__dict__'):
                        raw_data = raw_data.__dict__
                    else:
                        print(f"  Règle {i}: raw_data n'est pas un dictionnaire, conversion impossible.")
                        raw_data = {'description': 'Format de données invalide'}
                
                # Créer une ligne pour chaque règle
                rule_row = {
                    'rule_id': rule.get('rule_id') or raw_data.get('id') or raw_data.get('href', '').split('/')[-1] if raw_data.get('href') else f'rule_{i}',
                    'description': rule.get('description') or raw_data.get('description', 'Pas de description'),
                    'enabled': 'Oui' if raw_data.get('enabled') else 'Non',
                    'href': rule.get('href') or raw_data.get('href', 'N/A')
                }
                
                # Extraire les providers (fournisseurs)
                providers = []
                try:
                    if 'providers' in raw_data and isinstance(raw_data['providers'], (list, str)):
                        # Si c'est une chaîne JSON, la convertir
                        if isinstance(raw_data['providers'], str):
                            try:
                                providers_data = json.loads(raw_data['providers'])
                                if isinstance(providers_data, list):
                                    providers = providers_data
                            except json.JSONDecodeError:
                                print(f"  Règle {i}: Impossible de parser les providers.")
                        else:
                            providers = raw_data['providers']
                    
                    provider_descriptions = []
                    for provider in providers:
                        if not isinstance(provider, dict):
                            continue
                            
                        if 'actors' in provider and provider['actors'] == 'ams':
                            provider_descriptions.append('Tous les systèmes gérés')
                        elif 'label' in provider and isinstance(provider['label'], dict):
                            label = provider['label']
                            provider_descriptions.append(f"Label: {label.get('key')}:{label.get('value')}")
                        elif 'label_group' in provider and isinstance(provider['label_group'], dict):
                            lg = provider['label_group']
                            provider_descriptions.append(f"Groupe de labels: {lg.get('href', '').split('/')[-1]}")
                        elif 'workload' in provider and isinstance(provider['workload'], dict):
                            wl = provider['workload']
                            provider_descriptions.append(f"Workload: {wl.get('href', '').split('/')[-1]}")
                        elif 'ip_list' in provider and isinstance(provider['ip_list'], dict):
                            ip = provider['ip_list']
                            provider_descriptions.append(f"Liste IP: {ip.get('name') or ip.get('href', '').split('/')[-1]}")
                    
                    rule_row['providers'] = '; '.join(provider_descriptions) if provider_descriptions else 'N/A'
                except Exception as e:
                    print(f"  Règle {i}: Erreur lors de l'extraction des providers: {e}")
                    rule_row['providers'] = 'Erreur'
                
                # Extraire les consumers (consommateurs)
                consumers = []
                try:
                    if 'consumers' in raw_data and isinstance(raw_data['consumers'], (list, str)):
                        # Si c'est une chaîne JSON, la convertir
                        if isinstance(raw_data['consumers'], str):
                            try:
                                consumers_data = json.loads(raw_data['consumers'])
                                if isinstance(consumers_data, list):
                                    consumers = consumers_data
                            except json.JSONDecodeError:
                                print(f"  Règle {i}: Impossible de parser les consumers.")
                        else:
                            consumers = raw_data['consumers']
                    
                    consumer_descriptions = []
                    for consumer in consumers:
                        if not isinstance(consumer, dict):
                            continue
                            
                        if 'actors' in consumer and consumer['actors'] == 'ams':
                            consumer_descriptions.append('Tous les systèmes gérés')
                        elif 'label' in consumer and isinstance(consumer['label'], dict):
                            label = consumer['label']
                            consumer_descriptions.append(f"Label: {label.get('key')}:{label.get('value')}")
                        elif 'label_group' in consumer and isinstance(consumer['label_group'], dict):
                            lg = consumer['label_group']
                            consumer_descriptions.append(f"Groupe de labels: {lg.get('href', '').split('/')[-1]}")
                        elif 'workload' in consumer and isinstance(consumer['workload'], dict):
                            wl = consumer['workload']
                            consumer_descriptions.append(f"Workload: {wl.get('href', '').split('/')[-1]}")
                        elif 'ip_list' in consumer and isinstance(consumer['ip_list'], dict):
                            ip = consumer['ip_list']
                            consumer_descriptions.append(f"Liste IP: {ip.get('name') or ip.get('href', '').split('/')[-1]}")
                    
                    rule_row['consumers'] = '; '.join(consumer_descriptions) if consumer_descriptions else 'N/A'
                except Exception as e:
                    print(f"  Règle {i}: Erreur lors de l'extraction des consumers: {e}")
                    rule_row['consumers'] = 'Erreur'
                
                # Extraire les services
                services = []
                try:
                    if 'ingress_services' in raw_data and isinstance(raw_data['ingress_services'], (list, str)):
                        # Si c'est une chaîne JSON, la convertir
                        if isinstance(raw_data['ingress_services'], str):
                            try:
                                services_data = json.loads(raw_data['ingress_services'])
                                if isinstance(services_data, list):
                                    services = services_data
                            except json.JSONDecodeError:
                                print(f"  Règle {i}: Impossible de parser les services.")
                        else:
                            services = raw_data['ingress_services']
                    
                    service_descriptions = []
                    for service in services:
                        if not isinstance(service, dict):
                            continue
                            
                        if 'href' in service:
                            service_id = service['href'].split('/')[-1] if service['href'] else None
                            service_descriptions.append(f"Service: {service.get('name', service_id)}")
                        elif 'proto' in service:
                            proto = service['proto']
                            port = service.get('port', '')
                            port_text = f":{port}" if port else ""
                            service_descriptions.append(f"Proto {proto}{port_text}")
                    
                    rule_row['services'] = '; '.join(service_descriptions) if service_descriptions else 'N/A'
                except Exception as e:
                    print(f"  Règle {i}: Erreur lors de l'extraction des services: {e}")
                    rule_row['services'] = 'Erreur'
                
                # Ajouter cette règle aux données
                rule_rows.append(rule_row)
                print(f"  Règle {i}: Ajoutée avec succès.")
            except Exception as e:
                print(f"  Règle {i}: Erreur générale lors du traitement: {e}")
                # Ignorer cette règle et continuer
        
        # Vérifier qu'il reste des règles à exporter
        if not rule_rows:
            print("Aucune règle n'a pu être traitée, pas de feuille 'Règles' ajoutée.")
            return
        
        # Créer un DataFrame pour les règles
        try:
            print(f"Création du DataFrame des règles avec {len(rule_rows)} lignes...")
            rules_df = pd.DataFrame(rule_rows)
            
            print("Ajout de la feuille 'Règles' dans le fichier Excel...")
            # Ajouter le DataFrame des règles comme une nouvelle feuille dans le fichier Excel
            with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a') as writer:
                rules_df.to_excel(writer, sheet_name='Règles', index=False)
            
            print(f"✅ {len(rule_rows)} règles exportées dans la feuille 'Règles' du fichier {excel_path}")
        except Exception as e:
            print(f"❌ Erreur lors de la création de la feuille 'Règles': {e}")
            import traceback
            traceback.print_exc()
        
    except ImportError:
        print("❌ Erreur: Modules pandas ou openpyxl non disponibles.")
        print("   Installez-les avec: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erreur lors de l'export des données: {e}")
        import traceback
        traceback.print_exc()