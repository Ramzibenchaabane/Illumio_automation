# cli_modules/clustering_menu/common.py
#!/usr/bin/env python3
"""
Fonctions et classes utilitaires partagées pour le menu d'analyse de clustering.
"""
import os
import json
from typing import Dict, List, Any, Optional, Tuple

from illumio.utils.directory_manager import get_input_dir, get_output_dir

def prepare_servers_data(servers_ip_apps: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """
    Convertit un dictionnaire de serveurs IP et apps en format attendu pour l'analyseur.
    
    Args:
        servers_ip_apps (dict): Dictionnaire avec IP comme clé et liste d'apps comme valeur
    
    Returns:
        list: Liste de dictionnaires au format attendu par l'analyseur
    """
    return [
        {"server": server_ip, "apps": apps}
        for server_ip, apps in servers_ip_apps.items()
    ]

def save_temporary_json(data: List[Dict[str, Any]], filename: str = "temp_servers_data.json") -> str:
    """
    Sauvegarde les données au format JSON dans le répertoire d'entrée.
    
    Args:
        data (list): Données à sauvegarder
        filename (str): Nom du fichier temporaire
    
    Returns:
        str: Chemin complet du fichier sauvegardé
    """
    input_dir = get_input_dir()
    file_path = os.path.join(input_dir, filename)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    return file_path

def get_output_filename(base_name: str, timestamp: str, extension: str) -> str:
    """
    Génère un nom de fichier complet pour les résultats de sortie.
    
    Args:
        base_name (str): Nom de base du fichier
        timestamp (str): Horodatage pour rendre le nom unique
        extension (str): Extension du fichier (.json, .csv, etc.)
    
    Returns:
        str: Chemin complet du fichier de sortie
    """
    output_dir = get_output_dir()
    filename = f"{base_name}_{timestamp}{extension}"
    return os.path.join(output_dir, filename)

def format_cluster_info(clusters: Dict[str, List[str]], max_servers: int = 3) -> str:
    """
    Formate l'information de clusters pour affichage.
    
    Args:
        clusters (dict): Dictionnaire des clusters (id: liste de serveurs)
        max_servers (int): Nombre maximum de serveurs à afficher par cluster
    
    Returns:
        str: Information formatée pour affichage
    """
    output = []
    for cluster_id, servers in clusters.items():
        servers_str = ", ".join(servers[:max_servers])
        if len(servers) > max_servers:
            servers_str += f"... (+{len(servers) - max_servers} autres)"
        output.append(f"Cluster {cluster_id} ({len(servers)} serveurs): {servers_str}")
    
    return "\n".join(output)

def validate_json_format(data: Any) -> bool:
    """
    Valide que les données sont au format attendu pour l'analyse de clustering.
    
    Args:
        data (Any): Données à valider
    
    Returns:
        bool: True si le format est valide, False sinon
    """
    if not isinstance(data, list):
        return False
    
    if not data:
        return False
    
    # Vérifier la structure des premiers éléments
    for item in data[:3]:
        if not isinstance(item, dict):
            return False
        if "server" not in item or "apps" not in item:
            return False
        if not isinstance(item["apps"], list):
            return False
    
    return True

def generate_example_json() -> str:
    """
    Génère un exemple de fichier JSON pour l'analyse de clustering.
    
    Returns:
        str: Chemin du fichier exemple généré
    """
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
        }
    ]
    
    input_dir = get_input_dir()
    example_file = os.path.join(input_dir, "example_servers_data.json")
    
    with open(example_file, 'w') as f:
        json.dump(example_data, f, indent=2)
    
    return example_file