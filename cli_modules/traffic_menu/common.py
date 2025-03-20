# cli_modules/traffic_menu/common.py
#!/usr/bin/env python3
"""
Fonctions et classes utilitaires partagées pour le menu d'analyse de trafic.
"""
import json
import sys
from typing import Dict, List, Any, Optional, Tuple, Union

from cli_modules.menu_utils import print_header, test_connection, initialize_database
from illumio.traffic_analysis import IllumioTrafficAnalyzer

def validate_connection() -> bool:
    """
    Vérifie la connexion à l'API et l'initialisation de la base de données.
    
    Returns:
        bool: True si la connexion et la base de données sont prêtes, False sinon
    """
    if not test_connection():
        return False
    
    if not initialize_database():
        return False
    
    return True

def initialize_analyzer() -> Optional[IllumioTrafficAnalyzer]:
    """
    Initialise et retourne un analyseur de trafic.
    
    Returns:
        IllumioTrafficAnalyzer: Instance de l'analyseur, ou None en cas d'erreur
    """
    try:
        return IllumioTrafficAnalyzer()
    except Exception as e:
        print(f"Erreur lors de l'initialisation de l'analyseur: {e}")
        return None

def print_analysis_header(title: str) -> None:
    """
    Affiche un en-tête formaté pour les écrans d'analyse.
    
    Args:
        title (str): Titre de l'écran d'analyse
    """
    print_header()
    print(f"{title}\n")
    print("-" * 80)

def format_query_table(queries: List[Dict[str, Any]]) -> None:
    """
    Affiche un tableau formaté des requêtes d'analyse.
    
    Args:
        queries (list): Liste des requêtes d'analyse
    """
    print("-" * 90)
    print(f"{'ID':<8} {'NOM':<30} {'STATUT':<15} {'ANALYSE RÈGLES':<15} {'DATE':<20}")
    print("-" * 90)
    
    for query in queries:
        query_id = query.get('id')
        name = query.get('query_name')
        status = query.get('status')
        rules_status = query.get('rules_status', 'N/A')
        created_at = query.get('created_at')
        
        # Limiter la longueur du nom pour l'affichage
        if name and len(name) > 28:
            name = name[:25] + "..."
        
        print(f"{query_id:<8} {name:<30} {status:<15} {rules_status:<15} {created_at:<20}")
    
    print("-" * 90)

def format_numbered_query_table(queries: List[Dict[str, Any]]) -> None:
    """
    Affiche un tableau formaté et numéroté des requêtes d'analyse.
    
    Args:
        queries (list): Liste des requêtes d'analyse
    """
    print("-" * 90)
    print(f"{'#':<3} {'ID':<8} {'NOM':<30} {'STATUT':<15} {'ANALYSE RÈGLES':<15} {'DATE':<20}")
    print("-" * 90)
    
    for i, query in enumerate(queries, 1):
        query_id = query.get('id')
        name = query.get('query_name')
        status = query.get('status')
        rules_status = query.get('rules_status', 'N/A')
        created_at = query.get('created_at')
        
        # Limiter la longueur du nom pour l'affichage
        if name and len(name) > 28:
            name = name[:25] + "..."
        
        print(f"{i:<3} {query_id:<8} {name:<30} {status:<15} {rules_status:<15} {created_at:<20}")
    
    print("-" * 90)

def get_query_choice(queries: List[Dict[str, Any]], prompt: str = "\nEntrez l'ID d'une analyse (ou appuyez sur Entrée pour revenir): ") -> Optional[str]:
    """
    Demande à l'utilisateur de choisir une requête parmi une liste.
    
    Args:
        queries (list): Liste des requêtes d'analyse
        prompt (str): Message d'invite personnalisé
    
    Returns:
        str: ID de la requête choisie, ou None si annulé
    """
    if not queries:
        print("Aucune analyse trouvée.")
        return None
    
    # Afficher la liste des requêtes
    format_query_table(queries)
    
    # Demander le choix
    query_id = input(prompt)
    
    if not query_id:
        return None
    
    # Vérifier que la requête existe
    if not any(q.get('id') == query_id for q in queries):
        print(f"ID d'analyse invalide: {query_id}")
        return None
    
    return query_id

