# cli_modules/clustering_menu/cluster_analyzer.py
#!/usr/bin/env python3
"""
Module pour l'analyse de clustering de serveurs avec l'algorithme de Louvain.
"""
import os
import json
import time
import traceback
from datetime import datetime
import networkx as nx
import community as community_louvain
from collections import defaultdict
import pandas as pd

from cli_modules.menu_utils import print_header, print_menu, get_user_choice
from illumio.utils.directory_manager import get_input_dir, get_output_dir, list_files, get_file_path

def run_server_clustering_analysis():
    """Exécute une analyse de clustering sur les données de serveurs."""
    print_header()
    print("ANALYSE DE CLUSTERING DE SERVEURS\n")
    
    # Options pour l'analyse de clustering
    options = [
        "Sélectionner un fichier (Excel ou JSON)",
        "Générer un exemple de fichier Excel",
        "Afficher le format de fichier attendu"
    ]
    
    print_menu(options)
    choice = get_user_choice(len(options))
    
    if choice == 0:
        return
    
    if choice == 1:
        select_and_analyze_file()
    elif choice == 2:
        generate_example_excel()
    elif choice == 3:
        show_expected_format()
    
    # Retour au menu précédent est géré dans chaque fonction

def select_and_analyze_file():
    """Sélectionne un fichier (Excel ou JSON) et lance l'analyse de clustering."""
    print_header()
    print("SÉLECTION D'UN FICHIER POUR L'ANALYSE DE CLUSTERING\n")
    
    # Obtenir le dossier d'entrée et la liste des fichiers Excel et JSON
    input_dir = get_input_dir()
    excel_files = list_files('input', extension='.xlsx') + list_files('input', extension='.xls')
    json_files = list_files('input', extension='.json')
    
    all_files = excel_files + json_files
    if not all_files:
        print(f"Aucun fichier Excel ou JSON trouvé dans le dossier {input_dir}")
        print("Veuillez y placer un fichier Excel ou JSON contenant des données de serveurs ou générer un exemple.")
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")
        return
    
    # Afficher la liste des fichiers numérotés
    print(f"\nFichiers disponibles dans {input_dir}:")
    for i, file in enumerate(all_files, 1):
        file_type = "Excel" if file.endswith(('.xlsx', '.xls')) else "JSON"
        print(f"{i}. {file} [{file_type}]")
    
    print("\n0. Revenir au menu précédent")
    
    # Demander à l'utilisateur de choisir un fichier par son numéro
    choice = input("\nVotre choix (numéro du fichier): ")
    
    if choice == '0' or not choice:
        return
    
    try:
        file_index = int(choice) - 1
        if file_index < 0 or file_index >= len(all_files):
            print("Choix invalide.")
            input("\nAppuyez sur Entrée pour revenir au menu précédent...")
            return
        
        file_name = all_files[file_index]
        file_path = os.path.join(input_dir, file_name)
        
        print(f"\nAnalyse du fichier: {file_name}")
        
        # Générer un timestamp unique pour cette analyse
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Préparer les noms de fichiers de sortie avec le timestamp
        output_dir = get_output_dir()
        base_output_name = f"server_clusters_{timestamp}"
        results_file = os.path.join(output_dir, f"{base_output_name}_results.json")
        excel_file = os.path.join(output_dir, f"{base_output_name}_results.xlsx")
        visualization_file = os.path.join(output_dir, f"{base_output_name}_visualization.html")
        
        # Déterminer le type de fichier et le traiter en conséquence
        is_excel = file_name.endswith(('.xlsx', '.xls'))
        
        # Exécuter l'analyse
        print("\nDémarrage de l'analyse de clustering...")
        start_time = time.time()
        
        try:
            # Charger les données selon le format du fichier
            if is_excel:
                servers_data = load_excel_data(file_path)
                print(f"Données Excel chargées : {len(servers_data)} serveurs")
            else:
                servers_data = load_json_data(file_path)
                print(f"Données JSON chargées : {len(servers_data)} serveurs")
            
            # Appel à la fonction d'analyse avec le nouveau paramètre excel_file
            clusters, labels, graph, cluster_stats = analyze_server_clustering(
                servers_data, 
                results_file, 
                excel_file,
                visualization_file,
                is_data_loaded=True
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n✅ Analyse terminée en {duration:.2f} secondes.")
            print(f"Nombre de serveurs analysés: {len(graph.nodes())}")
            print(f"Nombre de clusters identifiés: {len(clusters)}")
            
            # Afficher un résumé des principaux clusters
            print("\nPrincipaux clusters identifiés:")
            top_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            for cluster_id, servers in top_clusters:
                print(f"  - Cluster {cluster_id}: {len(servers)} serveurs")
            
            # Indiquer où les fichiers ont été sauvegardés
            print("\nFichiers générés:")
            print(f"  - Résultats JSON: {results_file}")
            print(f"  - Résultats Excel: {excel_file}")
            print(f"  - Visualisation HTML: {visualization_file}")
            print("\nVous pouvez ouvrir le fichier HTML dans votre navigateur pour explorer interactivement les clusters.")
            print("Le fichier Excel contient les statistiques et les détails des clusters.")
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'analyse: {e}")
            traceback.print_exc()
    
    except ValueError:
        print("Veuillez entrer un nombre valide.")
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")
    except Exception as e:
        print(f"Erreur: {e}")
        traceback.print_exc()
    
    input("\nAppuyez sur Entrée pour revenir au menu précédent...")

def export_results_to_excel(clusters, labels, graph, cluster_stats, output_file):
    """
    Exporte les résultats de l'analyse de clustering dans un fichier Excel à deux feuilles,
    avec une approche simplifiée pour éviter les problèmes de corruption.
    
    Args:
        clusters (dict): Dictionnaire des clusters (id: liste de serveurs)
        labels (dict): Dictionnaire des labels (serveur: label)
        graph (nx.Graph): Graphe des serveurs
        cluster_stats (pd.DataFrame): Statistiques des clusters
        output_file (str): Chemin du fichier Excel de sortie
    """
    try:
        print(f"Exportation des résultats vers Excel: {output_file}")
        
        # 1. Préparation des données pour la feuille de statistiques
        stats_data = []
        # En-têtes
        stats_data.append(['ID Cluster', 'Nombre de serveurs', 
                          'Nombre d\'applications uniques', 
                          'Moyenne d\'applications par serveur'])
        
        # Données des statistiques
        for _, row in cluster_stats.iterrows():
            stats_data.append([
                str(row['cluster_id']),  # Convertir en string explicitement
                row['num_servers'],
                row['num_unique_apps'],
                row['avg_apps_per_server']
            ])
        
        # 2. Préparation des données pour la feuille de clusters
        clusters_data = []
        # En-têtes
        clusters_data.append(['Groupe', 'Serveur', 'Cluster', 'Applications', 'Nombre d\'applications'])
        
        # Données des clusters
        for cluster_id, servers in clusters.items():
            cluster_name = f"Cluster_{cluster_id}"
            for server in servers:
                apps = graph.nodes[server]["apps"]
                apps_str = ", ".join(apps)
                clusters_data.append([
                    cluster_name,
                    server,
                    cluster_name,
                    apps_str,
                    len(apps)
                ])
        
        # 3. Création du fichier Excel avec openpyxl de manière simple
        import openpyxl
        
        wb = openpyxl.Workbook()
        
        # Feuille Statistiques
        ws_stats = wb.active
        ws_stats.title = "Statistiques"
        
        # Ajouter les données statistiques
        for row in stats_data:
            ws_stats.append(row)
        
        # Feuille Clusters
        ws_clusters = wb.create_sheet(title="Clusters")
        
        # Ajouter les données de clusters
        for row in clusters_data:
            ws_clusters.append(row)
        
        # Sauvegarder le fichier
        wb.save(output_file)
        
        print(f"✅ Export Excel terminé: {output_file}")
        return True
        
    except ImportError:
        print("❌ La bibliothèque openpyxl n'est pas installée. Exportation en CSV à la place.")
        # Exporter en CSV si openpyxl n'est pas disponible
        stats_file = output_file.replace('.xlsx', '_statistics.csv')
        clusters_file = output_file.replace('.xlsx', '_clusters.csv')
        
        # Sauvegarder en CSV
        import csv
        
        with open(stats_file, 'w', newline='') as f:
            writer = csv.writer(f)
            for row in stats_data:
                writer.writerow(row)
        
        with open(clusters_file, 'w', newline='') as f:
            writer = csv.writer(f)
            for row in clusters_data:
                writer.writerow(row)
        
        print(f"✅ Export CSV terminé: {stats_file} et {clusters_file}")
        return False
        
    except Exception as e:
        print(f"❌ Erreur lors de l'export Excel: {e}")
        import traceback
        traceback.print_exc()
        
        # Tentative de sauvegarde en CSV
        try:
            stats_file = output_file.replace('.xlsx', '_statistics.csv')
            clusters_file = output_file.replace('.xlsx', '_clusters.csv')
            
            # Utiliser le module csv standard pour plus de robustesse
            import csv
            
            with open(stats_file, 'w', newline='') as f:
                writer = csv.writer(f)
                for row in stats_data:
                    writer.writerow(row)
            
            with open(clusters_file, 'w', newline='') as f:
                writer = csv.writer(f)
                for row in clusters_data:
                    writer.writerow(row)
            
            print(f"✅ Sauvegarde CSV terminée: {stats_file} et {clusters_file}")
        except Exception as csv_error:
            print(f"❌ Échec de la sauvegarde CSV: {csv_error}")
        
        return False

def load_excel_data(file_path):
    """
    Charge les données d'un fichier Excel au format attendu pour l'analyse de clustering.
    
    Args:
        file_path (str): Chemin vers le fichier Excel
        
    Returns:
        list: Liste de dictionnaires au format {"server": str, "apps": list}
    """
    try:
        # Charger le fichier Excel
        df = pd.read_excel(file_path)
        
        # Vérifier les colonnes requises
        required_columns = ["server", "applications"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"La colonne '{col}' est manquante dans le fichier Excel.")
        
        # Convertir le DataFrame en format attendu pour l'analyse
        servers_data = []
        
        for _, row in df.iterrows():
            server = str(row["server"]).strip()
            
            # Traiter les applications (séparées par des sauts de ligne)
            apps_text = str(row["applications"])
            if pd.isna(apps_text) or apps_text.strip() == "":
                apps = []
            else:
                # Séparer par saut de ligne et nettoyer
                apps = [app.strip() for app in apps_text.split("\n") if app.strip()]
            
            # N'ajouter que si le serveur a un nom et n'est pas déjà dans la liste
            if server and not pd.isna(server):
                servers_data.append({
                    "server": server,
                    "apps": apps
                })
        
        return servers_data
        
    except Exception as e:
        raise Exception(f"Erreur lors du chargement du fichier Excel: {e}")

def load_json_data(file_path):
    """
    Charge les données d'un fichier JSON.
    
    Args:
        file_path (str): Chemin vers le fichier JSON
        
    Returns:
        list: Données du fichier JSON
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Vérifier le format des données
    if not isinstance(data, list):
        raise ValueError("Le fichier JSON doit contenir une liste de serveurs")
    
    # Vérifier que chaque élément a la structure attendue
    for item in data:
        if not isinstance(item, dict) or "server" not in item or "apps" not in item:
            raise ValueError("Format de données incorrect. Chaque élément doit contenir 'server' et 'apps'")
    
    return data

def generate_example_excel():
    """Génère un exemple de fichier Excel pour l'analyse de clustering."""
    print_header()
    print("GÉNÉRATION D'UN EXEMPLE DE FICHIER EXCEL\n")
    
    # Données d'exemple
    example_data = [
        {"server": "server1.example.com", "applications": "app1\napp2\napp3"},
        {"server": "server2.example.com", "applications": "app1\napp4"},
        {"server": "server3.example.com", "applications": "app2\napp3\napp5"},
        {"server": "server4.example.com", "applications": "app4\napp5"},
        {"server": "server5.example.com", "applications": "app1\napp2\napp3"},
        {"server": "server6.example.com", "applications": "app6"},
        {"server": "server7.example.com", "applications": "app7\napp8"},
        {"server": "server8.example.com", "applications": "app7\napp8"},
        {"server": "server9.example.com", "applications": "app9"},
        {"server": "server10.example.com", "applications": "app1\napp10"}
    ]
    
    # Créer un DataFrame pandas
    df = pd.DataFrame(example_data)
    
    # Enregistrer le DataFrame dans un fichier Excel
    input_dir = get_input_dir()
    example_file = os.path.join(input_dir, "example_servers_data.xlsx")
    
    try:
        df.to_excel(example_file, index=False)
        print(f"✅ Exemple de fichier Excel généré: {example_file}")
        print("Ce fichier contient 10 serveurs avec diverses applications.")
        print("Vous pouvez maintenant l'utiliser pour l'analyse de clustering.")
    except Exception as e:
        print(f"❌ Erreur lors de la création du fichier Excel: {e}")
    
    input("\nAppuyez sur Entrée pour revenir au menu précédent...")

def generate_example_json():
    """Génère un exemple de fichier JSON pour l'analyse de clustering."""
    print_header()
    print("GÉNÉRATION D'UN EXEMPLE DE FICHIER JSON\n")
    
    example_data = [
        {
            "server": "server1.example.com",
            "apps": ["app1", "app2", "app3"]
        },
        {
            "server": "server2.example.com",
            "apps": ["app1", "app4"]
        },
        {
            "server": "server3.example.com",
            "apps": ["app2", "app3", "app5"]
        },
        {
            "server": "server4.example.com",
            "apps": ["app4", "app5"]
        },
        {
            "server": "server5.example.com",
            "apps": ["app1", "app2", "app3"]
        },
        {
            "server": "server6.example.com",
            "apps": ["app6"]
        },
        {
            "server": "server7.example.com",
            "apps": ["app7", "app8"]
        },
        {
            "server": "server8.example.com",
            "apps": ["app7", "app8"]
        },
        {
            "server": "server9.example.com",
            "apps": ["app9"]
        },
        {
            "server": "server10.example.com",
            "apps": ["app1", "app10"]
        }
    ]
    
    input_dir = get_input_dir()
    example_file = os.path.join(input_dir, "example_servers_data.json")
    
    with open(example_file, 'w') as f:
        json.dump(example_data, f, indent=2)
    
    print(f"✅ Exemple de fichier JSON généré: {example_file}")
    print("Ce fichier contient 10 serveurs avec diverses applications.")
    print("Vous pouvez maintenant l'utiliser pour l'analyse de clustering.")
    
    input("\nAppuyez sur Entrée pour revenir au menu précédent...")

def show_expected_format():
    """Affiche le format attendu pour les fichiers d'entrée."""
    print_header()
    print("FORMAT DE FICHIER ATTENDU\n")
    
    print("Deux formats de fichiers sont acceptés:\n")
    
    print("1. Format Excel:")
    print("   - Le fichier doit contenir deux colonnes: 'server' et 'applications'")
    print("   - Chaque ligne représente un serveur")
    print("   - La colonne 'server' contient l'identifiant unique du serveur")
    print("   - La colonne 'applications' contient les applications hébergées sur ce serveur,")
    print("     séparées par des sauts de ligne\n")
    
    print("   Exemple de contenu Excel:")
    print("   ┌─────────────────────┬───────────────┐")
    print("   │ server              │ applications  │")
    print("   ├─────────────────────┼───────────────┤")
    print("   │ server1.example.com │ app1          │")
    print("   │                     │ app2          │")
    print("   │                     │ app3          │")
    print("   ├─────────────────────┼───────────────┤")
    print("   │ server2.example.com │ app1          │")
    print("   │                     │ app4          │")
    print("   └─────────────────────┴───────────────┘\n")
    
    print("2. Format JSON:")
    print("   - Le fichier doit contenir une liste d'objets JSON")
    print("   - Chaque objet doit avoir les propriétés 'server' et 'apps'")
    print("   - 'server' est une chaîne de caractères")
    print("   - 'apps' est une liste de chaînes de caractères\n")
    
    print("   Exemple de format JSON:")
    print("""   [
     {
       "server": "server1.example.com",
       "apps": ["app1", "app2", "app3"]
     },
     {
       "server": "server2.example.com",
       "apps": ["app1", "app4"]
     }
   ]""")
    
    print("\nLe module de clustering analysera ces données pour identifier des groupes de serveurs")
    print("qui partagent des applications similaires, en utilisant l'algorithme de Louvain.")
    
    input("\nAppuyez sur Entrée pour revenir au menu précédent...")

def analyze_server_clustering(input_path, results_file, stats_file, visualization_file, is_data_loaded=False):
    """
    Analyse de clustering des serveurs.
    
    Args:
        input_path (str ou list): Chemin du fichier JSON ou données déjà chargées
        results_file (str): Chemin où sauvegarder les résultats JSON
        stats_file (str): Chemin où sauvegarder les statistiques CSV
        visualization_file (str): Chemin où sauvegarder la visualisation HTML
        is_data_loaded (bool): Si True, input_path contient déjà les données chargées
        
    Returns:
        tuple: (clusters, labels, server_graph, cluster_stats)
    """
    # Charger les données si nécessaire
    print("Chargement des données...")
    if is_data_loaded:
        servers_data = input_path
    else:
        servers_data = load_json_data(input_path)
    
    # Vérifier le format des données
    if not isinstance(servers_data, list):
        raise ValueError("Les données doivent être une liste de serveurs")
    
    if not servers_data:
        raise ValueError("Aucune donnée de serveur trouvée")
    
    # Vérifier la structure des données
    for server_info in servers_data[:5]:
        if not isinstance(server_info, dict) or "server" not in server_info or "apps" not in server_info:
            raise ValueError("Format de données incorrect. Chaque élément doit contenir 'server' et 'apps'")
    
    # Créer le graphe des serveurs
    print("Création du graphe de serveurs...")
    server_graph = create_server_graph(servers_data)
    
    # Appliquer l'algorithme de Louvain
    print("Application de l'algorithme de Louvain pour le clustering...")
    clusters, partition = apply_louvain_clustering(server_graph)
    
    # Créer des labels pour Illumio
    print("Création des labels pour les serveurs...")
    labels, isolated_servers = create_labels(clusters, server_graph)
    
    # Analyser les clusters
    print("Analyse des statistiques des clusters...")
    cluster_stats = analyze_clusters(clusters, server_graph)
    
    # Sauvegarder les résultats
    print("Sauvegarde des résultats...")
    results = {
        "clusters": {str(k): v for k, v in clusters.items()},
        "labels": labels,
        "isolated_servers": isolated_servers
    }
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Sauvegarder les statistiques
    cluster_stats.to_csv(stats_file, index=False)
    
    # Créer la visualisation interactive D3.js
    print("Génération de la visualisation interactive...")
    create_d3_network_html(server_graph, partition, clusters, visualization_file)
    
    return clusters, labels, server_graph, cluster_stats

def create_server_graph(servers_data):
    """
    Créer un graphe non-orienté où les nœuds sont les serveurs.
    Les arêtes sont pondérées par le nombre d'applications communes.
    """
    G = nx.Graph()
    
    # Ajouter tous les serveurs comme nœuds
    for server_info in servers_data:
        server = server_info["server"]
        G.add_node(server, apps=server_info["apps"])
    
    # Ajouter les arêtes entre serveurs partageant des applications
    servers = list(G.nodes())
    for i in range(len(servers)):
        server1 = servers[i]
        apps1 = set(G.nodes[server1]["apps"])
        
        for j in range(i+1, len(servers)):
            server2 = servers[j]
            apps2 = set(G.nodes[server2]["apps"])
            
            # Calcul des applications communes
            common_apps = apps1.intersection(apps2)
            
            # S'il y a des applications communes, ajouter une arête pondérée
            if common_apps:
                weight = len(common_apps)
                G.add_edge(server1, server2, weight=weight)
    
    return G

def apply_louvain_clustering(graph):
    """Appliquer l'algorithme de Louvain pour détecter les communautés."""
    # Appliquer l'algorithme de Louvain
    partition = community_louvain.best_partition(graph)
    
    # Organiser les résultats par cluster
    clusters = defaultdict(list)
    for server, cluster_id in partition.items():
        clusters[cluster_id].append(server)
    
    return clusters, partition

def create_labels(clusters, graph):
    """Créer des labels applicatifs pour Illumio basés sur les clusters."""
    labels = {}
    isolated_servers = []
    
    for cluster_id, servers in clusters.items():
        # Si le cluster ne contient qu'un seul serveur avec une seule application
        if len(servers) == 1 and len(graph.nodes[servers[0]]["apps"]) == 1:
            isolated_servers.append(servers[0])
            labels[servers[0]] = f"APP_{graph.nodes[servers[0]]['apps'][0]}"
        else:
            # Trouver les applications communes dans ce cluster
            common_apps = set()
            for server in servers:
                if not common_apps:
                    common_apps = set(graph.nodes[server]["apps"])
                else:
                    common_apps = common_apps.intersection(set(graph.nodes[server]["apps"]))
            
            # Si pas d'applications communes, trouver les applications les plus fréquentes
            if not common_apps:
                app_counts = defaultdict(int)
                for server in servers:
                    for app in graph.nodes[server]["apps"]:
                        app_counts[app] += 1
                
                # Trier les applications par fréquence
                common_apps = sorted(app_counts.keys(), key=lambda x: app_counts[x], reverse=True)[:3]
            
            # Créer un label pour ce cluster
            cluster_label = f"CLUSTER_{cluster_id}_" + "_".join(sorted([str(app) for app in common_apps])[:3])
            
            # Assigner ce label à tous les serveurs du cluster
            for server in servers:
                labels[server] = cluster_label
    
    return labels, isolated_servers

def analyze_clusters(clusters, graph):
    """Analyser les clusters pour obtenir des statistiques."""
    cluster_stats = []
    
    for cluster_id, servers in clusters.items():
        # Collecter toutes les applications dans ce cluster
        all_apps = set()
        for server in servers:
            all_apps.update(graph.nodes[server]["apps"])
        
        # Calculer la moyenne d'applications par serveur dans ce cluster
        avg_apps = sum(len(graph.nodes[server]["apps"]) for server in servers) / len(servers)
        
        cluster_stats.append({
            "cluster_id": cluster_id,
            "num_servers": len(servers),
            "num_unique_apps": len(all_apps),
            "avg_apps_per_server": avg_apps,
        })
    
    return pd.DataFrame(cluster_stats).sort_values("num_servers", ascending=False)

def create_d3_network_html(graph, partition, clusters, output_file):
    """
    Crée une visualisation D3.js où les nœuds peuvent être déplacés avec la souris.
    """
    # Préparer les données pour D3.js
    nodes = []
    for node in graph.nodes():
        apps = graph.nodes[node]["apps"]
        cluster_id = partition[node]
        nodes.append({
            "id": node,
            "group": cluster_id,
            "apps": apps,
            "app_count": len(apps),
            "label": node
        })
    
    links = []
    for source, target, data in graph.edges(data=True):
        links.append({
            "source": source,
            "target": target,
            "value": data["weight"]
        })
    
    # Nombre de groupes (clusters)
    num_groups = len(clusters)
    
    # Créer le fichier HTML avec la visualisation D3.js
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Clusters de serveurs Illumio</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                overflow: hidden;
            }}
            
            .controls {{
                position: absolute;
                top: 10px;
                left: 10px;
                background: white;
                padding: 10px;
                border-radius: 5px;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
                z-index: 1;
            }}
            
            .node-label {{
                pointer-events: none;
                font-size: 10px;
            }}
            
            .tooltip {{
                position: absolute;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                pointer-events: none;
                opacity: 0;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
                max-width: 300px;
                word-wrap: break-word;
            }}
            
            button {{
                margin: 5px;
                padding: 5px 10px;
                cursor: pointer;
            }}

            .cluster-hull {{
                fill: rgba(200, 200, 200, 0.1);
                stroke: rgba(0, 0, 0, 0.2);
                stroke-width: 1.5px;
                stroke-linejoin: round;
            }}
            
            .cluster-label {{
                font-size: 14px;
                font-weight: bold;
                text-anchor: middle;
                pointer-events: none;
            }}
        </style>
    </head>
    <body>
        <div class="controls">
            <h3>Clusters de serveurs avec l'algorithme de Louvain</h3>
            <button id="reset">Réinitialiser la vue</button>
            <button id="toggle-labels">Afficher/Masquer les étiquettes</button>
            <button id="group-clusters">Regrouper par cluster</button>
            <button id="toggle-cluster-hulls">Afficher/Masquer les contours</button>
            <div>
                <label>Attraction: <input type="range" id="attraction-slider" min="0.1" max="2" step="0.1" value="1"></label>
            </div>
            <div>
                <label>Répulsion: <input type="range" id="repulsion-slider" min="100" max="2000" step="100" value="800"></label>
            </div>
            <div>
                <label>Charge des liens: <input type="range" id="link-slider" min="0.1" max="2" step="0.1" value="1"></label>
            </div>
            <div>
                <input type="checkbox" id="freeze" checked>
                <label for="freeze">Geler la position après déplacement</label>
            </div>
        </div>
        
        <div id="tooltip" class="tooltip"></div>
        
        <script>
            // Données du graphe
            const graph = {{
                "nodes": {json.dumps(nodes)},
                "links": {json.dumps(links)}
            }};
            
            // Paramètres initiaux
            let showLabels = false;
            let showClusterHulls = false;
            const width = window.innerWidth;
            const height = window.innerHeight;
            
            // Créer un tooltip
            const tooltip = d3.select("#tooltip");
            
            // Créer le svg
            const svg = d3.select("body").append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Groupe principal
            const g = svg.append("g");
            
            // Groupe pour les hulls des clusters (contours)
            const hullsGroup = g.append("g").attr("class", "hulls");
            
            // Groupe pour les étiquettes des clusters
            const clusterLabelsGroup = g.append("g").attr("class", "cluster-labels");
            
            // Ajouter un zoom
            svg.call(d3.zoom()
                .extent([[0, 0], [width, height]])
                .scaleExtent([0.1, 10])
                .on("zoom", (event) => {{
                    g.attr("transform", event.transform);
                }}));
            
            // Couleurs pour les clusters
            const color = d3.scaleOrdinal(d3.schemeCategory10)
                .domain(d3.range({num_groups}));
            
            // Définir la fonction drag
            function drag(simulation) {{
                function dragstarted(event, d) {{
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    d.fx = d.x;
                    d.fy = d.y;
                }}
                
                function dragged(event, d) {{
                    d.fx = event.x;
                    d.fy = event.y;
                }}
                
                function dragended(event, d) {{
                    if (!event.active) simulation.alphaTarget(0);
                    if (!document.getElementById("freeze").checked) {{
                        d.fx = null;
                        d.fy = null;
                    }}
                }}
                
                return d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended);
            }}
            
            // Fonction pour créer un contour autour des nœuds du même groupe
            function drawClusterHulls() {{
                // Supprimer les anciens hulls
                hullsGroup.selectAll("*").remove();
                clusterLabelsGroup.selectAll("*").remove();
                
                if (!showClusterHulls) return;
                
                // Grouper les nœuds par cluster
                const clusters = d3.group(graph.nodes, n => n.group);
                
                // Créer un contour pour chaque cluster
                clusters.forEach((nodes, groupId) => {{
                    // Obtenir les positions des nœuds
                    const points = nodes.map(n => [n.x, n.y]);
                    if (points.length < 3) return; // Besoin de 3 points minimum pour un hull
                    
                    // Créer le contour (enveloppe convexe)
                    const hull = d3.polygonHull(points);
                    if (!hull) return;
                    
                    // Ajouter un padding au contour
                    const padding = 20;
                    const centroid = d3.polygonCentroid(hull);
                    const paddedHull = hull.map(point => {{
                        // Déplacer chaque point du contour vers l'extérieur
                        const angle = Math.atan2(point[1] - centroid[1], point[0] - centroid[0]);
                        return [
                            point[0] + padding * Math.cos(angle),
                            point[1] + padding * Math.sin(angle)
                        ];
                    }});
                    
                    // Dessiner le contour
                    hullsGroup.append("path")
                        .attr("d", `M${{paddedHull.join("L")}}Z`)
                        .attr("class", "cluster-hull")
                        .style("fill", function() {{
                            // Créer une couleur avec opacité
                            const baseColor = d3.color(color(groupId));
                            baseColor.opacity = 0.2;
                            return baseColor;
                        }});
                    
                    // Ajouter une étiquette au centre du cluster
                    const clusterCenter = d3.polygonCentroid(hull);
                    clusterLabelsGroup.append("text")
                        .attr("class", "cluster-label")
                        .attr("x", clusterCenter[0])
                        .attr("y", clusterCenter[1])
                        .text(`Cluster ${{groupId}}`)
                        .style("fill", d3.color(color(groupId)).darker(1));
                }});
            }}
            
            // Initialiser la simulation
            const simulation = d3.forceSimulation(graph.nodes)
                .force("link", d3.forceLink(graph.links).id(n => n.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-800))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius(n => 5 + n.app_count).iterations(2));
            
            // Créer les liens
            const link = g.append("g")
                .selectAll("line")
                .data(graph.links)
                .enter().append("line")
                .attr("stroke", "#888")
                .attr("stroke-opacity", 0.3)
                .attr("stroke-width", l => Math.sqrt(l.value) * 0.5);
            
            // Créer les nœuds
            const node = g.append("g")
                .selectAll("circle")
                .data(graph.nodes)
                .enter().append("circle")
                .attr("r", n => 3 + Math.sqrt(n.app_count) * 2)
                .attr("fill", n => color(n.group))
                .attr("stroke", "#fff")
                .attr("stroke-width", 1.5)
                .call(drag(simulation))
                .each(function(n) {{
                    // Stocker une référence à l'élément DOM dans le nœud pour l'animation
                    n.element = this;
                }})
                .on("mouseover", function(event, n) {{
                    const serverInfo = `<strong>Serveur:</strong> ${{n.id}}<br>
                                      <strong>Cluster:</strong> ${{n.group}}<br>
                                      <strong>Applications:</strong> ${{n.apps.join(", ")}}<br>
                                      <strong>Nombre d'apps:</strong> ${{n.app_count}}`;
                    
                    tooltip.html(serverInfo)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px")
                        .style("opacity", 1);
                }})
                .on("mouseout", function() {{
                    tooltip.style("opacity", 0);
                }});
            
            // Ajouter les étiquettes
            const label = g.append("g")
                .selectAll("text")
                .data(graph.nodes)
                .enter().append("text")
                .attr("class", "node-label")
                .attr("text-anchor", "middle")
                .attr("dy", "0.35em")
                .text(n => n.label)
                .style("display", "none");
            
            // Fonction de mise à jour à chaque tick
            function ticked() {{
                link
                    .attr("x1", l => l.source.x)
                    .attr("y1", l => l.source.y)
                    .attr("x2", l => l.target.x)
                    .attr("y2", l => l.target.y);
                
                node
                    .attr("cx", n => n.x)
                    .attr("cy", n => n.y);
                
                label
                    .attr("x", n => n.x)
                    .attr("y", n => n.y);
                
                // Mettre à jour les contours des clusters
                drawClusterHulls();
            }}
            
            // Ajouter la fonction ticked à la simulation
            simulation.on("tick", ticked);
            
            // Gestion des contrôles
            d3.select("#reset").on("click", function() {{
                // Réinitialiser le zoom
                svg.transition().duration(750).call(
                    d3.zoom().transform,
                    d3.zoomIdentity
                );
                
                // Réinitialiser les positions fixes
                graph.nodes.forEach(node => {{
                    node.fx = null;
                    node.fy = null;
                }});
                
                // Supprimer la force de cluster si elle existe
                simulation.force("cluster", null);
                
                // Redémarrer la simulation
                simulation.alpha(1).restart();
            }});
            
            d3.select("#toggle-labels").on("click", function() {{
                showLabels = !showLabels;
                label.style("display", showLabels ? "block" : "none");
            }});
            
            d3.select("#toggle-cluster-hulls").on("click", function() {{
                showClusterHulls = !showClusterHulls;
                drawClusterHulls();
            }});
            
            d3.select("#attraction-slider").on("input", function() {{
                const value = +this.value;
                simulation.force("link").distance(100 / value);
                simulation.alpha(0.3).restart();
            }});
            
            d3.select("#repulsion-slider").on("input", function() {{
                const value = +this.value;
                simulation.force("charge").strength(-value);
                simulation.alpha(0.3).restart();
            }});
            
            d3.select("#link-slider").on("input", function() {{
                const value = +this.value;
                simulation.force("link").strength(value * 0.1);
                simulation.alpha(0.3).restart();
            }});
            
            // Regrouper les nœuds par cluster
            d3.select("#group-clusters").on("click", function() {{
                // Arrêter la simulation
                simulation.stop();
                
                // Créer un dictionnaire des positions centrales pour chaque groupe
                const groupCenters = {{}};
                const groupCounts = {{}};
                
                // Calculer les centres de masse initiaux pour chaque groupe
                graph.nodes.forEach(node => {{
                    if (!groupCenters[node.group]) {{
                        groupCenters[node.group] = {{ x: 0, y: 0 }};
                        groupCounts[node.group] = 0;
                    }}
                    groupCenters[node.group].x += node.x || width / 2;
                    groupCenters[node.group].y += node.y || height / 2;
                    groupCounts[node.group]++;
                }});
                
                // Calculer les positions moyennes pour chaque groupe
                Object.keys(groupCenters).forEach(group => {{
                    groupCenters[group].x /= groupCounts[group];
                    groupCenters[group].y /= groupCounts[group];
                }});
                
                // Disposer les groupes en cercle autour du centre
                const numGroups = Object.keys(groupCenters).length;
                const radius = Math.min(width, height) * 0.35;
                
                Object.keys(groupCenters).forEach((group, i) => {{
                    const angle = (2 * Math.PI * i) / numGroups;
                    groupCenters[group].x = width / 2 + radius * Math.cos(angle);
                    groupCenters[group].y = height / 2 + radius * Math.sin(angle);
                }});
                
                // Animation pour déplacer les nœuds vers leur centre de groupe
                graph.nodes.forEach(node => {{
                    const center = groupCenters[node.group];
                    // Ajouter un décalage aléatoire pour créer un groupe circulaire
                    const nodeRadius = 50 + Math.random() * 50; // Rayon du cercle de nœuds autour du centre du groupe
                    const angle = 2 * Math.PI * Math.random();
                    
                    // Définir la position cible avec un léger offset aléatoire
                    const targetX = center.x + nodeRadius * Math.cos(angle);
                    const targetY = center.y + nodeRadius * Math.sin(angle);
                    
                    // Animation de déplacement
                    d3.select(node.element)
                      .transition()
                      .duration(750)
                      .attr("cx", node.x = targetX)
                      .attr("cy", node.y = targetY);
                      
                    // Mettre à jour les positions fixes pour que les nœuds restent dans leur groupe
                    node.fx = targetX;
                    node.fy = targetY;
                }});
                
                // Mettre à jour les positions des liens et étiquettes
                ticked();
                
                // Redémarrer la simulation avec une faible force pour organiser les nœuds à l'intérieur de leur groupe
                simulation.alpha(0.3).restart();
                
                // Après l'animation, ajouter une force d'attraction vers le centre du groupe
                simulation.force("cluster", d3.forceRadial(function(n) {{
                    return 50; // Distance au centre de leur groupe
                }}, function(n) {{
                    return groupCenters[n.group].x;
                }}, function(n) {{
                    return groupCenters[n.group].y;
                }}).strength(0.8));
                
                // Activer les contours des clusters
                showClusterHulls = true;
                drawClusterHulls();
            }});
        </script>
    </body>
    </html>
    """
    
    # Écrire le fichier HTML
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Visualisation interactive générée et sauvegardée dans {output_file}")