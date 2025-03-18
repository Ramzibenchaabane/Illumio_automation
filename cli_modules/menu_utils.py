#!/usr/bin/env python3
import os
from illumio import IllumioAPI, ConfigurationError

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
        from illumio.database import IllumioDatabase
        db = IllumioDatabase()
        db.init_db()
        return True
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base de données: {e}")
        return False