# cli_modules/clustering_menu/menu.py
#!/usr/bin/env python3
"""
Module principal du menu d'analyse de clustering de serveurs.
"""
from cli_modules.menu_utils import print_header, print_menu, get_user_choice
from .cluster_analyzer import run_server_clustering_analysis
from .results_viewer import view_clustering_results
from .algorithm_comparison import compare_clustering_algorithms

def server_clustering_menu():
    """Menu principal pour l'analyse de clustering de serveurs."""
    while True:
        print_header()
        print("ANALYSE DE CLUSTERING DE SERVEURS\n")
        
        print("Ce module permet de regrouper les serveurs en clusters en fonction des applications qu'ils ont en commun.")
        print("Plusieurs algorithmes de clustering sont disponibles, chacun avec des caractéristiques différentes.")
        print("L'objectif est de minimiser les connexions entre clusters tout en maximisant les connexions internes.\n")
        
        options = [
            "Lancer une analyse de clustering",
            "Visualiser les résultats d'une analyse précédente",
            "Comparer les algorithmes de clustering sur un jeu de données"
        ]
        
        print_menu(options)
        choice = get_user_choice(len(options))
        
        if choice == 0:
            return
        
        if choice == 1:
            run_server_clustering_analysis()
        elif choice == 2:
            view_clustering_results()
        elif choice == 3:
            compare_clustering_algorithms()