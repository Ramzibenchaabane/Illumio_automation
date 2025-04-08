# cli_modules/clustering_menu/algorithm_comparison.py
#!/usr/bin/env python3
"""
Module pour comparer différents algorithmes de clustering sur un même jeu de données.
"""
import os
import json
import time
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime

from cli_modules.menu_utils import print_header, print_menu, get_user_choice
from illumio.utils.directory_manager import get_input_dir, get_output_dir, list_files

from .cluster_analyzer import (
    load_excel_data, 
    load_json_data, 
    create_server_graph, 
    apply_louvain_clustering,
    apply_spectral_clustering, 
    # apply_infomap_clustering supprimé
    apply_hierarchical_clustering, 
    apply_min_cut_clustering,
    analyze_clusters
)

def compare_clustering_algorithms():
    """
    Compare différents algorithmes de clustering sur un même jeu de données
    et génère un rapport comparatif.
    """
    print_header()
    print("COMPARAISON DES ALGORITHMES DE CLUSTERING\n")
    
    # Sélectionner un fichier pour l'analyse
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
    print(f"\nSélectionnez un fichier de données pour la comparaison:")
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
        
        print(f"\nAnalyse comparative du fichier: {file_name}")
        
        # Option de nombre de clusters fixe pour la comparaison
        print("\nPour une comparaison équitable, voulez-vous utiliser le même nombre de clusters pour tous les algorithmes?")
        print("(Recommandé pour une comparaison directe des performances)")
        fixed_clusters_choice = input("Nombre de clusters fixe (laissez vide pour laisser chaque algorithme déterminer son optimum): ")
        
        fixed_clusters = None
        if fixed_clusters_choice.strip():
            try:
                fixed_clusters = int(fixed_clusters_choice)
                if fixed_clusters < 2:
                    print("Le nombre de clusters doit être d'au moins 2. Utilisation de 2 clusters.")
                    fixed_clusters = 2
            except ValueError:
                print("Valeur invalide. Chaque algorithme déterminera son nombre optimal de clusters.")
        
        # Générer un timestamp unique pour cette analyse
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = get_output_dir()
        
        # Préparer le nom du fichier de sortie
        comparison_file = os.path.join(output_dir, f"clustering_comparison_{timestamp}.xlsx")
        
        # Charger les données
        is_excel = file_name.endswith(('.xlsx', '.xls'))
        if is_excel:
            servers_data = load_excel_data(file_path)
            print(f"Données Excel chargées : {len(servers_data)} serveurs")
        else:
            servers_data = load_json_data(file_path)
            print(f"Données JSON chargées : {len(servers_data)} serveurs")
        
        # Créer le graphe de serveurs (une seule fois pour tous les algorithmes)
        print("Création du graphe de serveurs...")
        graph = create_server_graph(servers_data)
        
        # Liste des algorithmes à comparer
        algorithms = [
            ('louvain', "Louvain (original)", apply_louvain_clustering),
            ('spectral', "Clustering Spectral", apply_spectral_clustering),
            # ('infomap', "InfoMap", apply_infomap_clustering), supprimé
            ('hierarchical', "Clustering Hiérarchique", apply_hierarchical_clustering),
            ('min_cut', "Min-Cut", apply_min_cut_clustering)
        ]
        
        # Exécuter chaque algorithme et collecter les résultats
        results = []
        cluster_distributions = {}
        
        print("\nExécution des algorithmes de clustering:\n")
        for algo_id, algo_name, algo_func in algorithms:
            print(f"- {algo_name}...")
            start_time = time.time()
            
            # Appliquer l'algorithme
            if algo_id in ['spectral', 'hierarchical', 'min_cut'] and fixed_clusters is not None:
                clusters, partition = algo_func(graph, fixed_clusters)
            else:
                clusters, partition = algo_func(graph)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Analyser les résultats
            stats_df = analyze_clusters(clusters, graph)
            
            # Calculer des métriques supplémentaires
            num_clusters = len(clusters)
            avg_cluster_size = sum(len(servers) for servers in clusters.values()) / num_clusters
            max_cluster_size = max(len(servers) for servers in clusters.values())
            min_cluster_size = min(len(servers) for servers in clusters.values())
            
            # Calculer la granularité (ratio entre le min et max cluster size)
            granularity = min_cluster_size / max_cluster_size if max_cluster_size > 0 else 0
            
            # Calculer le nombre moyen de connexions externes par cluster
            avg_external_connections = stats_df['external_connections'].mean()
            
            # Calculer le nombre total de connexions inter-clusters (divisé par 2 car chaque connexion est comptée deux fois)
            total_cross_connections = stats_df['external_connections'].sum() / 2
            
            # Ratio de connexions inter-clusters par rapport au total
            total_edges = graph.number_of_edges()
            cross_cluster_ratio = total_cross_connections / total_edges if total_edges > 0 else 0
            
            # Stocker la distribution des tailles de clusters pour les graphiques
            cluster_sizes = [len(servers) for servers in clusters.values()]
            cluster_distributions[algo_id] = cluster_sizes
            
            # Collecter les résultats pour comparaison
            results.append({
                'Algorithme': algo_name,
                'Nombre de clusters': num_clusters,
                'Taille moyenne de cluster': avg_cluster_size,
                'Taille min de cluster': min_cluster_size,
                'Taille max de cluster': max_cluster_size,
                'Granularité (min/max)': granularity,
                'Connexions inter-clusters': total_cross_connections,
                'Ratio de connexions inter-clusters': cross_cluster_ratio,
                'Temps d\'exécution (s)': duration,
                'Score d\'isolation moyen': stats_df['isolation_score'].mean(),
                'Score de qualité moyen': stats_df['quality_score'].mean()
            })
            
            print(f"  ✓ Terminé en {duration:.2f}s - {num_clusters} clusters créés")
        
        # Créer un DataFrame pour la comparaison
        comparison_df = pd.DataFrame(results)
        
        # Créer le rapport de comparaison
        print(f"\nCréation du rapport de comparaison dans {comparison_file}...")
        
        try:
            # Utiliser Excel writer pour créer un fichier multi-feuilles
            with pd.ExcelWriter(comparison_file, engine='openpyxl') as writer:
                # Feuille principale de comparaison
                comparison_df.to_excel(writer, sheet_name='Comparaison', index=False)
                
                # Créer des graphiques de comparaison
                create_comparison_graphs(comparison_df, cluster_distributions, writer)
            
            print(f"✅ Rapport de comparaison généré : {comparison_file}")
            
            # Afficher un résumé des résultats
            print("\nRésumé de la comparaison:\n")
            print(f"{'Algorithme':<25} {'Clusters':<10} {'Conn. inter':<12} {'Ratio inter':<12} {'Temps (s)':<10}")
            print("-" * 70)
            
            # Trier les algorithmes par le ratio de connexions inter-clusters (croissant)
            sorted_results = sorted(results, key=lambda x: x['Ratio de connexions inter-clusters'])
            
            for result in sorted_results:
                algo_name = result['Algorithme']
                num_clusters = result['Nombre de clusters']
                cross_conn = result['Connexions inter-clusters']
                cross_ratio = result['Ratio de connexions inter-clusters']
                duration = result['Temps d\'exécution (s)']
                
                print(f"{algo_name:<25} {num_clusters:<10} {cross_conn:<12.0f} {cross_ratio:<12.2%} {duration:<10.2f}")
            
            print("\nRecommandation:")
            # Identifier le meilleur algorithme basé sur le ratio de connexions inter-clusters
            best_algo = sorted_results[0]['Algorithme']
            print(f"Pour minimiser les connexions entre clusters: {best_algo}")
            
            # Si la granularité est importante, on peut aussi recommander selon ce critère
            sorted_by_granularity = sorted(results, key=lambda x: (-x['Granularité (min/max)']))
            balanced_algo = sorted_by_granularity[0]['Algorithme']
            print(f"Pour des clusters de taille équilibrée: {balanced_algo}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la création du rapport: {e}")
            
            # Fallback: sauvegarder au moins le DataFrame de comparaison en CSV
            csv_file = comparison_file.replace('.xlsx', '.csv')
            comparison_df.to_csv(csv_file, index=False)
            print(f"Un fichier CSV de fallback a été créé: {csv_file}")
        
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")
        
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        input("\nAppuyez sur Entrée pour revenir au menu précédent...")

