import sys
from illumio import IllumioAPI, ConfigurationError

def display_workloads(workloads, limit=5):
    """Affiche les informations des workloads."""
    print(f"Nombre total de workloads: {len(workloads)}")
    print("\nDétails des premiers workloads:")
    for i, workload in enumerate(workloads[:limit], 1):
        print(f"\n--- Workload {i} ---")
        print(f"Nom: {workload.get('name')}")
        print(f"Hostname: {workload.get('hostname')}")
        print(f"Description: {workload.get('description')}")
        print(f"État: {'En ligne' if workload.get('online') else 'Hors ligne'}")

def main():
    """Fonction principale du script."""
    try:
        # Initialisation de l'API
        api = IllumioAPI()
        
        # Test de connexion
        success, message = api.test_connection()
        if not success:
            print(f"Échec de la connexion: {message}")
            return 1
        
        print(f"✅ {message}")
        
        # Exemple: récupérer et afficher les workloads
        workloads = api.get_workloads()
        if workloads:
            display_workloads(workloads)
        
        return 0
    
    except ConfigurationError as e:
        print(f"Erreur de configuration: {e}")
        return 1
    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())