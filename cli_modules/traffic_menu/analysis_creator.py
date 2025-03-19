# cli_modules/traffic_menu/analysis_creator.py
#!/usr/bin/env python3
"""
Module pour la création et le lancement d'analyses de trafic.
"""
import time
from datetime import datetime, timedelta

from .common import (
    initialize_analyzer, 
    print_analysis_header,
    get_numbered_query_choice,
    FlowDisplayFormatter
)

def create_traffic_analysis():
    """Crée une nouvelle analyse de trafic."""
    # Initialiser l'analyseur de trafic
    analyzer = initialize_analyzer()
    if not analyzer:
        return
    
    # Afficher l'en-tête
    print_analysis_header("CRÉATION D'UNE NOUVELLE ANALYSE DE TRAFIC")
    
    # Demander les paramètres de l'analyse
    query_name = input("Nom de la requête (laisser vide pour un nom automatique): ")
    days = input("Nombre de jours à analyser (défaut: 7): ")
    max_results = input("Nombre maximum de résultats (défaut: 10000): ")
    
    # Demander si l'analyse de règles approfondie doit être effectuée
    deep_analysis = input("Effectuer une analyse de règles approfondie ? (o/N): ").lower()
    perform_deep_analysis = deep_analysis in ('o', 'oui', 'y', 'yes')
    
    # Utiliser les valeurs par défaut si non spécifiées
    if not query_name:
        query_name = None
    if not days:
        days = 7
    else:
        try:
            days = int(days)
        except ValueError:
            print("Valeur invalide, utilisation de la valeur par défaut (7).")
            days = 7
    
    if not max_results:
        max_results = 10000
    else:
        try:
            max_results = int(max_results)
        except ValueError:
            print("Valeur invalide, utilisation de la valeur par défaut (10000).")
            max_results = 10000
    
    print("\nDémarrage de l'analyse de trafic...")
    if perform_deep_analysis:
        print("L'analyse de règles approfondie sera effectuée après l'analyse de trafic.")
    
    start_time = time.time()
    
    # Créer les dates pour l'analyse
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    date_range = (start_date, end_date)
    
    # Exécuter l'analyse de trafic
    results = analyzer.analyze(
        query_name=query_name,
        date_range=date_range,
        max_results=max_results,
        perform_deep_analysis=perform_deep_analysis
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    if results:
        print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
        print(f"   {len(results)} flux de trafic récupérés.")
    else:
        print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")

def launch_deep_rule_analysis():
    """Lance une analyse de règles approfondie sur une requête de trafic existante."""
    print_analysis_header("ANALYSE DE RÈGLES APPROFONDIE")
    
    # Initialiser l'analyseur de trafic
    analyzer = initialize_analyzer()
    if not analyzer:
        return
    
    try:
        # Récupérer uniquement les requêtes complétées
        queries = analyzer.get_queries("completed")
        
        if not queries:
            print("Aucune analyse de trafic complétée trouvée.")
            return
        
        # Filtrer les requêtes qui n'ont pas encore d'analyse de règles complétée
        eligible_queries = [q for q in queries if q.get('rules_status') != 'completed']
        
        if not eligible_queries:
            print("Toutes les analyses de trafic complétées ont déjà une analyse de règles.")
            return
        
        # Faire sélectionner une requête par l'utilisateur
        selected_query = get_numbered_query_choice(
            eligible_queries,
            "\nEntrez le numéro de l'analyse à traiter (ou appuyez sur Entrée pour revenir): "
        )
        
        if not selected_query:
            return
        
        query_id = selected_query.get('id')
        
        print(f"\nLancement de l'analyse de règles approfondie pour la requête {query_id}...")
        
        # Exécuter directement l'analyse de règles approfondie
        start_time = time.time()
        results = analyzer._perform_deep_rule_analysis(query_id)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if results:
            print(f"\n✅ Analyse de règles approfondie terminée en {duration:.2f} secondes.")
            print(f"   {len(results)} flux de trafic avec analyse de règles récupérés.")
            
            # Demander si l'utilisateur veut voir les résultats
            show_results = input("\nAfficher les résultats? (o/n): ").lower()
            if show_results in ('o', 'oui', 'y', 'yes'):
                FlowDisplayFormatter.format_flow_table(results)
        else:
            print(f"\n❌ Échec de l'analyse de règles après {duration:.2f} secondes.")
    
    except Exception as e:
        print(f"Erreur lors de l'analyse de règles: {e}")