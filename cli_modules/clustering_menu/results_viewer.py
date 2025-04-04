# cli_modules/clustering_menu/results_viewer.py
#!/usr/bin/env python3
"""
Module pour visualiser les résultats d'analyse de clustering précédentes.
"""
import os
import json
import pandas as pd
import traceback
import webbrowser
from datetime import datetime

from cli_modules.menu_utils import print_header, get_user_choice
from illumio.utils.directory_manager import get_output_dir, list_files

def view_clustering_results():
    """Affiche et explore les résultats d'analyses de clustering précédentes."""
    print_header()
    print("VISUALISATION DES RÉSULTATS DE CLUSTERING\n")
    
    # Obtenir le dossier de sortie et lister les fichiers de résultats
    output_dir = get_output_dir()
    result_files = list_files('output', pattern='server_clusters_*_results.json')
    
    if not result_files:
        print(f"Aucun résultat d'analyse de clustering trouvé dans le dossier {output_dir}")
        print("Exécutez d'abord une analyse de clustering pour générer des résultats.")
        return
    
    # Trier les fichiers par date (en supposant un format de nom incluant un timestamp)
    # Format attendu: server_clusters_YYYYMMDD_HHMMSS_results.json
    sorted_files = sorted(result_files, reverse=True)
    
    print(f"\nRésultats d'analyses disponibles:")
    
    # Extraire la date à partir du nom de fichier pour un affichage plus convivial
    formatted_files = []
    for i, file in enumerate(sorted_files, 1):
        try:
            # Extraction du timestamp depuis le nom de fichier
            parts = file.split('_')
            timestamp_str = f"{parts[2]}_{parts[3]}"
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            date_str = timestamp.strftime('%d/%m/%Y %H:%M:%S')
            formatted_files.append((file, date_str))
            print(f"{i}. Analyse du {date_str}")
        except (IndexError, ValueError):
            # Fallback si le format n'est pas celui attendu
            formatted_files.append((file, "Date inconnue"))
            print(f"{i}. {file}")
    
    print("\n0. Revenir au menu précédent")
    
    # Demander à l'utilisateur de choisir un fichier
    choice = input("\nVotre choix (numéro du résultat): ")
    
    if choice == '0' or not choice:
        return
    
    try:
        file_index = int(choice) - 1
        if file_index < 0 or file_index >= len(sorted_files):
            print("Choix invalide.")
            return
        
        selected_file = sorted_files[file_index]
        base_name = selected_file.replace('_results.json', '')
        
        # Chemins des fichiers associés
        results_file = os.path.join(output_dir, selected_file)
        stats_file = os.path.join(output_dir, f"{base_name}_statistics.csv")
        visualization_file = os.path.join(output_dir, f"{base_name}_visualization.html")
        
        # Vérifier que les fichiers existent
        files_exist = {
            'results': os.path.exists(results_file),
            'stats': os.path.exists(stats_file),
            'viz': os.path.exists(visualization_file)
        }
        
        if not files_exist['results']:
            print(f"Erreur: Fichier de résultats {results_file} introuvable.")
            return
        
        # Charger et afficher les résultats
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        clusters = results.get('clusters', {})
        labels = results.get('labels', {})
        isolated_servers = results.get('isolated_servers', [])
        
        print("\n" + "="*50)
        print(f"RÉSULTATS DE L'ANALYSE DE CLUSTERING")
        print("="*50)
        
        num_clusters = len(clusters)
        num_servers = sum(len(servers) for servers in clusters.values())
        
        print(f"Nombre total de serveurs: {num_servers}")
        print(f"Nombre de clusters: {num_clusters}")
        print(f"Nombre de serveurs isolés: {len(isolated_servers)}")
        
        # Afficher les statistiques si disponibles
        if files_exist['stats']:
            try:
                stats_df = pd.read_csv(stats_file)
                print("\nStatistiques des principaux clusters:")
                print("-" * 80)
                print(f"{'ID':<5} {'Serveurs':<10} {'Apps uniques':<15} {'Apps/serveur':<15}")
                print("-" * 80)
                
                # Afficher les 5 plus grands clusters
                top_clusters = stats_df.nlargest(5, 'num_servers')
                for _, row in top_clusters.iterrows():
                    cluster_id = row['cluster_id']
                    num_servers = row['num_servers']
                    num_apps = row['num_unique_apps']
                    avg_apps = row['avg_apps_per_server']
                    print(f"{cluster_id:<5} {num_servers:<10} {num_apps:<15} {avg_apps:<15.2f}")
            except Exception as e:
                print(f"\nErreur lors de la lecture des statistiques: {e}")
                traceback.print_exc()
        
        # Menu d'actions
        print("\nActions disponibles:")
        options = [
            "Afficher les détails d'un cluster spécifique",
            "Afficher les serveurs isolés",
            "Afficher tous les labels générés",
            "Ouvrir la visualisation interactive"
        ]
        
        # N'ajouter cette option que si le fichier de visualisation existe
        if not files_exist['viz']:
            options.pop()
        
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        print("\n0. Revenir au menu précédent")
        
        action = get_user_choice(len(options))
        
        if action == 0:
            return
        
        if action == 1:
            # Afficher les détails d'un cluster
            cluster_list = list(clusters.keys())
            print("\nClusters disponibles:")
            
            # Trier les clusters par taille
            sorted_clusters = sorted(
                [(cid, len(clusters[cid])) for cid in cluster_list],
                key=lambda x: x[1],
                reverse=True
            )
            
            for i, (cid, size) in enumerate(sorted_clusters, 1):
                print(f"{i}. Cluster {cid} ({size} serveurs)")
            
            print("\n0. Revenir au menu précédent")
            
            cluster_choice = input("\nVotre choix (numéro du cluster): ")
            
            if cluster_choice == '0' or not cluster_choice:
                view_clustering_results()  # Retour au menu de visualisation
                return
            
            try:
                cluster_index = int(cluster_choice) - 1
                if cluster_index < 0 or cluster_index >= len(sorted_clusters):
                    print("Choix invalide.")
                    return
                
                selected_cluster_id = sorted_clusters[cluster_index][0]
                servers = clusters[selected_cluster_id]
                
                print(f"\nDétails du cluster {selected_cluster_id} ({len(servers)} serveurs):")
                print("-" * 50)
                
                # Afficher les serveurs par pages de 20
                servers_per_page = 20
                total_pages = (len(servers) + servers_per_page - 1) // servers_per_page
                current_page = 1
                
                while current_page <= total_pages:
                    start_idx = (current_page - 1) * servers_per_page
                    end_idx = min(start_idx + servers_per_page, len(servers))
                    
                    print(f"\nPage {current_page}/{total_pages}:")
                    for i, server in enumerate(servers[start_idx:end_idx], start_idx + 1):
                        label = labels.get(server, "N/A")
                        print(f"{i}. {server} - Label: {label}")
                    
                    if current_page < total_pages:
                        more = input("\nAfficher plus de serveurs? (o/n): ").lower()
                        if more != 'o' and more != 'oui':
                            break
                    
                    current_page += 1
                
                input("\nAppuyez sur Entrée pour revenir...")
                view_clustering_results()  # Retour au menu de visualisation
            
            except ValueError:
                print("Veuillez entrer un nombre valide.")
                view_clustering_results()
        
        elif action == 2:
            # Afficher les serveurs isolés
            if not isolated_servers:
                print("\nAucun serveur isolé trouvé.")
            else:
                print(f"\nServeurs isolés ({len(isolated_servers)}):")
                print("-" * 50)
                
                # Afficher les serveurs par pages de 20
                servers_per_page = 20
                total_pages = (len(isolated_servers) + servers_per_page - 1) // servers_per_page
                current_page = 1
                
                while current_page <= total_pages:
                    start_idx = (current_page - 1) * servers_per_page
                    end_idx = min(start_idx + servers_per_page, len(isolated_servers))
                    
                    print(f"\nPage {current_page}/{total_pages}:")
                    for i, server in enumerate(isolated_servers[start_idx:end_idx], start_idx + 1):
                        label = labels.get(server, "N/A")
                        print(f"{i}. {server} - Label: {label}")
                    
                    if current_page < total_pages:
                        more = input("\nAfficher plus de serveurs? (o/n): ").lower()
                        if more != 'o' and more != 'oui':
                            break
                    
                    current_page += 1
            
            input("\nAppuyez sur Entrée pour revenir...")
            view_clustering_results()
        
        elif action == 3:
            # Afficher tous les labels générés
            print("\nLabels générés:")
            print("-" * 80)
            
            # Regrouper les serveurs par label
            label_to_servers = {}
            for server, label in labels.items():
                if label not in label_to_servers:
                    label_to_servers[label] = []
                label_to_servers[label].append(server)
            
            # Trier les labels par nombre de serveurs
            sorted_labels = sorted(
                [(label, len(servers)) for label, servers in label_to_servers.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Afficher les labels
            for i, (label, count) in enumerate(sorted_labels, 1):
                print(f"{i}. {label} ({count} serveurs)")
            
            # Option pour voir les serveurs associés à un label
            print("\n0. Revenir au menu précédent")
            label_choice = input("\nEntrez un numéro pour voir les serveurs associés au label: ")
            
            if label_choice == '0' or not label_choice:
                view_clustering_results()
                return
            
            try:
                label_index = int(label_choice) - 1
                if label_index < 0 or label_index >= len(sorted_labels):
                    print("Choix invalide.")
                    return
                
                selected_label = sorted_labels[label_index][0]
                servers = label_to_servers[selected_label]
                
                print(f"\nServeurs avec le label '{selected_label}' ({len(servers)}):")
                print("-" * 50)
                
                # Afficher les serveurs par pages de 20
                servers_per_page = 20
                total_pages = (len(servers) + servers_per_page - 1) // servers_per_page
                current_page = 1
                
                while current_page <= total_pages:
                    start_idx = (current_page - 1) * servers_per_page
                    end_idx = min(start_idx + servers_per_page, len(servers))
                    
                    print(f"\nPage {current_page}/{total_pages}:")
                    for i, server in enumerate(servers[start_idx:end_idx], start_idx + 1):
                        print(f"{i}. {server}")
                    
                    if current_page < total_pages:
                        more = input("\nAfficher plus de serveurs? (o/n): ").lower()
                        if more != 'o' and more != 'oui':
                            break
                    
                    current_page += 1
                
                input("\nAppuyez sur Entrée pour revenir...")
                view_clustering_results()
            
            except ValueError:
                print("Veuillez entrer un nombre valide.")
                view_clustering_results()
        
        elif action == 4 and files_exist['viz']:
            # Ouvrir la visualisation interactive
            print(f"\nOuverture de la visualisation interactive: {visualization_file}")
            try:
                # Utiliser le navigateur par défaut pour ouvrir le fichier HTML
                webbrowser.open(f'file://{os.path.abspath(visualization_file)}')
                print("Si le navigateur ne s'ouvre pas automatiquement, veuillez ouvrir manuellement le fichier:")
                print(os.path.abspath(visualization_file))
            except Exception as e:
                print(f"Erreur lors de l'ouverture du fichier: {e}")
                print(f"Veuillez ouvrir manuellement le fichier: {os.path.abspath(visualization_file)}")
            
            input("\nAppuyez sur Entrée pour revenir...")
            view_clustering_results()
    
    except ValueError:
        print("Veuillez entrer un nombre valide.")
    except Exception as e:
        print(f"Erreur: {e}")
        traceback.print_exc()
        input("\nAppuyez sur Entrée pour revenir...")