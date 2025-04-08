#!/usr/bin/env python3
"""
Module pour l'analyse de clustering de serveurs avec différents algorithmes.
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
import numpy as np

# Imports qui peuvent être manquants (avec gestion des ImportError dans les fonctions)
try:
    from sklearn.cluster import SpectralClustering, AgglomerativeClustering
except ImportError:
    pass  # Ces imports sont gérés dans les fonctions spécifiques

try:
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import minimum_spanning_tree
except ImportError:
    pass  # Ces imports sont gérés dans les fonctions spécifiques

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

def create_server_graph(servers_data):
    """
    Créer un graphe non-orienté où les nœuds sont les serveurs.
    Les arêtes sont pondérées par le nombre d'applications communes.
    
    Args:
        servers_data (list): Liste de dictionnaires au format {"server": str, "apps": list}
        
    Returns:
        nx.Graph: Graphe des serveurs
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
    """
    Applique l'algorithme de Louvain pour détecter les communautés.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        
    Returns:
        tuple: (clusters, partition)
    """
    # Appliquer l'algorithme de Louvain
    partition = community_louvain.best_partition(graph)
    
    # Organiser les résultats par cluster
    clusters = defaultdict(list)
    for server, cluster_id in partition.items():
        clusters[cluster_id].append(server)
    
    return clusters, partition

def apply_jaccard_based_clustering(graph, initial_threshold=0.9, threshold_step=0.1, min_threshold=0.2, min_common_apps=1):
    """
    Applique un algorithme de clustering en deux phases basé sur le coefficient de Jaccard.
    Phase 1: Regroupe les serveurs ayant exactement les mêmes applications.
    Phase 2: Fusionne progressivement les groupes similaires en diminuant le seuil de similarité.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        initial_threshold (float): Seuil initial de similarité de Jaccard (0-1)
        threshold_step (float): Pas de diminution du seuil à chaque itération
        min_threshold (float): Seuil minimal de similarité en dessous duquel on arrête les fusions
        min_common_apps (int): Nombre minimal d'applications communes pour fusionner deux groupes
        
    Returns:
        tuple: (clusters, partition)
    """
    from collections import defaultdict
    import numpy as np
    
    # Phase 1: Regroupement par identité exacte
    print("Phase 1: Regroupement des serveurs par ensemble d'applications identiques...")
    
    # Créer un dictionnaire pour regrouper les serveurs par leur signature d'applications
    signature_to_servers = defaultdict(list)
    
    # Pour chaque serveur, créer une signature (tuple trié d'applications)
    for server in graph.nodes():
        apps = graph.nodes[server]["apps"]
        # Créer une signature immuable (tuple) des applications triées
        signature = tuple(sorted(apps))
        signature_to_servers[signature].append(server)
    
    # Créer les clusters initiaux à partir des groupes par signature
    initial_clusters = {}
    for i, (signature, servers) in enumerate(signature_to_servers.items()):
        initial_clusters[i] = servers
    
    print(f"  → {len(initial_clusters)} groupes initiaux formés")
    
    # Si aucun seuil de fusion n'est demandé, retourner directement les clusters par identité
    if initial_threshold <= 0:
        # Créer le dictionnaire de partition
        partition = {}
        for cluster_id, servers in initial_clusters.items():
            for server in servers:
                partition[server] = cluster_id
        
        return initial_clusters, partition
    
    # Phase 2: Fusion progressive par similarité
    print("Phase 2: Fusion progressive des groupes par similarité...")
    
    # Fonction pour calculer le coefficient de Jaccard entre deux ensembles
    def jaccard_similarity(set1, set2):
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0
    
    # Fonction pour obtenir l'ensemble des applications d'un groupe
    def get_apps_set(cluster_id):
        app_set = set()
        for server in current_clusters[cluster_id]:
            app_set.update(graph.nodes[server]["apps"])
        return app_set
    
    # Commencer avec les clusters initiaux
    current_clusters = initial_clusters.copy()
    current_threshold = initial_threshold
    
    # Continuer les fusions tant que le seuil est supérieur au minimum
    while current_threshold >= min_threshold:
        print(f"  → Fusion avec seuil de similarité: {current_threshold:.2f}")
        
        # Calculer les ensembles d'applications pour chaque cluster actuel
        cluster_app_sets = {cid: get_apps_set(cid) for cid in current_clusters}
        
        # Préparer une liste de toutes les paires possibles de clusters
        cluster_ids = list(current_clusters.keys())
        pairs_to_merge = []
        
        # Évaluer chaque paire de clusters
        for i in range(len(cluster_ids)):
            for j in range(i+1, len(cluster_ids)):
                cid1, cid2 = cluster_ids[i], cluster_ids[j]
                
                # Calculer la similarité de Jaccard
                apps1 = cluster_app_sets[cid1]
                apps2 = cluster_app_sets[cid2]
                
                # Calculer l'intersection des applications
                common_apps = apps1.intersection(apps2)
                
                # Vérifier le nombre minimal d'applications communes
                if len(common_apps) < min_common_apps:
                    continue
                
                similarity = jaccard_similarity(apps1, apps2)
                
                # Si la similarité dépasse le seuil, ajouter à la liste des paires à fusionner
                if similarity >= current_threshold:
                    pairs_to_merge.append((cid1, cid2, similarity))
        
        # Si aucune fusion n'est possible avec ce seuil, réduire le seuil
        if not pairs_to_merge:
            current_threshold -= threshold_step
            continue
        
        # Trier les paires par similarité décroissante pour fusionner d'abord les plus similaires
        pairs_to_merge.sort(key=lambda x: x[2], reverse=True)
        
        # Effectuer les fusions
        clusters_to_remove = set()
        for cid1, cid2, _ in pairs_to_merge:
            # Vérifier que les deux clusters existent toujours (n'ont pas été fusionnés)
            if cid1 in clusters_to_remove or cid2 in clusters_to_remove:
                continue
            
            # Fusionner cid2 dans cid1
            current_clusters[cid1].extend(current_clusters[cid2])
            clusters_to_remove.add(cid2)
        
        # Supprimer les clusters qui ont été fusionnés
        for cid in clusters_to_remove:
            del current_clusters[cid]
        
        print(f"  → {len(clusters_to_remove)} fusions effectuées. Clusters restants: {len(current_clusters)}")
        
        # Réduire le seuil pour la prochaine itération
        current_threshold -= threshold_step
    
    # Réindexer les clusters pour avoir des IDs consécutifs
    final_clusters = {}
    for i, (_, servers) in enumerate(current_clusters.items()):
        final_clusters[i] = servers
    
    # Créer le dictionnaire de partition
    partition = {}
    for cluster_id, servers in final_clusters.items():
        for server in servers:
            partition[server] = cluster_id
    
    print(f"Clustering terminé. {len(final_clusters)} clusters finaux formés.")
    return final_clusters, partition


