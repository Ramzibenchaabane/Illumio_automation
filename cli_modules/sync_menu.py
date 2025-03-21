# cli_modules/sync_menu.py
#!/usr/bin/env python3
"""
Module de menu pour la synchronisation des données Illumio.
"""
import time
from illumio import IllumioSyncManager
from cli_modules.menu_utils import print_header, print_menu, get_user_choice, test_connection, initialize_database

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
        "Synchroniser uniquement les groupes de labels",
        "Synchroniser uniquement les ensembles de règles"  # Nouvelle option
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    start_time = time.time()
    
    # Créer le gestionnaire de synchronisation
    sync_manager = IllumioSyncManager()
    
    if choice == 1:
        print("\nSynchronisation complète en cours...")
        success = sync_manager.sync_all()
    else:
        print("\nSynchronisation partielle en cours...")
        # Mapper les choix de menu aux types de ressources
        resource_types = {
            2: ['workloads'],
            3: ['labels'],
            4: ['ip_lists'],
            5: ['services'],
            6: ['label_groups'],
            7: ['rule_sets']  # Ajout de l'option rule_sets
        }
        
        # Synchroniser les types de ressources spécifiés
        selected_types = resource_types.get(choice, [])
        if selected_types:
            success = sync_manager.sync_multiple(selected_types)
        else:
            print("Option non valide.")
            success = False
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        print(f"\n✅ Synchronisation terminée en {duration:.2f} secondes.")
    else:
        print(f"\n❌ Échec de la synchronisation après {duration:.2f} secondes.")
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")