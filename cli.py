#cli.py
#!/usr/bin/env python3
import sys
import os
from datetime import datetime
from illumio import IllumioAPI, ConfigurationError
from cli_modules.menu_utils import clear_screen, print_header, print_menu, get_user_choice
from cli_modules.sync_menu import sync_database_menu
from cli_modules.traffic_menu import traffic_analysis_menu

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