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

class FlowDisplayFormatter:
    """Classe utilitaire pour formater l'affichage des flux de trafic."""
    
    @staticmethod
    def format_flow_table(flows, limit=20):
        """
        Affiche un tableau formaté des flux de trafic.
        
        Args:
            flows (list): Liste des flux de trafic
            limit (int): Limite du nombre de flux à afficher
        """
        print("\n" + "-" * 115)
        print(f"{'SOURCE':<16} {'DESTINATION':<16} {'SERVICE':<20} {'PORT':<8} {'PROTO':<8} {'DÉCISION':<15} {'CONNEXIONS':<10} {'RÈGLE':<20}")
        print("-" * 115)
        
        for i, flow in enumerate(flows):
            if i >= limit:
                print(f"\n... et {len(flows) - limit} autres flux (utilisez --limit pour voir plus de résultats).")
                break
            
            try:
                # Extraire les données du flux
                flow_data = FlowDisplayFormatter._extract_flow_data(flow)
                
                # Formater et afficher la ligne
                print(f"{flow_data['src_ip']:<16} {flow_data['dst_ip']:<16} "
                      f"{flow_data['service_name']:<20} {flow_data['port']:<8} "
                      f"{flow_data['protocol']:<8} {flow_data['decision']:<15} "
                      f"{flow_data['connections']:<10} {flow_data['rule_name']:<20}")
                
            except Exception as e:
                print(f"Erreur de formatage pour le flux {i}: {e}")
    
    @staticmethod
    def _extract_flow_data(flow):
        """
        Extrait les données importantes d'un flux pour l'affichage.
        
        Args:
            flow (dict): Données du flux
        
        Returns:
            dict: Données formatées pour l'affichage
        """
        # Valeurs par défaut
        flow_data = {
            'src_ip': 'N/A',
            'dst_ip': 'N/A',
            'service_name': 'N/A',
            'port': 'N/A',
            'protocol': 'N/A',
            'decision': 'N/A',
            'rule_name': 'N/A',
            'connections': 'N/A'
        }
        
        # Si les données sont stockées dans raw_data (format JSON), les extraire
        if 'raw_data' in flow and flow['raw_data']:
            try:
                import json
                raw_data = None
                
                # Tenter de parser les données JSON
                if isinstance(flow.get('raw_data'), str):
                    raw_data = json.loads(flow.get('raw_data', '{}'))
                elif isinstance(flow.get('raw_data'), dict):
                    raw_data = flow.get('raw_data')
                
                if raw_data:
                    src = raw_data.get('src', {})
                    dst = raw_data.get('dst', {})
                    service = raw_data.get('service', {})
                    rules = raw_data.get('rules')
                    
                    # Extraire les données de base
                    flow_data['src_ip'] = src.get('ip') or 'N/A'
                    flow_data['dst_ip'] = dst.get('ip') or 'N/A'
                    flow_data['decision'] = raw_data.get('policy_decision') or 'N/A'
                    flow_data['connections'] = str(raw_data.get('num_connections', 'N/A'))
                    
                    # Extraire le service et le port
                    flow_data['service_name'] = service.get('name', 'N/A')
                    flow_data['port'] = str(service.get('port', 'N/A'))
                    flow_data['protocol'] = str(service.get('proto', 'N/A'))
                    
                    # Si aucun nom de service mais port/proto présents, les utiliser comme nom
                    if flow_data['service_name'] == 'N/A' and flow_data['port'] != 'N/A' and flow_data['protocol'] != 'N/A':
                        flow_data['service_name'] = f"{flow_data['port']}/{flow_data['protocol']}"
                    
                    # Extraire l'information de règle
                    if isinstance(rules, dict) and 'sec_policy' in rules:
                        # Ancien format (avant update_rules)
                        sec_policy = rules.get('sec_policy', {})
                        if sec_policy and 'name' in sec_policy:
                            flow_data['rule_name'] = sec_policy.get('name')
                        elif sec_policy and 'href' in sec_policy:
                            # Extraire l'ID de la règle depuis l'URL href
                            flow_data['rule_name'] = sec_policy.get('href').split('/')[-1]
                    elif isinstance(rules, list) and len(rules) > 0:
                        # Nouveau format (après update_rules)
                        rule = rules[0]
                        rule_href = rule.get('href', 'N/A')
                        # Utiliser l'ID de la règle depuis l'URL href
                        if rule_href != 'N/A':
                            flow_data['rule_name'] = rule_href.split('/')[-1]
            except Exception as e:
                print(f"Erreur lors de l'extraction des données JSON: {e}")
        else:
            # Si pas de raw_data, utiliser directement les champs de flow
            flow_data['src_ip'] = flow.get('src_ip') or 'N/A'
            flow_data['dst_ip'] = flow.get('dst_ip') or 'N/A'
            flow_data['service_name'] = flow.get('service') or 'N/A'
            flow_data['port'] = str(flow.get('port') or 'N/A')
            flow_data['protocol'] = str(flow.get('protocol') or 'N/A')
            flow_data['decision'] = flow.get('policy_decision') or 'N/A'
            flow_data['rule_name'] = flow.get('rule_name') or 'N/A'
            flow_data['connections'] = str(flow.get('num_connections') or 'N/A')
        
        # Limiter la longueur de rule_name pour l'affichage
        if flow_data['rule_name'] != 'N/A' and len(str(flow_data['rule_name'])) > 18:
            flow_data['rule_name'] = str(flow_data['rule_name'])[:15] + '...'
        
        # Assurer que toutes les valeurs sont des chaînes
        for key, value in flow_data.items():
            flow_data[key] = str(value)
        
        return flow_data