def apply_spectral_clustering(graph, n_clusters=None):
    """
    Applique l'algorithme de clustering spectral au graphe.
    Minimise les connexions entre clusters.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        n_clusters (int, optional): Nombre de clusters cible. Si None, 
                                   l'algorithme tentera de déterminer le nombre optimal.
    
    Returns:
        tuple: (clusters, partition)
    """
    try:
        from sklearn.cluster import SpectralClustering
        from collections import defaultdict
        
        # Si n_clusters n'est pas spécifié, essayer de le déterminer
        if n_clusters is None:
            # Estimer un bon nombre de clusters
            # Une approche heuristique basée sur la taille du graphe
            n_clusters = max(2, min(int(np.sqrt(len(graph.nodes)) / 2), 20))
        
        # Préparer la matrice d'adjacence
        adjacency_matrix = nx.to_numpy_array(graph)
        
        # Appliquer le clustering spectral
        spectral = SpectralClustering(n_clusters=n_clusters, 
                                    affinity='precomputed',
                                    assign_labels='discretize',
                                    random_state=42)
        
        # Utiliser la matrice d'adjacence comme matrice d'affinité
        labels = spectral.fit_predict(adjacency_matrix)
        
        # Créer le dictionnaire partition
        partition = {}
        nodes = list(graph.nodes())
        for i, node in enumerate(nodes):
            partition[node] = int(labels[i])
        
        # Organiser les résultats par cluster
        clusters = defaultdict(list)
        for server, cluster_id in partition.items():
            clusters[cluster_id].append(server)
        
        return clusters, partition
    
    except ImportError:
        print("⚠️ La bibliothèque sklearn n'est pas installée. Utilisation de l'algorithme de Louvain à la place.")
        return apply_louvain_clustering(graph)

