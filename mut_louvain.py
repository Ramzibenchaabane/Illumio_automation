import json
import networkx as nx
import community as community_louvain
from collections import defaultdict
import pandas as pd

def load_data(file_path):
    """Charger les données depuis le fichier JSON."""
    with open(file_path, 'r') as f:
        return json.load(f)

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

def create_d3_network_html(graph, partition, clusters, output_file="server_clusters_d3.html"):
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
                const clusters = d3.group(graph.nodes, d => d.group);
                
                // Créer un contour pour chaque cluster
                clusters.forEach((nodes, groupId) => {{
                    // Obtenir les positions des nœuds
                    const points = nodes.map(d => [d.x, d.y]);
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
                        .style("fill", d3.color(color(groupId)).copy({{opacity: 0.2}}));
                    
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
                .force("link", d3.forceLink(graph.links).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-800))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collide", d3.forceCollide().radius(d => 5 + d.app_count).iterations(2));
            
            // Créer les liens
            const link = g.append("g")
                .selectAll("line")
                .data(graph.links)
                .enter().append("line")
                .attr("stroke", "#888")
                .attr("stroke-opacity", 0.3)
                .attr("stroke-width", d => Math.sqrt(d.value) * 0.5);
            
            // Créer les nœuds
            const node = g.append("g")
                .selectAll("circle")
                .data(graph.nodes)
                .enter().append("circle")
                .attr("r", d => 3 + Math.sqrt(d.app_count) * 2)
                .attr("fill", d => color(d.group))
                .attr("stroke", "#fff")
                .attr("stroke-width", 1.5)
                .call(drag(simulation))
                .each(function(d) {{
                    // Stocker une référence à l'élément DOM dans le nœud pour l'animation
                    d.element = this;
                }})
                .on("mouseover", function(event, d) {{
                    const serverInfo = `<strong>Serveur:</strong> ${{d.id}}<br>
                                      <strong>Cluster:</strong> ${{d.group}}<br>
                                      <strong>Applications:</strong> ${{d.apps.join(", ")}}<br>
                                      <strong>Nombre d'apps:</strong> ${{d.app_count}}`;
                    
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
                .text(d => d.label)
                .style("display", "none");
            
            // Fonction de mise à jour à chaque tick
            function ticked() {{
                link
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                node
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);
                
                label
                    .attr("x", d => d.x)
                    .attr("y", d => d.y);
                
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
                simulation.force("cluster", d3.forceRadial(function(d) {{
                    return 50; // Distance au centre de leur groupe
                }}, function(d) {{
                    return groupCenters[d.group].x;
                }}, function(d) {{
                    return groupCenters[d.group].y;
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
    print("Ouvrez ce fichier dans un navigateur pour manipuler les nœuds.")

def main(file_path="servers_apps_less_mutualized.json"):
    # Charger les données
    servers_data = load_data(file_path)
    
    # Créer le graphe des serveurs
    server_graph = create_server_graph(servers_data)
    
    # Appliquer l'algorithme de Louvain
    clusters, partition = apply_louvain_clustering(server_graph)
    
    # Créer des labels pour Illumio
    labels, isolated_servers = create_labels(clusters, server_graph)
    
    # Analyser les clusters
    cluster_stats = analyze_clusters(clusters, server_graph)
    
    # Afficher les résultats
    print(f"Nombre total de serveurs: {len(server_graph.nodes())}")
    print(f"Nombre de clusters identifiés: {len(clusters)}")
    print(f"Nombre de serveurs isolés: {len(isolated_servers)}")
    print("\nStatistiques des clusters:")
    print(cluster_stats)
    
    # Sauvegarder les résultats
    results = {
        "clusters": {str(k): v for k, v in clusters.items()},
        "labels": labels,
        "isolated_servers": isolated_servers
    }
    
    with open("server_clusters_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    cluster_stats.to_csv("cluster_statistics.csv", index=False)
    
    # Créer la visualisation interactive D3.js
    create_d3_network_html(server_graph, partition, clusters)
    
    return clusters, labels, server_graph

if __name__ == "__main__":
    main()