# cli_modules/traffic_menu/flow_analyzer.py
#!/usr/bin/env python3
"""
Module pour l'analyse de flux de trafic spécifiques.
"""
import time
from datetime import datetime, timedelta

from cli_modules.menu_utils import get_user_choice
from .common import (
    initialize_analyzer,
    print_analysis_header,
    FlowDisplayFormatter
)

def manual_entry_analysis():
    """Analyse de trafic par entrée manuelle de source, destination et service."""
    print_analysis_header("ANALYSE DE TRAFIC PAR ENTRÉE MANUELLE")
    
    # Obtenir les informations source, destination et service
    source_ip = input("Adresse IP source: ")
    dest_ip = input("Adresse IP destination: ")
    
    # Menu pour le protocole
    print("\nChoisissez le protocole:")
    protocols = [
        "TCP (6)",
        "UDP (17)",
        "ICMP (1)",
        "Autre (spécifier)"
    ]
    
    for i, proto in enumerate(protocols, 1):
        print(f"{i}. {proto}")
    
    proto_choice = get_user_choice(len(protocols))
    
    if proto_choice == 0:
        return
    
    # Convertir le choix en numéro de protocole
    if proto_choice == 1:
        protocol = 6  # TCP
    elif proto_choice == 2:
        protocol = 17  # UDP
    elif proto_choice == 3:
        protocol = 1  # ICMP
    else:
        try:
            protocol = int(input("Numéro de protocole: "))
        except ValueError:
            print("Numéro de protocole invalide, utilisation de TCP (6).")
            protocol = 6
    
    # Pour TCP/UDP, demander le port
    port = None
    if protocol in [6, 17]:
        try:
            port_input = input("Port (1-65535): ")
            if port_input:
                port = int(port_input)
                if port < 1 or port > 65535:
                    raise ValueError("Port hors limites")
        except ValueError:
            print("Port invalide, aucun port spécifié.")
            port = None
    
    # Demander si l'analyse de règles approfondie doit être effectuée
    deep_analysis = input("\nEffectuer une analyse de règles approfondie ? (o/N): ").lower()
    perform_deep_analysis = deep_analysis in ('o', 'oui', 'y', 'yes')
    
    # Créer une requête d'analyse avec ces paramètres
    analyze_specific_flow(source_ip, dest_ip, protocol, port, perform_deep_analysis)

def analyze_specific_flow(source_ip, dest_ip, protocol, port=None, perform_deep_analysis=False):
    """
    Analyse un flux spécifique entre source et destination.
    
    Args:
        source_ip (str): Adresse IP source
        dest_ip (str): Adresse IP destination
        protocol (int): Protocole IP
        port (int, optional): Port TCP/UDP
        perform_deep_analysis (bool): Si True, effectuer analyse de règles approfondie
    """
    # Initialiser l'analyseur de trafic
    analyzer = initialize_analyzer()
    if not analyzer:
        return
    
    # Afficher un résumé des paramètres d'analyse
    print("\nParamètres d'analyse:")
    print(f"  Source      : {source_ip}")
    print(f"  Destination : {dest_ip}")
    print(f"  Protocole   : {protocol}")
    if port:
        print(f"  Port        : {port}")
    print(f"  Analyse des règles: {'Oui' if perform_deep_analysis else 'Non'}")
    
    # Créer un nom de requête spécifique
    query_name = f"Flow_{source_ip}_to_{dest_ip}_{protocol}"
    if port:
        query_name += f"_port{port}"
    
    # Créer une requête d'analyse personnalisée
    query_data = {
        "query_name": query_name,
        "start_date": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d'),
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
    
    print("\nDémarrage de l'analyse de trafic spécifique...")
    
    # Préciser la période de recherche
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    print(f"Période d'analyse: {start_date} à {end_date} (7 derniers jours)")
    
    if perform_deep_analysis:
        print("L'analyse de règles approfondie sera effectuée après l'analyse de trafic.")
        
    start_time = time.time()
    
    # Exécuter l'analyse
    results = analyzer.analyze(query_data=query_data, perform_deep_analysis=perform_deep_analysis)
    
    end_time = time.time()
    duration = end_time - start_time
    
    if results:
        print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
        print(f"   {len(results)} flux de trafic correspondants trouvés.")
        
        # Vérifier s'il y a des résultats pour afficher
        if len(results) > 0:
            # Résumé des résultats
            policy_decisions = {}
            has_rules = 0
            
            for flow in results:
                # Compter les décisions de politique
                decision = flow.get('policy_decision', 'N/A')
                if decision in policy_decisions:
                    policy_decisions[decision] += 1
                else:
                    policy_decisions[decision] = 1
                
                # Vérifier si une règle est associée
                if 'rules' in flow and (
                    (isinstance(flow['rules'], dict) and 'sec_policy' in flow['rules']) or
                    (isinstance(flow['rules'], list) and len(flow['rules']) > 0)
                ):
                    has_rules += 1
            
            # Afficher le résumé
            print("\nRésumé des résultats:")
            for decision, count in policy_decisions.items():
                print(f"  - {decision}: {count} flux")
            
            if has_rules > 0:
                print(f"  - {has_rules} flux avec règles identifiées ({(has_rules/len(results))*100:.1f}%)")
            
            # Afficher les flux détaillés dans un format identique à l'export CSV
            limit = min(20, len(results))  # Limiter à 20 résultats par défaut
            print(f"\nDétail des {limit} premiers flux (format identique à l'export CSV):")
            FlowDisplayFormatter.format_flow_table(results, limit)
            
            # Proposer d'afficher plus de résultats si nécessaire
            if len(results) > limit:
                show_more = input(f"\nAfficher les {len(results) - limit} flux supplémentaires? (o/n): ").lower()
                if show_more in ('o', 'oui', 'y', 'yes'):
                    print(f"\nFlux supplémentaires ({limit+1} à {len(results)}):")
                    FlowDisplayFormatter.format_flow_table(results[limit:], len(results) - limit)
        else:
            print("Aucun flux correspondant trouvé dans la période spécifiée.")
    else:
        print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")
        print("Suggestions:")
        print("  - Vérifiez que les adresses IP sont correctes")
        print("  - Assurez-vous que la communication a eu lieu dans les 7 derniers jours")
        print("  - Vérifiez la connexion à Illumio PCE")