def apply_hierarchical_clustering(graph, n_clusters=None):
    """
    Applique un clustering hiérarchique agglomératif au graphe.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        n_clusters (int, optional): Nombre de clusters souhaité. Si None,
                                   un nombre approprié sera déterminé automatiquement.
    
    Returns:
        tuple: (clusters, partition)
    """
    try:
        from sklearn.cluster import AgglomerativeClustering
        from collections import defaultdict
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import minimum_spanning_tree
        
        # Convertir le graphe en matrice de distances
        adj_matrix = nx.to_numpy_array(graph)
        
        # Transformer les poids (qui représentent la similarité) en distances
        # Plus le poids est élevé, plus les nœuds sont similaires, donc plus la distance est faible
        max_weight = np.max(adj_matrix) if np.max(adj_matrix) > 0 else 1
        distance_matrix = np.zeros_like(adj_matrix)
        
        # Pour les arêtes existantes, calculer l'inverse du poids (plus le poids est grand, plus la distance est petite)
        for i in range(adj_matrix.shape[0]):
            for j in range(adj_matrix.shape[1]):
                if adj_matrix[i, j] > 0:
                    distance_matrix[i, j] = max_weight / adj_matrix[i, j]
                else:
                    distance_matrix[i, j] = max_weight * 10  # Grande distance pour les non-connexions
        
        # Si n_clusters n'est pas spécifié, estimer un bon nombre
        if n_clusters is None:
            # Utiliser l'arbre couvrant de poids minimum pour estimer le nombre de clusters
            mst = minimum_spanning_tree(csr_matrix(distance_matrix)).toarray()
            
            # Analyser les poids des arêtes dans l'MST pour trouver des points de coupure naturels
            edges = []
            for i in range(mst.shape[0]):
                for j in range(i+1, mst.shape[1]):
                    if mst[i, j] > 0:
                        edges.append(mst[i, j])
            
            if not edges:
                # Si pas d'arêtes dans l'MST (graphe déconnecté), utiliser une heuristique simple
                n_clusters = max(2, min(int(np.sqrt(len(graph.nodes)) / 2), 20))
            else:
                # Trier les poids des arêtes
                edges.sort()
                
                # Trouver un "gap" significatif dans les poids des arêtes
                gaps = [edges[i+1] - edges[i] for i in range(len(edges)-1)]
                if gaps:
                    # Choisir le nombre de clusters en fonction du plus grand gap
                    cutoff_idx = np.argmax(gaps)
                    n_clusters = len(graph.nodes) - cutoff_idx - 1
                    n_clusters = max(2, min(n_clusters, int(np.sqrt(len(graph.nodes)) * 2)))
                else:
                    n_clusters = 2
        
        # Appliquer le clustering hiérarchique
        clustering = AgglomerativeClustering(
            n_clusters=n_clusters,
            affinity='precomputed',
            linkage='average'  # 'average', 'complete', ou 'single'
        )
        
        labels = clustering.fit_predict(distance_matrix)
        
        # Créer le dictionnaire partition
        partition = {}
        nodes = list(graph.nodes())
        for i, node in enumerate(nodes):
            partition[node] = int(labels[i])
        
        # Organiser les résultats par cluster
        clusters = defaultdict(list)
        for server, cluster_id in partition.items():
            clusters[cluster_id].append(server)
        
        return clusters, partition
        
    except ImportError:
        print("⚠️ Les bibliothèques sklearn ou scipy ne sont pas installées. Utilisation de l'algorithme de Louvain à la place.")
        return apply_louvain_clustering(graph)
    except Exception as e:
        print(f"⚠️ Erreur lors du clustering hiérarchique: {e}")
        print("Utilisation de l'algorithme de Louvain à la place.")
        return apply_louvain_clustering(graph)

def apply_min_cut_clustering(graph, n_clusters=None):
    """
    Applique un algorithme de type min-cut pour le clustering.
    Minimise explicitement le nombre de connexions entre clusters.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        n_clusters (int, optional): Nombre de clusters souhaité. Si None,
                                  un nombre approprié sera déterminé.
    
    Returns:
        tuple: (clusters, partition)
    """
    try:
        from sklearn.cluster import SpectralClustering
        from collections import defaultdict
        
        # Si n_clusters n'est pas spécifié, estimer un bon nombre
        if n_clusters is None:
            # Estimer en fonction de la taille et de la structure du graphe
            avg_degree = np.mean([d for _, d in graph.degree()])
            n_clusters = max(2, min(int(len(graph.nodes) / avg_degree), int(np.sqrt(len(graph.nodes)))))
        
        # Construire la matrice d'adjacence
        adjacency_matrix = nx.to_numpy_array(graph)
        
        # Appliquer SpectralClustering avec configuration pour minimiser les connexions entre clusters
        spectral = SpectralClustering(
            n_clusters=n_clusters,
            affinity='precomputed',
            assign_labels='discretize',
            random_state=42
        )
        
        # Utiliser la matrice d'adjacence comme entrée
        labels = spectral.fit_predict(adjacency_matrix)
        
        # Créer le dictionnaire partition
        partition = {}
        nodes = list(graph.nodes())
        for i, node in enumerate(nodes):
            partition[node] = int(labels[i])
        
        # Organiser les résultats par cluster
        clusters = defaultdict(list)
        for server, cluster_id in partition.items():
            clusters[cluster_id].append(server)
        
        return clusters, partition
        
    except ImportError:
        print("⚠️ La bibliothèque sklearn n'est pas installée. Utilisation de l'algorithme de Louvain à la place.")
        return apply_louvain_clustering(graph)
    except Exception as e:
        print(f"⚠️ Erreur lors du min-cut clustering: {e}")
        print("Utilisation de l'algorithme de Louvain à la place.")
        return apply_louvain_clustering(graph)