def create_comparison_graphs(comparison_df, cluster_distributions, excel_writer):
    """
    Crée des graphiques de comparaison des algorithmes et les ajoute au fichier Excel.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame contenant les résultats de comparaison
        cluster_distributions (dict): Dictionnaire des distributions de taille de clusters
        excel_writer: Writer Excel pour ajouter les graphiques
    """
    try:
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        # 1. Graphique de barres pour le nombre de clusters
        plt.figure(figsize=(10, 6))
        plt.bar(comparison_df['Algorithme'], comparison_df['Nombre de clusters'], color='skyblue')
        plt.title('Nombre de clusters par algorithme')
        plt.xlabel('Algorithme')
        plt.ylabel('Nombre de clusters')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Sauvegarder le graphique dans le fichier Excel
        imgdata = BytesIO()
        plt.savefig(imgdata, format='png')
        worksheet = excel_writer.sheets['Comparaison']
        
        # Ajouter l'image dans Excel après le tableau de comparaison
        from openpyxl.drawing.image import Image
        img = Image(imgdata)
        img.width = 600
        img.height = 400
        
        # Positionner l'image après le tableau
        row_pos = len(comparison_df) + 5
        worksheet.add_image(img, f'A{row_pos}')
        
        # 2. Graphique du ratio de connexions inter-clusters
        plt.figure(figsize=(10, 6))
        plt.bar(comparison_df['Algorithme'], comparison_df['Ratio de connexions inter-clusters'], color='lightgreen')
        plt.title('Ratio de connexions inter-clusters')
        plt.xlabel('Algorithme')
        plt.ylabel('Ratio')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Sauvegarder ce graphique aussi
        imgdata2 = BytesIO()
        plt.savefig(imgdata2, format='png')
        img2 = Image(imgdata2)
        img2.width = 600
        img2.height = 400
        worksheet.add_image(img2, f'A{row_pos + 25}')
        
        # 3. Ajouter une feuille pour les distributions de tailles de clusters
        dist_df = pd.DataFrame({})
        
        # Créer une structure de données pour le boxplot
        boxplot_data = []
        
        for algo_id, sizes in cluster_distributions.items():
            # Pour le boxplot
            for size in sizes:
                boxplot_data.append({'Algorithme': algo_id.capitalize(), 'Taille du cluster': size})
        
        # Convertir en DataFrame
        boxplot_df = pd.DataFrame(boxplot_data)
        
        # Sauvegarder le DataFrame pour le boxplot
        boxplot_df.to_excel(excel_writer, sheet_name='Distributions', index=False)
        
        # 4. Créer un boxplot des distributions de tailles
        plt.figure(figsize=(12, 8))
        # Modifié pour ne plus inclure 'infomap'
        boxplot = plt.boxplot([cluster_distributions[algo] for algo in ['louvain', 'spectral', 'hierarchical', 'min_cut']], 
                              labels=['Louvain', 'Spectral', 'Hiérarchique', 'Min-Cut'],
                              patch_artist=True)
        
        # Couleurs pour les boxplots
        colors = ['lightblue', 'lightgreen', 'lightyellow', 'lightcoral']  # Ajusté pour 4 algorithmes au lieu de 5
        for box, color in zip(boxplot['boxes'], colors):
            box.set(facecolor=color)
        
        plt.title('Distribution des tailles de clusters par algorithme')
        plt.xlabel('Algorithme')
        plt.ylabel('Nombre de serveurs par cluster')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Sauvegarder le boxplot
        imgdata3 = BytesIO()
        plt.savefig(imgdata3, format='png')
        worksheet2 = excel_writer.sheets['Distributions']
        img3 = Image(imgdata3)
        img3.width = 800
        img3.height = 500
        worksheet2.add_image(img3, 'D5')
        
    except ImportError:
        # Si matplotlib n'est pas disponible, on sauvegarde juste les données
        print("⚠️ La bibliothèque matplotlib n'est pas disponible pour créer des graphiques.")
        
        # Sauvegarder quand même les données de distribution dans une feuille séparée
        dist_data = []
        for algo_id, sizes in cluster_distributions.items():
            for i, size in enumerate(sizes):
                dist_data.append({
                    'Algorithme': algo_id,
                    'Cluster ID': i,
                    'Taille': size
                })
        
        pd.DataFrame(dist_data).to_excel(excel_writer, sheet_name='Distributions', index=False)
    
    except Exception as e:
        print(f"⚠️ Erreur lors de la création des graphiques: {e}")