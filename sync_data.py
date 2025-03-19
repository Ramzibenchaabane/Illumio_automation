# sync_data.py
#!/usr/bin/env python3
"""
Script pour synchroniser les données depuis l'API Illumio vers la base de données locale.
"""
import sys
import time
import argparse
from illumio import IllumioSyncManager, ConfigurationError, APIRequestError

def sync_all_data():
    """Synchronise toutes les données depuis Illumio PCE vers la base de données locale."""
    sync_manager = IllumioSyncManager()
    return sync_manager.sync_all()

def sync_specific_data(resource_types):
    """
    Synchronise des types de données spécifiques.
    
    Args:
        resource_types (list): Liste des types de ressources à synchroniser
    
    Returns:
        bool: True si la synchronisation a réussi, False sinon
    """
    sync_manager = IllumioSyncManager()
    return sync_manager.sync_multiple(resource_types)

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Synchronisation des données Illumio')
    parser.add_argument('--all', action='store_true', help='Synchroniser tous les types de données')
    parser.add_argument('--workloads', action='store_true', help='Synchroniser les workloads')
    parser.add_argument('--labels', action='store_true', help='Synchroniser les labels')
    parser.add_argument('--ip-lists', action='store_true', help='Synchroniser les listes d\'IPs')
    parser.add_argument('--services', action='store_true', help='Synchroniser les services')
    parser.add_argument('--label-groups', action='store_true', help='Synchroniser les groupes de labels')
    
    args = parser.parse_args()
    
    print("=== Synchronisation des données Illumio ===")
    start_time = time.time()
    
    # Déterminer les types de ressources à synchroniser
    if args.all:
        success = sync_all_data()
    else:
        resource_types = []
        if args.workloads:
            resource_types.append('workloads')
        if args.labels:
            resource_types.append('labels')
        if args.ip_lists:
            resource_types.append('ip_lists')
        if args.services:
            resource_types.append('services')
        if args.label_groups:
            resource_types.append('label_groups')
        
        if not resource_types:
            print("Aucun type de données spécifié. Utilisez --all pour tout synchroniser ou spécifiez des types spécifiques.")
            return 1
        
        success = sync_specific_data(resource_types)
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"\nDurée de la synchronisation: {duration:.2f} secondes")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())