def get_numbered_query_choice(queries: List[Dict[str, Any]], prompt: str = "\nEntrez le numéro d'une analyse (ou appuyez sur Entrée pour revenir): ") -> Optional[Dict[str, Any]]:
    """
    Demande à l'utilisateur de choisir une requête par numéro.
    
    Args:
        queries (list): Liste des requêtes d'analyse
        prompt (str): Message d'invite personnalisé
    
    Returns:
        dict: Requête choisie, ou None si annulé
    """
    if not queries:
        print("Aucune analyse trouvée.")
        return None
    
    # Afficher la liste des requêtes numérotées
    format_numbered_query_table(queries)
    
    # Demander le choix
    choice = input(prompt)
    
    if not choice:
        return None
    
    try:
        index = int(choice) - 1
        if index < 0 or index >= len(queries):
            print("Numéro invalide.")
            return None
        
        return queries[index]
    except ValueError:
        print("Entrée invalide. Veuillez entrer un numéro.")
        return None

def debug_flow_structure(flow):
    """
    Fonction utilitaire pour déboguer la structure d'un flux de trafic.
    
    Args:
        flow: Objet flux de trafic à analyser
    """
    print("\n==== DÉBOGAGE STRUCTURE DE FLUX ====")
    print(f"Type d'objet: {type(flow)}")
    
    # Attributs et méthodes
    if hasattr(flow, '__dict__'):
        print(f"Attributs: {list(flow.__dict__.keys())}")
    
    # Si c'est un dictionnaire
    if isinstance(flow, dict):
        print(f"Clés: {list(flow.keys())}")
        
        # Examiner certaines clés importantes
        for key in ['src', 'dst', 'service', 'policy_decision', 'raw_data']:
            if key in flow:
                print(f"{key}: {type(flow[key])} - {flow[key]}")
        
        # Examiner raw_data si présent
        if 'raw_data' in flow:
            print("\n-- Analyse de raw_data --")
            if isinstance(flow['raw_data'], str):
                print("raw_data est une chaîne, tentative de parsing JSON...")
                try:
                    import json
                    raw_data = json.loads(flow['raw_data'])
                    print(f"Structure JSON: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Non dictionnaire'}")
                    
                    # Examiner certaines clés importantes dans raw_data
                    if isinstance(raw_data, dict):
                        for key in ['src', 'dst', 'service', 'policy_decision', 'rules']:
                            if key in raw_data:
                                value_type = type(raw_data[key])
                                value_preview = str(raw_data[key])[:100] + "..." if len(str(raw_data[key])) > 100 else str(raw_data[key])
                                print(f"raw_data[{key}]: {value_type} - {value_preview}")
                except Exception as e:
                    print(f"Erreur de parsing JSON: {e}")
            elif isinstance(flow['raw_data'], dict):
                print("raw_data est déjà un dictionnaire")
                raw_data = flow['raw_data']
                print(f"Clés raw_data: {list(raw_data.keys())}")
                
                # Examiner certaines clés importantes
                for key in ['src', 'dst', 'service', 'policy_decision', 'rules']:
                    if key in raw_data:
                        value_type = type(raw_data[key])
                        value_preview = str(raw_data[key])[:100] + "..." if len(str(raw_data[key])) > 100 else str(raw_data[key])
                        print(f"raw_data[{key}]: {value_type} - {value_preview}")
            else:
                print(f"raw_data est de type {type(flow['raw_data'])}")
    
    print("==== FIN DÉBOGAGE ====\n")

