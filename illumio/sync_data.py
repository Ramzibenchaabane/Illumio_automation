#!/usr/bin/env python3
import sys
import time
from illumio import IllumioAPI, ConfigurationError, APIRequestError
from illumio.database import IllumioDatabase

def sync_all_data():
    """Synchronise toutes les données depuis Illumio PCE vers la base de données locale."""
    try:
        # Initialiser l'API et la base de données
        api = IllumioAPI()
        db = IllumioDatabase()
        
        # Initialiser la structure de la base de données
        print("Initialisation de la base de données...")
        if not db.init_db():
            print("Erreur lors de l'initialisation de la base de données.")
            return False
        
        # Test de connexion
        success, message = api.test_connection()
        if not success:
            print(f"Échec de la connexion: {message}")
            return False
        
        print(f"✅ {message}")
        
        # Synchroniser les labels
        print("\nRécupération des labels...")
        labels = api.get_labels()
        if labels:
            print(f"✅ {len(labels)} labels récupérés.")
            if db.store_labels(labels):
                print("✅ Labels stockés dans la base de données.")
            else:
                print("❌ Erreur lors du stockage des labels.")
        else:
            print("❌ Échec de la récupération des labels.")
        
        # Synchroniser les workloads
        print("\nRécupération des workloads...")
        workloads = api.get_workloads()
        if workloads:
            print(f"✅ {len(workloads)} workloads récupérés.")
            if db.store_workloads(workloads):
                print("✅ Workloads stockés dans la base de données.")
            else:
                print("❌ Erreur lors du stockage des workloads.")
        else:
            print("❌ Échec de la récupération des workloads.")
        
        # Synchroniser les IP Lists
        print("\nRécupération des listes d'IPs...")
        ip_lists = api.get_ip_lists()
        if ip_lists:
            print(f"✅ {len(ip_lists)} listes d'IPs récupérées.")
            if db.store_ip_lists(ip_lists):
                print("✅ Listes d'IPs stockées dans la base de données.")
            else:
                print("❌ Erreur lors du stockage des listes d'IPs.")
        else:
            print("❌ Échec de la récupération des listes d'IPs.")
        
        # Synchroniser les services
        print("\nRécupération des services...")
        services = api.get_services()
        if services:
            print(f"✅ {len(services)} services récupérés.")
            if db.store_services(services):
                print("✅ Services stockés dans la base de données.")
            else:
                print("❌ Erreur lors du stockage des services.")
        else:
            print("❌ Échec de la récupération des services.")
        
        # Synchroniser les groupes de labels
        print("\nRécupération des groupes de labels...")
        label_groups = api.get_label_groups()
        if label_groups:
            print(f"✅ {len(label_groups)} groupes de labels récupérés.")
            if db.store_label_groups(label_groups):
                print("✅ Groupes de labels stockés dans la base de données.")
            else:
                print("❌ Erreur lors du stockage des groupes de labels.")
        else:
            print("❌ Échec de la récupération des groupes de labels.")
        
        print("\n✅ Synchronisation terminée avec succès.")
        return True
    
    except ConfigurationError as e:
        print(f"Erreur de configuration: {e}")
        return False
    except APIRequestError as e:
        print(f"Erreur API: {e}")
        return False
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False

def main():
    """Fonction principale."""
    print("=== Synchronisation des données Illumio ===")
    start_time = time.time()
    
    success = sync_all_data()
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\nDurée de la synchronisation: {duration:.2f} secondes")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())