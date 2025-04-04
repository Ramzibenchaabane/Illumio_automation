# cli_modules/clustering_menu.py
#!/usr/bin/env python3
"""
Module de menu pour l'analyse de clustering de serveurs.
"""
from cli_modules.menu_utils import print_header, print_menu, get_user_choice
from cli_modules.clustering_menu.cluster_analyzer import run_server_clustering_analysis
from cli_modules.clustering_menu.results_viewer import view_clustering_results

def server_clustering_menu():
    """Menu pour l'analyse de clustering de serveurs."""
    while True:
        print_header()
        print("ANALYSE DE CLUSTERING DE SERVEURS\n")
        
        print("Ce module utilise l'algorithme de Louvain pour regrouper les serveurs")
        print("en fonction des applications qu'ils ont en commun.\n")
        
        options = [
            "Lancer une analyse de clustering",
            "Visualiser les résultats d'une analyse précédente"
        ]
        
        print_menu(options)
        choice = get_user_choice(len(options))
        
        if choice == 0:
            return
        
        if choice == 1:
            run_server_clustering_analysis()
        elif choice == 2:
            view_clustering_results()
        
        input("\nAppuyez sur Entrée pour revenir au menu de clustering...")