class FlowDisplayFormatter:
    """Classe utilitaire pour formater l'affichage des flux de trafic."""
    
    @staticmethod
    def format_flow_table(flows, limit=20):
        """
        Affiche un tableau formaté des flux de trafic, identique au format CSV exporté.
        
        Args:
            flows (list): Liste des flux de trafic
            limit (int): Limite du nombre de flux à afficher
        """
        if not flows:
            print("Aucun flux à afficher.")
            return
            
        # Vérifier le type de la liste flows
        if not isinstance(flows, list):
            print(f"Attention: 'flows' n'est pas une liste mais un {type(flows)}. Tentative de conversion...")
            try:
                if hasattr(flows, '__iter__'):
                    flows = list(flows)
                else:
                    flows = [flows]
            except Exception as e:
                print(f"Erreur de conversion: {e}")
                return
        
        # Définir l'en-tête du tableau
        print("\n" + "-" * 120)
        print(f"{'SOURCE':<16} {'DESTINATION':<16} {'SERVICE':<20} {'DÉCISION':<15} {'CONNEXIONS':<12} {'DIRECTION':<10} {'RÈGLE ID':<25} {'RÈGLE NOM':<20}")
        print("-" * 120)
        
        count = 0
        for flow in flows:
            if count >= limit:
                break
                
            try:
                # Données à extraire avec valeurs par défaut
                src_ip = "N/A"
                dst_ip = "N/A"
                service_name = "N/A"
                policy_decision = "N/A"
                num_connections = "N/A"
                flow_direction = "N/A"
                rule_href = "N/A"
                rule_name = "N/A"
                
                # Vérifier si flow est un objet dict ou un autre type
                if not isinstance(flow, dict):
                    if hasattr(flow, 'get') and callable(flow.get):
                        # C'est un objet qui supporte get() comme un dictionnaire
                        pass
                    elif hasattr(flow, '__dict__'):
                        # Convertir un objet en dictionnaire
                        flow = flow.__dict__
                    elif hasattr(flow, 'raw_data') and isinstance(flow.raw_data, str):
                        # Essayer de parser raw_data comme JSON
                        import json
                        try:
                            flow = json.loads(flow.raw_data)
                        except:
                            pass
                    else:
                        # Impossible de traiter ce type de flux
                        print(f"Impossible de traiter ce type de flux: {type(flow)}")
                        count += 1
                        continue
                
                # Extraction des données d'un flux à partir de différentes structures possibles
                
                # 1. Extraire l'IP source
                if 'src' in flow and isinstance(flow['src'], dict) and 'ip' in flow['src']:
                    src_ip = flow['src']['ip']
                elif 'src_ip' in flow:
                    src_ip = flow['src_ip']
                
                # 2. Extraire l'IP destination
                if 'dst' in flow and isinstance(flow['dst'], dict) and 'ip' in flow['dst']:
                    dst_ip = flow['dst']['ip']
                elif 'dst_ip' in flow:
                    dst_ip = flow['dst_ip']
                
                # 3. Extraire les informations de service
                if 'service' in flow:
                    if isinstance(flow['service'], dict):
                        service = flow['service']
                        port = service.get('port', '')
                        proto = service.get('proto', '')
                        
                        if 'name' in service and service['name']:
                            service_name = service['name']
                        elif port and proto:
                            service_name = f"{port}/{proto}"
                        elif port:
                            service_name = f"Port {port}"
                        elif proto:
                            service_name = f"Proto {proto}"
                    elif isinstance(flow['service'], str):
                        service_name = flow['service']
                elif 'service_name' in flow:
                    service_name = flow['service_name']
                
                # 4. Extraire la décision de politique
                policy_decision = flow.get('policy_decision', flow.get('draft_policy_decision', 'N/A'))
                
                # 5. Extraire le nombre de connexions
                num_connections = str(flow.get('num_connections', 'N/A'))
                
                # 6. Extraire la direction du flux
                flow_direction = flow.get('flow_direction', 'N/A')
                
                # 7. Extraire les informations de règle
                if 'rule_href' in flow:
                    # Format déjà extrait
                    rule_href = flow.get('rule_href', 'N/A')
                    rule_name = flow.get('rule_name', 'N/A')
                elif 'rules' in flow:
                    rules = flow['rules']
                    if isinstance(rules, list) and len(rules) > 0:
                        first_rule = rules[0]
                        if 'href' in first_rule:
                            rule_href = first_rule['href']
                            # Extraire l'ID de la règle à partir de l'URL
                            rule_name = first_rule.get('name', rule_href.split('/')[-1] if rule_href else 'N/A')
                    elif isinstance(rules, dict) and 'sec_policy' in rules:
                        sec_policy = rules['sec_policy']
                        if isinstance(sec_policy, dict):
                            rule_href = sec_policy.get('href', 'N/A')
                            rule_name = sec_policy.get('name', rule_href.split('/')[-1] if rule_href != 'N/A' else 'N/A')
                        elif isinstance(sec_policy, str):
                            rule_href = sec_policy
                            rule_name = sec_policy.split('/')[-1] if '/' in sec_policy else sec_policy
                
                # 8. Tentative supplémentaire avec raw_data si présent
                if 'raw_data' in flow and flow['raw_data']:
                    try:
                        import json
                        raw_data = None
                        
                        # Parse le JSON si c'est une chaîne
                        if isinstance(flow['raw_data'], str):
                            raw_data = json.loads(flow['raw_data'])
                        elif isinstance(flow['raw_data'], dict):
                            raw_data = flow['raw_data']
                            
                        if raw_data:
                            # Remplir les valeurs manquantes ou remplacer les valeurs N/A
                            if src_ip == "N/A" and 'src' in raw_data and isinstance(raw_data['src'], dict) and 'ip' in raw_data['src']:
                                src_ip = raw_data['src']['ip']
                            
                            if dst_ip == "N/A" and 'dst' in raw_data and isinstance(raw_data['dst'], dict) and 'ip' in raw_data['dst']:
                                dst_ip = raw_data['dst']['ip']
                            
                            if service_name == "N/A" and 'service' in raw_data and isinstance(raw_data['service'], dict):
                                service = raw_data['service']
                                port = service.get('port', '')
                                proto = service.get('proto', '')
                                
                                if 'name' in service and service['name']:
                                    service_name = service['name']
                                elif port and proto:
                                    service_name = f"{port}/{proto}"
                                elif port:
                                    service_name = f"Port {port}"
                                elif proto:
                                    service_name = f"Proto {proto}"
                            
                            if policy_decision == "N/A":
                                policy_decision = raw_data.get('policy_decision', raw_data.get('draft_policy_decision', 'N/A'))
                            
                            if num_connections == "N/A" and 'num_connections' in raw_data:
                                num_connections = str(raw_data['num_connections'])
                            
                            if flow_direction == "N/A" and 'flow_direction' in raw_data:
                                flow_direction = raw_data['flow_direction']
                            
                            if rule_href == "N/A" and rule_name == "N/A" and 'rules' in raw_data:
                                rules = raw_data['rules']
                                if isinstance(rules, list) and len(rules) > 0:
                                    first_rule = rules[0]
                                    if 'href' in first_rule:
                                        rule_href = first_rule['href']
                                        # Extraire l'ID de la règle à partir de l'URL
                                        rule_name = first_rule.get('name', rule_href.split('/')[-1] if rule_href else 'N/A')
                                elif isinstance(rules, dict) and 'sec_policy' in rules:
                                    sec_policy = rules['sec_policy']
                                    if isinstance(sec_policy, dict):
                                        rule_href = sec_policy.get('href', 'N/A')
                                        rule_name = sec_policy.get('name', rule_href.split('/')[-1] if rule_href != 'N/A' else 'N/A')
                    except Exception as e:
                        # Ignorer les erreurs de parsing de raw_data
                        pass
                
                # Formatage pour l'affichage avec gestion des valeurs None ou vides
                if src_ip in ("None", None, ""):
                    src_ip = "N/A"
                if dst_ip in ("None", None, ""):
                    dst_ip = "N/A"
                if service_name in ("None", None, ""):
                    service_name = "N/A"
                if policy_decision in ("None", None, ""):
                    policy_decision = "N/A"
                if num_connections in ("None", None, ""):
                    num_connections = "N/A"
                if flow_direction in ("None", None, ""):
                    flow_direction = "N/A"
                if rule_href in ("None", None, ""):
                    rule_href = "N/A"
                if rule_name in ("None", None, ""):
                    rule_name = "N/A"
                
                # Limiter la longueur des chaînes pour éviter les problèmes d'affichage
                src_ip = str(src_ip)[:16]
                dst_ip = str(dst_ip)[:16]
                service_name = str(service_name)[:20]
                policy_decision = str(policy_decision)[:15]
                num_connections = str(num_connections)[:12]
                flow_direction = str(flow_direction)[:10]
                
                # Si rule_href est trop long, le raccourcir
                if len(str(rule_href)) > 23:
                    rule_href = str(rule_href)[:20] + "..."
                else:
                    rule_href = str(rule_href)[:25]
                
                rule_name = str(rule_name)[:20]
                
                # Afficher la ligne
                print(f"{src_ip:<16} {dst_ip:<16} {service_name:<20} {policy_decision:<15} "
                      f"{num_connections:<12} {flow_direction:<10} {rule_href:<25} {rule_name:<20}")
                
                count += 1
            except Exception as e:
                print(f"Erreur de formatage pour un flux: {e}")
                # Ne pas afficher tout le flux si c'est un objet volumineux
                count += 1
        
        print("-" * 120)
        if count < len(flows):
            print(f"\n... et {len(flows) - count} autres flux.")