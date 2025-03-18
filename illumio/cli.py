#!/usr/bin/env python3
import sys
import os
import time
from illumio import IllumioAPI, ConfigurationError
from illumio.database import IllumioDatabase
from sync_data import sync_all_data
from traffic_analysis import analyze_traffic

def clear_screen():
    """Nettoie l'écran pour une meilleure lisibilité."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Affiche l'en-tête de l'application."""
    clear_screen()
    print("=" * 60)
    print("               ILLUMIO AUTOMATION TOOL               ")
    print("=" * 60)
    print()

def print_menu(options):
    """Affiche un menu avec des options numérotées."""
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    print("\n0. Quitter")
    print("-" * 60)

def get_user_choice(max_option):
    """Récupère le choix de l'utilisateur avec validation."""
    while True:
        try:
            choice = int(input("\nVotre choix: "))
            if 0 <= choice <= max_option:
                return choice
            print(f"Veuillez entrer un nombre entre 0 et {max_option}.")
        except ValueError:
            print("Veuillez entrer un nombre valide.")

def test_connection():
    """Teste la connexion à l'API Illumio et affiche le résultat."""
    print("\nTest de connexion à l'API Illumio...")
    try:
        api = IllumioAPI()
        success, message = api.test_connection()
        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ {message}")
            return False
    except ConfigurationError as e:
        print(f"❌ Erreur de configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def initialize_database():
    """Initialise la base de données si elle n'existe pas."""
    try:
        db = IllumioDatabase()
        db.init_db()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        return False

def sync_database_menu():
    """Menu pour la synchronisation de la base de données."""
    print_header()
    print("SYNCHRONISATION DE LA BASE DE DONNÉES\n")
    
    if not test_connection():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    if not initialize_database():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    print("\nOptions de synchronisation:")
    options = [
        "Synchroniser tous les éléments",
        "Synchroniser uniquement les workloads",
        "Synchroniser uniquement les labels",
        "Synchroniser uniquement les listes d'IPs",
        "Synchroniser uniquement les services",
        "Synchroniser uniquement les label groups"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    start_time = time.time()
    
    if choice == 1:
        print("\nSynchronisation complète en cours...")
        success = sync_all_data()
    else:
        print("\nFonctionnalité non implémentée pour le moment.")
        # TODO: Implémenter les synchronisations partielles
        success = False
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        print(f"\n✅ Synchronisation terminée en {duration:.2f} secondes.")
    else:
        print(f"\n❌ Échec de la synchronisation après {duration:.2f} secondes.")
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

def traffic_analysis_menu():
    """Menu pour l'analyse de trafic."""
    print_header()
    print("ANALYSE DE TRAFIC\n")
    
    if not test_connection():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    if not initialize_database():
        input("\nAppuyez sur Entrée pour revenir au menu principal...")
        return
    
    print("\nOptions d'analyse de trafic:")
    options = [
        "Créer une nouvelle analyse de trafic",
        "Voir les analyses précédentes",
        "Exporter les résultats d'une analyse"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    if choice == 1:
        # Demander les paramètres de l'analyse
        print("\nCréation d'une nouvelle analyse de trafic:")
        query_name = input("Nom de la requête (laisser vide pour un nom automatique): ")
        days = input("Nombre de jours à analyser (défaut: 7): ")
        max_results = input("Nombre maximum de résultats (défaut: 1000): ")
        
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
            max_results = 1000
        else:
            try:
                max_results = int(max_results)
            except ValueError:
                print("Valeur invalide, utilisation de la valeur par défaut (1000).")
                max_results = 1000
        
        print("\nDémarrage de l'analyse de trafic...")
        start_time = time.time()
        
        # Créer une requête par défaut avec les paramètres spécifiés
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        from illumio import TrafficAnalysisOperation
        api = IllumioAPI()
        traffic_op = TrafficAnalysisOperation(api=api)
        query_data = traffic_op.create_default_query(
            query_name=query_name or f"Traffic_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            start_date=start_date,
            end_date=end_date,
            max_results=max_results
        )
        
        # Exécuter l'analyse
        results = analyze_traffic(query_data=query_data)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if results:
            print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
            print(f"   {len(results)} flux de trafic récupérés.")
        else:
            print(f"\n❌ Échec de l'analyse après {duration:.2f} secondes.")
    
    elif choice == 2 or choice == 3:
        print("\nFonctionnalité non implémentée pour le moment.")
        # TODO: Implémenter la visualisation et l'export des analyses
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

def main():
    """Fonction principale du CLI interactif."""
    # Vérifier si la base de données existe déjà
    db_file = 'data/illumio.db'
    db_exists = os.path.exists(db_file)
    
    # Afficher un message d'accueil
    print_header()
    print("Bienvenue dans l'outil d'automatisation Illumio!")
    print("\nCet outil vous permet de gérer et d'analyser votre environnement Illumio.")
    
    # Proposer de synchroniser la base de données au démarrage si elle n'existe pas
    if not db_exists:
        print("\nLa base de données locale n'a pas été détectée.")
        choice = input("Voulez-vous la synchroniser maintenant? (o/n): ").lower()
        if choice in ('o', 'oui', 'y', 'yes'):
            sync_database_menu()
    
    # Boucle principale du menu
    while True:
        print_header()
        print("MENU PRINCIPAL\n")
        
        main_options = [
            "Synchroniser la base de données",
            "Analyse de trafic",
            # Ajoutez ici d'autres options de menu au fur et à mesure
        ]
        
        print_menu(main_options)
        choice = get_user_choice(len(main_options))
        
        if choice == 0:
            print("\nMerci d'avoir utilisé l'outil d'automatisation Illumio. Au revoir!")
            return 0
        
        # Rediriger vers le sous-menu approprié
        if choice == 1:
            sync_database_menu()
        elif choice == 2:
            traffic_analysis_menu()
        # Ajoutez d'autres options ici au fur et à mesure

if __name__ == "__main__":
    sys.exit(main())