def choose_clustering_algorithm(graph, algorithm='louvain', n_clusters=None, **kwargs):
    """
    Choisit et applique l'algorithme de clustering spécifié.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        algorithm (str): Algorithme à utiliser ('louvain', 'spectral', 'hierarchical', 'min_cut', 'jaccard')
        n_clusters (int, optional): Nombre de clusters souhaité (pour les algorithmes qui le supportent)
        **kwargs: Arguments supplémentaires spécifiques à chaque algorithme
    
    Returns:
        tuple: (clusters, partition)
    """
    if algorithm == 'louvain':
        return apply_louvain_clustering(graph)
    elif algorithm == 'spectral':
        return apply_spectral_clustering(graph, n_clusters)
    elif algorithm == 'hierarchical':
        return apply_hierarchical_clustering(graph, n_clusters)
    elif algorithm == 'min_cut':
        return apply_min_cut_clustering(graph, n_clusters)
    elif algorithm == 'jaccard':
        # Extraire les paramètres spécifiques à l'algorithme Jaccard
        initial_threshold = kwargs.get('initial_threshold', 0.9)
        threshold_step = kwargs.get('threshold_step', 0.1)
        min_threshold = kwargs.get('min_threshold', 0.2)
        min_common_apps = kwargs.get('min_common_apps', 1)
        
        return apply_jaccard_based_clustering(
            graph, 
            initial_threshold=initial_threshold,
            threshold_step=threshold_step,
            min_threshold=min_threshold,
            min_common_apps=min_common_apps
        )
    else:
        print(f"Algorithme {algorithm} non reconnu, utilisation de Louvain par défaut.")
        return apply_louvain_clustering(graph)
    
def create_labels(clusters, graph):
    """
    Créer des labels applicatifs pour Illumio basés sur les clusters.
    
    Args:
        clusters (dict): Dictionnaire des clusters (id: liste de serveurs)
        graph (nx.Graph): Graphe des serveurs avec attributs d'applications
    
    Returns:
        tuple: (labels, isolated_servers)
    """
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
    """
    Analyser les clusters pour obtenir des statistiques détaillées.
    
    Args:
        clusters (dict): Dictionnaire des clusters (id: liste de serveurs)
        graph (nx.Graph): Graphe des serveurs
    
    Returns:
        pd.DataFrame: DataFrame des statistiques des clusters
    """
    cluster_stats = []
    
    # Analyser chaque cluster
    for cluster_id, servers in clusters.items():
        # Collecter toutes les applications dans ce cluster
        all_apps = set()
        for server in servers:
            all_apps.update(graph.nodes[server]["apps"])
        
        # Calculer la moyenne d'applications par serveur dans ce cluster
        avg_apps = sum(len(graph.nodes[server]["apps"]) for server in servers) / len(servers)
        
        # Calculer le nombre de connexions à l'intérieur du cluster (densité interne)
        internal_connections = 0
        for i, server1 in enumerate(servers):
            for server2 in servers[i+1:]:
                if graph.has_edge(server1, server2):
                    internal_connections += 1
        
        # Calculer le nombre de connexions vers l'extérieur du cluster
        external_connections = 0
        for server in servers:
            for neighbor in graph.neighbors(server):
                if neighbor not in servers:
                    external_connections += 1
        
        # Calculer un score de qualité pour le cluster (internal vs external connections)
        max_possible_internal = (len(servers) * (len(servers) - 1)) / 2
        quality_score = internal_connections / max_possible_internal if max_possible_internal > 0 else 0
        isolation_score = 1.0 if external_connections == 0 else internal_connections / (internal_connections + external_connections)
        
        cluster_stats.append({
            "cluster_id": cluster_id,
            "num_servers": len(servers),
            "num_unique_apps": len(all_apps),
            "avg_apps_per_server": avg_apps,
            "internal_connections": internal_connections,
            "external_connections": external_connections,
            "quality_score": quality_score,
            "isolation_score": isolation_score
        })
    
    # Calculer des statistiques globales sur les connexions inter-clusters
    total_edges = graph.number_of_edges()
    inter_cluster_edges = sum(stats["external_connections"] for stats in cluster_stats) / 2  # Division par 2 car chaque connexion externe est comptée deux fois
    
    for stats in cluster_stats:
        stats["cross_cluster_ratio"] = inter_cluster_edges / total_edges if total_edges > 0 else 0
    
    return pd.DataFrame(cluster_stats).sort_values("num_servers", ascending=False)

