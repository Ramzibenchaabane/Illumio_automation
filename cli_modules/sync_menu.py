#cli_modues/sync_menu.py
#!/usr/bin/env python3
import time
from illumio import IllumioAPI
from illumio.database import IllumioDatabase
from sync_data import sync_all_data
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
        "Synchroniser tous les éléments (mode asynchrone)",
        "Synchroniser uniquement les workloads",
        "Synchroniser uniquement les labels",
        "Synchroniser uniquement les listes d'IPs",
        "Synchroniser uniquement les services",
        "Synchroniser uniquement les groupes de labels"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    start_time = time.time()
    
    if choice == 1:
        print("\nSynchronisation complète en cours (mode asynchrone)...")
        success = sync_all_data()
    else:
        print("\nSynchronisation partielle en cours...")
        success = sync_specific_data(choice)
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        print(f"\n✅ Synchronisation terminée en {duration:.2f} secondes.")
    else:
        print(f"\n❌ Échec de la synchronisation après {duration:.2f} secondes.")
    
    input("\nAppuyez sur Entrée pour revenir au menu principal...")

def sync_specific_data(choice):
    """Synchronise un type spécifique de données."""
    try:
        api = IllumioAPI()
        db = IllumioDatabase()
        
        if choice == 2:  # Workloads
            print("Récupération des workloads (mode asynchrone)...")
            workloads = api.get_workloads()
            if workloads:
                print(f"✅ {len(workloads)} workloads récupérés.")
                if db.store_workloads(workloads):
                    print("✅ Workloads stockés dans la base de données.")
                    return True
                else:
                    print("❌ Erreur lors du stockage des workloads.")
            else:
                print("❌ Échec de la récupération des workloads.")
        
        elif choice == 3:  # Labels
            print("Récupération des labels (mode asynchrone)...")
            labels = api.get_labels()
            if labels:
                print(f"✅ {len(labels)} labels récupérés.")
                if db.store_labels(labels):
                    print("✅ Labels stockés dans la base de données.")
                    return True
                else:
                    print("❌ Erreur lors du stockage des labels.")
            else:
                print("❌ Échec de la récupération des labels.")
        
        elif choice == 4:  # IP Lists
            print("Récupération des listes d'IPs (mode asynchrone)...")
            ip_lists = api.get_ip_lists()
            if ip_lists:
                print(f"✅ {len(ip_lists)} listes d'IPs récupérées.")
                if db.store_ip_lists(ip_lists):
                    print("✅ Listes d'IPs stockées dans la base de données.")
                    return True
                else:
                    print("❌ Erreur lors du stockage des listes d'IPs.")
            else:
                print("❌ Échec de la récupération des listes d'IPs.")
        
        elif choice == 5:  # Services
            print("Récupération des services (mode asynchrone)...")
            services = api.get_services()
            if services:
                print(f"✅ {len(services)} services récupérés.")
                if db.store_services(services):
                    print("✅ Services stockés dans la base de données.")
                    return True
                else:
                    print("❌ Erreur lors du stockage des services.")
            else:
                print("❌ Échec de la récupération des services.")
        
        elif choice == 6:  # Label Groups
            print("Récupération des groupes de labels (mode asynchrone)...")
            label_groups = api.get_label_groups()
            if label_groups:
                print(f"✅ {len(label_groups)} groupes de labels récupérés.")
                if db.store_label_groups(label_groups):
                    print("✅ Groupes de labels stockés dans la base de données.")
                    return True
                else:
                    print("❌ Erreur lors du stockage des groupes de labels.")
            else:
                print("❌ Échec de la récupération des groupes de labels.")
        
        return False
    
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation: {e}")
        return False