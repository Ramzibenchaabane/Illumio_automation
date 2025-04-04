#!/usr/bin/env python3
# illumio_toolbox.py
# Point d'entrée principal pour l'application d'automatisation Illumio.
"""
Point d'entrée principal pour l'application d'automatisation Illumio.
"""
import sys
import os
from cli_modules.menu_utils import print_header, print_menu, get_user_choice
from cli_modules.sync_menu import sync_database_menu
from cli_modules.traffic_menu import traffic_analysis_menu
from cli_modules.clustering_menu import server_clustering_menu
from illumio.utils.directory_manager import get_input_dir, get_output_dir

def check_dependencies():
    """Vérifie si les dépendances nécessaires sont installées."""
    missing_deps = []
    
    # Vérification des dépendances
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import configparser
    except ImportError:
        missing_deps.append("configparser")
    
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import openpyxl
    except ImportError:
        missing_deps.append("openpyxl")
    
    # Ajout de vérification pour les dépendances de clustering
    try:
        import networkx
    except ImportError:
        missing_deps.append("networkx")
    
    try:
        import community
    except ImportError:
        missing_deps.append("python-louvain")
    
    if missing_deps:
        print("Dépendances manquantes:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nVeuillez installer les dépendances manquantes avec:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True

def main_menu():
    """Affiche le menu principal de l'application."""
    while True:
        print_header()
        print("MENU PRINCIPAL\n")
        
        options = [
            "Synchroniser la base de données",
            "Analyse de trafic",
            "Analyse de clustering de serveurs",
            "Afficher les statistiques"
        ]
        
        print_menu(options)
        choice = get_user_choice(len(options))
        
        if choice == 0:
            print("\nAu revoir!")
            return 0
        
        if choice == 1:
            sync_database_menu()
        elif choice == 2:
            traffic_analysis_menu()
        elif choice == 3:
            server_clustering_menu()
        elif choice == 4:
            show_statistics()

def show_statistics():
    """Affiche les statistiques de la base de données."""
    print_header()
    print("STATISTIQUES DE LA BASE DE DONNÉES\n")
    
    try:
        from illumio import IllumioDatabase
        
        db = IllumioDatabase()
        conn, cursor = db.connect()
        
        # Récupérer les statistiques des différentes tables
        tables = {
            'workloads': 'Workloads',
            'labels': 'Labels',
            'ip_lists': 'Listes d\'IP',
            'services': 'Services',
            'label_groups': 'Groupes de labels',
            'traffic_queries': 'Requêtes de trafic',
            'traffic_flows': 'Flux de trafic'
        }
        
        print("Nombre d'entrées par table:\n")
        print("-" * 40)
        
        for table, display_name in tables.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{display_name}: {count}")
        
        print("-" * 40)
        
        # Statistiques supplémentaires
        cursor.execute("SELECT COUNT(DISTINCT query_id) FROM traffic_flows")
        queries_with_flows = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(num_connections) FROM traffic_flows")
        total_connections = cursor.fetchone()[0] or 0
        
        print(f"\nRequêtes avec des flux: {queries_with_flows}")
        print(f"Nombre total de connexions analysées: {total_connections}")
        
        db.close(conn)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des statistiques: {e}")
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

def show_version():
    """Affiche la version de l'application."""
    print("\nIllumio Automation Tool v1.3")
    print("© 2025 - Tous droits réservés")
    print("\nAméliorations:")
    print("- Analyse manuelle (source/destination/service)")
    print("- Import de fichiers Excel depuis le dossier 'input_files'")
    print("- Export des résultats dans le dossier 'outputs'")
    print("- Analyse de clustering de serveurs avec l'algorithme de Louvain")

def setup_directories():
    """Crée les répertoires nécessaires pour l'application."""
    # Crée les répertoires d'entrée et de sortie
    input_dir = get_input_dir()
    output_dir = get_output_dir()
    
    # Crée également le répertoire de données
    os.makedirs('data', exist_ok=True)
    
    print(f"Répertoires d'application initialisés:")
    print(f"- Entrée: {input_dir}")
    print(f"- Sortie: {output_dir}")
    print(f"- Données: {os.path.abspath('data')}")

def main():
    """Fonction principale."""
    try:
        # Vérifier les dépendances
        if not check_dependencies():
            return 1
        
        # Afficher la version
        show_version()
        
        # Initialiser les répertoires de l'application
        setup_directories()
        
        # Lancer le menu principal
        return main_menu()
    except KeyboardInterrupt:
        print("\n\nOpération interrompue. Au revoir!")
        return 1
    except Exception as e:
        print(f"\nErreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())