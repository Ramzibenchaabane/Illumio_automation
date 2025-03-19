# cli_modules/traffic_menu/analysis_viewer.py
#!/usr/bin/env python3
"""
Module pour visualiser les analyses de trafic existantes.
"""
from .common import (
    initialize_analyzer, 
    print_analysis_header, 
    get_query_choice,
    FlowDisplayFormatter
)

def view_traffic_analyses():
    """Affiche la liste des analyses de trafic existantes."""
    print_analysis_header("ANALYSES DE TRAFIC EXISTANTES")
    
    try:
        # Initialiser l'analyseur de trafic
        analyzer = initialize_analyzer()
        if not analyzer:
            return
        
        # Récupérer les requêtes
        queries = analyzer.get_queries()
        
        if not queries:
            print("Aucune analyse de trafic trouvée.")
            return
        
        print(f"\n{len(queries)} analyses trouvées.\n")
        
        # Demander si l'utilisateur veut voir les détails d'une analyse
        query_id = get_query_choice(
            queries,
            "\nEntrez l'ID d'une analyse pour voir ses détails (ou appuyez sur Entrée pour revenir): "
        )
        
        if query_id:
            view_traffic_analysis_details(query_id)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des analyses: {e}")

def view_traffic_analysis_details(query_id):
    """
    Affiche les détails d'une analyse de trafic spécifique.
    
    Args:
        query_id (str): Identifiant de la requête d'analyse
    """
    try:
        # Initialiser l'analyseur de trafic
        analyzer = initialize_analyzer()
        if not analyzer:
            return
        
        # Récupérer les flux
        flows = analyzer.get_flows(query_id)
        
        if not flows:
            print(f"Aucun flux trouvé pour l'analyse {query_id}.")
            return
        
        print(f"\nDétails de l'analyse {query_id}:")
        print(f"{len(flows)} flux de trafic trouvés.")
        
        # Afficher un résumé des flux par décision de politique
        decisions = {}
        for flow in flows:
            decision = flow.get('policy_decision')
            if decision in decisions:
                decisions[decision] += 1
            else:
                decisions[decision] = 1
        
        print("\nRépartition par décision de politique:")
        for decision, count in decisions.items():
            if decision:  # Éviter les clés None
                print(f"  - {decision}: {count} flux")
        
        # Compter les flux avec une règle identifiée
        flows_with_rules = sum(1 for flow in flows if flow.get('rule_href'))
        if flows_with_rules > 0:
            print(f"\nFlux avec règles identifiées: {flows_with_rules} ({(flows_with_rules / len(flows)) * 100:.1f}%)")
        
        # Demander si l'utilisateur veut voir plus de détails
        show_details = input("\nAfficher les détails des flux? (o/n): ").lower()
        
        if show_details in ('o', 'oui', 'y', 'yes'):
            display_traffic_flows(flows)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des détails: {e}")

def display_traffic_flows(flows, limit=20):
    """
    Affiche les détails des flux de trafic.
    
    Args:
        flows (list): Liste des flux de trafic
        limit (int): Nombre maximum de flux à afficher
    """
    # Utiliser le formatteur de la classe utilitaire
    FlowDisplayFormatter.format_flow_table(flows, limit)