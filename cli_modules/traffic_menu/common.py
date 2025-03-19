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
        Affiche un tableau formaté des flux de trafic, identique au format CSV exporté.
        
        Args:
            flows (list): Liste des flux de trafic
            limit (int): Limite du nombre de flux à afficher
        """
        print("\n" + "-" * 120)
        print(f"{'SOURCE':<16} {'DESTINATION':<16} {'SERVICE':<20} {'DÉCISION':<15} {'CONNEXIONS':<12} {'DIRECTION':<10} {'RÈGLE ID':<25} {'RÈGLE NOM':<20}")
        print("-" * 120)
        
        for i, flow in enumerate(flows):
            if i >= limit:
                print(f"\n... et {len(flows) - limit} autres flux.")
                break
            
            try:
                # Extraire les données du flux selon le format CSV
                flow_data = FlowDisplayFormatter._extract_flow_data_csv_format(flow)
                
                # Formater et afficher la ligne
                print(f"{flow_data['src']:<16} {flow_data['dst']:<16} "
                      f"{flow_data['service']:<20} {flow_data['policy_decision']:<15} "
                      f"{flow_data['num_connections']:<12} {flow_data['flow_direction']:<10} "
                      f"{flow_data['rule_href']:<25} {flow_data['rule_name']:<20}")
                
            except Exception as e:
                print(f"Erreur de formatage pour le flux {i}: {e}")
    
    @staticmethod
    def _extract_flow_data_csv_format(flow):
        """
        Extrait les données d'un flux au format CSV.
        
        Args:
            flow (dict): Données du flux
        
        Returns:
            dict: Données formatées selon le format CSV
        """
        # Valeurs par défaut identiques au format CSV exporté
        flow_data = {
            'src': 'N/A',
            'dst': 'N/A',
            'service': 'N/A',
            'policy_decision': 'N/A',
            'num_connections': 'N/A',
            'flow_direction': 'N/A',
            'rule_href': 'N/A',
            'rule_name': 'N/A'
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
                    # Extraire selon le format exporté en CSV
                    src = raw_data.get('src', {})
                    dst = raw_data.get('dst', {})
                    service = raw_data.get('service', {})
                    
                    flow_data['src'] = src.get('ip', 'N/A')
                    flow_data['dst'] = dst.get('ip', 'N/A')
                    flow_data['service'] = service.get('name', 'N/A')
                    flow_data['policy_decision'] = raw_data.get('policy_decision', 'N/A')
                    flow_data['num_connections'] = str(raw_data.get('num_connections', 'N/A'))
                    flow_data['flow_direction'] = raw_data.get('flow_direction', 'N/A')
                    
                    # Extraire les informations de règles
                    rules = raw_data.get('rules')
                    if isinstance(rules, dict) and 'sec_policy' in rules:
                        # Ancien format (avant update_rules)
                        sec_policy = rules.get('sec_policy', {})
                        flow_data['rule_href'] = sec_policy.get('href', 'N/A')
                        flow_data['rule_name'] = sec_policy.get('name', 'N/A')
                    elif isinstance(rules, list) and len(rules) > 0:
                        # Nouveau format (après update_rules)
                        rule = rules[0]
                        flow_data['rule_href'] = rule.get('href', 'N/A')
                        # Le nom de la règle est souvent l'ID à la fin de l'URL
                        if flow_data['rule_href'] != 'N/A':
                            flow_data['rule_name'] = flow_data['rule_href'].split('/')[-1]
            
            except Exception as e:
                print(f"Erreur lors de l'extraction des données JSON: {e}")
        
        else:
            # Si pas de raw_data, utiliser directement les champs du flux
            # Ces champs correspondent au schéma de la base de données
            flow_data['src'] = flow.get('src_ip', 'N/A')
            flow_data['dst'] = flow.get('dst_ip', 'N/A')
            flow_data['service'] = flow.get('service', 'N/A')
            flow_data['policy_decision'] = flow.get('policy_decision', 'N/A')
            flow_data['num_connections'] = str(flow.get('num_connections', 'N/A'))
            flow_data['flow_direction'] = flow.get('flow_direction', 'N/A')
            flow_data['rule_href'] = flow.get('rule_href', 'N/A')
            flow_data['rule_name'] = flow.get('rule_name', 'N/A')
        
        # Traiter les cas où le service est manquant mais port/proto sont présents
        if flow_data['service'] == 'N/A':
            port = None
            proto = None
            
            # Chercher dans les données brutes
            if 'raw_data' in flow and flow['raw_data']:
                try:
                    if isinstance(flow.get('raw_data'), str):
                        raw_data = json.loads(flow.get('raw_data', '{}'))
                    elif isinstance(flow.get('raw_data'), dict):
                        raw_data = flow.get('raw_data')
                    
                    if raw_data and 'service' in raw_data:
                        service = raw_data.get('service', {})
                        port = service.get('port')
                        proto = service.get('proto')
                except:
                    pass
            # Ou chercher directement dans l'objet flow
            else:
                port = flow.get('port')
                proto = flow.get('protocol')
            
            # Construire un nom de service à partir du port et du protocole si disponibles
            if port and proto:
                flow_data['service'] = f"{port}/{proto}"
        
        # Raccourcir les valeurs trop longues pour l'affichage
        for key in ['rule_href', 'rule_name']:
            if flow_data[key] != 'N/A' and len(str(flow_data[key])) > 18:
                flow_data[key] = str(flow_data[key])[:15] + '...'
        
        # Assurer que toutes les valeurs sont des chaînes
        for key, value in flow_data.items():
            flow_data[key] = str(value)
        
        return flow_data