def create_d3_network_html(graph, partition, clusters, output_file, algorithm='louvain'):
    """
    Crée une visualisation D3.js où les nœuds peuvent être déplacés avec la souris.
    
    Args:
        graph (nx.Graph): Graphe des serveurs
        partition (dict): Dictionnaire de partition (serveur: cluster_id)
        clusters (dict): Dictionnaire des clusters (id: liste de serveurs)
        output_file (str): Chemin du fichier HTML de sortie
        algorithm (str): Nom de l'algorithme utilisé
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
            <h3>Clusters de serveurs avec l'algorithme de {algorithm.capitalize()}</h3>
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

def select_and_analyze_file():
    """Sélectionne un fichier et lance l'analyse de clustering."""
    print_header()
    print("SÉLECTION DE FICHIER POUR ANALYSE DE CLUSTERING\n")
    
    # Lister les fichiers disponibles
    input_dir = get_input_dir()
    excel_files = list_files('input', extension='.xlsx') + list_files('input', extension='.xls')
    json_files = list_files('input', extension='.json')
    
    all_files = excel_files + json_files
    if not all_files:
        print(f"Aucun fichier Excel ou JSON trouvé dans le dossier {input_dir}")
        print("Veuillez y placer un fichier Excel ou JSON contenant des données de serveurs.")
        print("Vous pouvez aussi générer un exemple avec l'option 'Générer un exemple'.")
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")
        return
    
    # Afficher la liste des fichiers numérotés
    print(f"\nFichiers disponibles:")
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
        
        # Options d'analyse de clustering
        print("\nOPTIONS D'ANALYSE DE CLUSTERING")
        print("-" * 50)
        
        # Choix de l'algorithme
        print("\nChoisissez l'algorithme de clustering:")
        algorithms = [
            ("louvain", "Louvain (détection de communautés basée sur la modularité)"),
            ("spectral", "Clustering Spectral (clusters de taille équilibrée)"),
            ("hierarchical", "Clustering Hiérarchique (basé sur les similitudes)"),
            ("min_cut", "Min-Cut (minimisation des connexions entre clusters)"),
            ("jaccard", "Jaccard en deux phases (maximisation du nombre de groupes cohérents)")
        ]
        
        for i, (algo_id, algo_desc) in enumerate(algorithms, 1):
            print(f"{i}. {algo_desc}")
        
        algo_choice = get_user_choice(len(algorithms))
        if algo_choice == 0:
            return
        
        algorithm = algorithms[algo_choice - 1][0]
        
        # Paramètres spécifiques au clustering Jaccard
        jaccard_params = {}
        if algorithm == 'jaccard':
            print("\nConfiguration des paramètres pour l'algorithme Jaccard:")
            
            try:
                print("\n1. Seuil initial de similarité (0-1):")
                print("   Plus le seuil est élevé, plus les groupes seront homogènes.")
                initial_threshold = float(input("   Seuil initial [0.9]: ") or "0.9")
                jaccard_params['initial_threshold'] = max(0.0, min(1.0, initial_threshold))
                
                print("\n2. Pas de diminution du seuil à chaque itération:")
                print("   Valeur plus petite = progression plus graduelle.")
                threshold_step = float(input("   Pas de diminution [0.1]: ") or "0.1")
                jaccard_params['threshold_step'] = max(0.01, min(0.5, threshold_step))
                
                print("\n3. Seuil minimal de similarité:")
                print("   En dessous de ce seuil, les fusions s'arrêtent.")
                min_threshold = float(input("   Seuil minimal [0.2]: ") or "0.2")
                jaccard_params['min_threshold'] = max(0.0, min(0.9, min_threshold))
                
                print("\n4. Nombre minimal d'applications communes:")
                print("   Nombre minimum d'applications que deux groupes doivent partager pour être fusionnés.")
                min_common_apps = int(input("   Nombre minimal [1]: ") or "1")
                jaccard_params['min_common_apps'] = max(1, min_common_apps)
                
            except ValueError:
                print("Valeur invalide. Utilisation des valeurs par défaut.")
                jaccard_params = {
                    'initial_threshold': 0.9,
                    'threshold_step': 0.1,
                    'min_threshold': 0.2,
                    'min_common_apps': 1
                }
            
            print("\nParamètres configurés pour l'algorithme Jaccard:")
            for key, value in jaccard_params.items():
                print(f"  - {key}: {value}")

        # Option de nombre de clusters
        n_clusters = None
        if algorithm in ['spectral', 'hierarchical', 'min_cut']:
            print("\nSouhaitez-vous spécifier un nombre de clusters?")
            print("1. Oui, spécifier le nombre")
            print("2. Non, laisser l'algorithme déterminer automatiquement")
            
            cluster_option = get_user_choice(2)
            if cluster_option == 0:
                return
            
            if cluster_option == 1:
                try:
                    n_clusters = int(input("\nNombre de clusters souhaité: "))
                    if n_clusters < 2:
                        print("Le nombre de clusters doit être d'au moins 2. Utilisation de 2 clusters.")
                        n_clusters = 2
                except ValueError:
                    print("Valeur invalide. L'algorithme déterminera automatiquement le nombre de clusters.")
                    n_clusters = None
        
        # Charger les données et effectuer l'analyse
        is_excel = file_name.endswith(('.xlsx', '.xls'))
        
        if is_excel:
            try:
                import pandas as pd
                
                # Charger le fichier Excel
                df = pd.read_excel(file_path)
                
                # Vérifier les colonnes nécessaires
                if "server" not in df.columns or "applications" not in df.columns:
                    print("❌ Format de fichier Excel invalide!")
                    print("Le fichier doit contenir les colonnes 'server' et 'applications'.")
                    input("\nAppuyez sur Entrée pour revenir au menu précédent...")
                    return
                
                # Préparer les données pour l'analyse
                servers_data = []
                for _, row in df.iterrows():
                    server = str(row["server"]).strip()
                    
                    # Gérer différents formats possibles pour les applications
                    apps_str = str(row["applications"])
                    if "\n" in apps_str:
                        apps = [app.strip() for app in apps_str.split("\n") if app.strip()]
                    elif "," in apps_str:
                        apps = [app.strip() for app in apps_str.split(",") if app.strip()]
                    else:
                        apps = [apps_str.strip()] if apps_str.strip() else []
                    
                    if server and apps:
                        servers_data.append({"server": server, "apps": apps})
                
                if not servers_data:
                    print("❌ Aucune donnée valide trouvée dans le fichier Excel.")
                    input("\nAppuyez sur Entrée pour revenir au menu précédent...")
                    return
                
                print(f"\n✅ Données Excel chargées avec succès: {len(servers_data)} serveurs.")
                
            except Exception as e:
                print(f"❌ Erreur lors de la lecture du fichier Excel: {e}")
                traceback.print_exc()
                input("\nAppuyez sur Entrée pour revenir au menu précédent...")
                return
        else:
            # Fichier JSON
            try:
                with open(file_path, 'r') as f:
                    servers_data = json.load(f)
                
                # Vérifier le format
                if not isinstance(servers_data, list) or not servers_data or \
                   not all(isinstance(s, dict) and "server" in s and "apps" in s for s in servers_data):
                    print("❌ Format de fichier JSON invalide!")
                    print("Le fichier doit contenir une liste d'objets avec les champs 'server' et 'apps'.")
                    input("\nAppuyez sur Entrée pour revenir au menu précédent...")
                    return
                
                print(f"\n✅ Données JSON chargées avec succès: {len(servers_data)} serveurs.")
                
            except Exception as e:
                print(f"❌ Erreur lors de la lecture du fichier JSON: {e}")
                traceback.print_exc()
                input("\nAppuyez sur Entrée pour revenir au menu précédent...")
                return
        
        # Créer un graphe à partir des données
        print(f"\nCréation du graphe de serveurs...")
        graph = create_server_graph(servers_data)
        
        print(f"- {len(graph.nodes())} nœuds (serveurs)")
        print(f"- {len(graph.edges())} arêtes (connexions)")
        
        # Appliquer l'algorithme de clustering
        print(f"\nApplication de l'algorithme de clustering {algorithm}...")
        
        if algorithm == 'jaccard':
            print(f"- Mode: Clustering basé sur le coefficient de Jaccard en deux phases")
            for key, value in jaccard_params.items():
                print(f"- {key}: {value}")
            clusters, partition = choose_clustering_algorithm(graph, algorithm, **jaccard_params)
        elif n_clusters is not None:
            print(f"- Nombre de clusters cible: {n_clusters}")
            clusters, partition = choose_clustering_algorithm(graph, algorithm, n_clusters)
        else:
            clusters, partition = choose_clustering_algorithm(graph, algorithm)
        
        # Créer des labels basés sur les clusters
        print("\nCréation des labels applicatifs...")
        labels, isolated_servers = create_labels(clusters, graph)
        
        # Analyser les clusters
        print("\nAnalyse des clusters...")
        stats_df = analyze_clusters(clusters, graph)
        
        # Générer un timestamp unique pour cette analyse
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = get_output_dir()
        
        # Préfixe des fichiers de sortie
        output_prefix = f"server_clusters_{timestamp}"
        
        # Exporter les résultats
        print("\nExportation des résultats...")
        
        # 1. Exporter les résultats en JSON
        results_file = os.path.join(output_dir, f"{output_prefix}_results.json")
        results = {
            "algorithm": algorithm,
            "n_clusters": n_clusters,
            "num_servers": len(graph.nodes()),
            "num_connections": len(graph.edges()),
            "clusters": {str(cid): servers for cid, servers in clusters.items()},
            "labels": labels,
            "isolated_servers": isolated_servers
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # 2. Exporter les statistiques en CSV
        stats_file = os.path.join(output_dir, f"{output_prefix}_statistics.csv")
        stats_df.to_csv(stats_file, index=False)
        
        # 3. Créer une visualisation interactive
        visualization_file = os.path.join(output_dir, f"{output_prefix}_visualization.html")
        create_d3_network_html(graph, partition, clusters, visualization_file, algorithm)
        
        # 4. Exporter en Excel avec statistiques et clusters
        excel_file = os.path.join(output_dir, f"{output_prefix}_report.xlsx")
        
        try:
            import pandas as pd
            
            # Créer un writer Excel
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                # Feuille des statistiques
                stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
                
                # Feuille des clusters
                cluster_data = []
                for cluster_id, servers in clusters.items():
                    for server in servers:
                        apps = graph.nodes[server]["apps"]
                        cluster_data.append({
                            "cluster_id": cluster_id,
                            "server": server,
                            "label": labels.get(server, ""),
                            "applications": ", ".join(apps),
                            "num_applications": len(apps)
                        })
                
                cluster_df = pd.DataFrame(cluster_data)
                cluster_df.to_excel(writer, sheet_name='Clusters', index=False)
                
                # Feuille de résumé
                summary_data = {
                    "Paramètre": [
                        "Algorithme",
                        "Nombre de clusters",
                        "Nombre de serveurs",
                        "Nombre de connexions",
                        "Nombre de serveurs isolés"
                    ],
                    "Valeur": [
                        algorithm,
                        len(clusters),
                        len(graph.nodes()),
                        len(graph.edges()),
                        len(isolated_servers)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Résumé', index=False)
        
        except Exception as e:
            print(f"⚠️ Erreur lors de la création du rapport Excel: {e}")
            print("Le rapport JSON et CSV a été généré correctement.")
        
        # Afficher un résumé des résultats
        print("\n" + "="*50)
        print("RÉSULTATS DE L'ANALYSE DE CLUSTERING")
        print("="*50)
        print(f"Algorithme: {algorithm}")
        print(f"Nombre de clusters: {len(clusters)}")
        print(f"Nombre de serveurs: {len(graph.nodes())}")
        print(f"Nombre de connexions: {len(graph.edges())}")
        print(f"Nombre de serveurs isolés: {len(isolated_servers)}")
        
        # Afficher les plus grands clusters
        top_clusters = stats_df.nlargest(5, 'num_servers')
        print("\nPrincipaux clusters:")
        print(f"{'ID':<5} {'Serveurs':<10} {'Apps uniques':<15} {'Isol Score':<15}")
        print("-" * 50)
        
        for _, row in top_clusters.iterrows():
            cluster_id = row['cluster_id']
            num_servers = row['num_servers']
            num_apps = row['num_unique_apps']
            isolation_score = row['isolation_score']
            print(f"{cluster_id:<5} {num_servers:<10} {num_apps:<15} {isolation_score:<15.2f}")
        
        # Résumé des fichiers générés
        print("\nFichiers générés:")
        print(f"- Résultats: {results_file}")
        print(f"- Statistiques: {stats_file}")
        print(f"- Visualisation: {visualization_file}")
        print(f"- Rapport Excel: {excel_file}")
        
        # Demander à l'utilisateur s'il souhaite ouvrir la visualisation
        print("\nSouhaitez-vous ouvrir la visualisation interactive?")
        print("1. Oui")
        print("2. Non")
        
        viz_choice = get_user_choice(2)
        if viz_choice == 1:
            try:
                import webbrowser
                print(f"\nOuverture de {visualization_file}...")
                webbrowser.open(f'file://{os.path.abspath(visualization_file)}')
            except:
                print(f"Impossible d'ouvrir automatiquement le navigateur.")
                print(f"Veuillez ouvrir manuellement le fichier: {os.path.abspath(visualization_file)}")
        
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")
    
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        traceback.print_exc()
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")

def generate_example_excel():
    """Génère un exemple de fichier Excel pour l'analyse de clustering."""
    print_header()
    print("GÉNÉRATION D'UN EXEMPLE DE FICHIER EXCEL\n")
    
    try:
        import pandas as pd
        
        # Définir des données d'exemple
        data = []
        
        # Groupe 1: Serveurs d'applications web
        web_apps = ["WebApp1", "WebAPI", "Frontend", "Redis"]
        for i in range(1, 6):
            # Chaque serveur a 2-3 applications du groupe web
            apps = np.random.choice(web_apps, size=np.random.randint(2, 4), replace=False)
            data.append({
                "server": f"web-server-{i}.example.com",
                "applications": "\n".join(apps)
            })
        
        # Groupe 2: Serveurs de base de données
        db_apps = ["MySQL", "PostgreSQL", "MongoDB", "Redis", "ElasticSearch"]
        for i in range(1, 5):
            # Chaque serveur a 1-2 applications du groupe db
            apps = np.random.choice(db_apps, size=np.random.randint(1, 3), replace=False)
            data.append({
                "server": f"db-server-{i}.example.com",
                "applications": "\n".join(apps)
            })
            
        # Groupe 3: Serveurs de traitement
        proc_apps = ["DataProcessor", "BatchJob", "ReportGenerator", "APIServer"]
        for i in range(1, 7):
            # Chaque serveur a 2-3 applications du groupe proc
            apps = np.random.choice(proc_apps, size=np.random.randint(2, 4), replace=False)
            data.append({
                "server": f"proc-server-{i}.example.com",
                "applications": "\n".join(apps)
            })
        
        # Groupe 4: Serveurs mixtes (cross-functional)
        all_apps = web_apps + db_apps + proc_apps
        for i in range(1, 4):
            # Chaque serveur a 3-4 applications mixtes
            apps = np.random.choice(all_apps, size=np.random.randint(3, 5), replace=False)
            data.append({
                "server": f"mixed-server-{i}.example.com",
                "applications": "\n".join(apps)
            })
        
        # Créer un DataFrame
        df = pd.DataFrame(data)
        
        # Enregistrer dans un fichier Excel
        input_dir = get_input_dir()
        example_file = os.path.join(input_dir, "example_server_apps.xlsx")
        
        df.to_excel(example_file, index=False)
        
        print(f"✅ Exemple de fichier Excel créé: {example_file}")
        print(f"Ce fichier contient {len(data)} serveurs répartis en 4 groupes fonctionnels")
        print("avec différentes applications. Ce jeu de données est conçu pour démontrer")
        print("comment les algorithmes de clustering peuvent identifier ces groupes.")
        
    except ImportError:
        print("❌ La bibliothèque pandas n'est pas installée.")
        print("Pour installer pandas: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erreur lors de la création du fichier exemple: {e}")
    
    input("\nAppuyez sur Entrée pour revenir au menu précédent...")


def show_expected_format():
    """Affiche le format attendu pour les fichiers d'entrée."""
    print_header()
    print("FORMAT DE FICHIER ATTENDU\n")
    
    print("L'analyse de clustering accepte deux formats de fichiers:\n")
    
    print("1. Fichier Excel (.xlsx, .xls)")
    print("   - Doit contenir deux colonnes: 'server' et 'applications'")
    print("   - Chaque ligne représente un serveur unique")
    print("   - La colonne 'applications' peut contenir plusieurs applications séparées par:")
    print("     * Sauts de ligne (préféré)")
    print("     * Virgules")
    print("   Exemple:")
    print("   +----------------------+------------------+")
    print("   | server               | applications     |")
    print("   +----------------------+------------------+")
    print("   | server1.example.com  | app1             |")
    print("   |                      | app2             |")
    print("   |                      | app3             |")
    print("   +----------------------+------------------+")
    print("   | server2.example.com  | app1,app4        |")
    print("   +----------------------+------------------+")
    
    print("\n2. Fichier JSON (.json)")
    print("   - Doit contenir une liste d'objets avec les champs 'server' et 'apps'")
    print("   - Le champ 'apps' doit être une liste de chaînes")
    print("   Exemple:")
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
    
    print("\nLe module de clustering utilise ces données pour:")
    print("1. Créer un graphe où les serveurs sont des nœuds")
    print("2. Établir des connexions entre serveurs partageant des applications")
    print("3. Regrouper les serveurs en clusters selon l'algorithme choisi")
    print("4. Générer des labels basés sur les applications communes dans chaque cluster")
    
    input("\nAppuyez sur Entrée pour revenir au menu précédent...")


def load_excel_data(file_path):
    """
    Charge les données depuis un fichier Excel.
    
    Args:
        file_path (str): Chemin du fichier Excel
        
    Returns:
        list: Liste de dictionnaires au format {"server": str, "apps": list}
    """
    try:
        import pandas as pd
        
        # Charger le fichier Excel
        df = pd.read_excel(file_path)
        
        # Vérifier les colonnes nécessaires
        if "server" not in df.columns or "applications" not in df.columns:
            print("❌ Format de fichier Excel invalide!")
            print("Le fichier doit contenir les colonnes 'server' et 'applications'.")
            return []
        
        # Préparer les données pour l'analyse
        servers_data = []
        for _, row in df.iterrows():
            server = str(row["server"]).strip()
            
            # Gérer différents formats possibles pour les applications
            apps_str = str(row["applications"])
            if "\n" in apps_str:
                apps = [app.strip() for app in apps_str.split("\n") if app.strip()]
            elif "," in apps_str:
                apps = [app.strip() for app in apps_str.split(",") if app.strip()]
            else:
                apps = [apps_str.strip()] if apps_str.strip() else []
            
            if server and apps:
                servers_data.append({"server": server, "apps": apps})
        
        return servers_data
    
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier Excel: {e}")
        traceback.print_exc()
        return []


def load_json_data(file_path):
    """
    Charge les données depuis un fichier JSON.
    
    Args:
        file_path (str): Chemin du fichier JSON
        
    Returns:
        list: Liste de dictionnaires au format {"server": str, "apps": list}
    """
    try:
        with open(file_path, 'r') as f:
            servers_data = json.load(f)
        
        # Vérifier le format
        if not isinstance(servers_data, list) or not servers_data or \
           not all(isinstance(s, dict) and "server" in s and "apps" in s for s in servers_data):
            print("❌ Format de fichier JSON invalide!")
            print("Le fichier doit contenir une liste d'objets avec les champs 'server' et 'apps'.")
            return []
        
        return servers_data
    
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du fichier JSON: {e}")
        traceback.print_exc()
        return []