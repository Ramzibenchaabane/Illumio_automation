# illumio/db_utils.py
"""
Fonctions utilitaires pour la gestion de la base de données.
"""
import os
import sqlite3
import json
from contextlib import contextmanager

@contextmanager
def db_connection(db_file, timeout=30.0):
    """
    Gestionnaire de contexte pour les connexions à la base de données.
    
    Args:
        db_file (str): Chemin vers le fichier de base de données
        timeout (float): Temps d'attente maximum en secondes pour acquérir un verrou
        
    Yields:
        tuple: (connection, cursor) pour la base de données
        
    Example:
        with db_connection('data/illumio.db') as (conn, cursor):
            cursor.execute('SELECT * FROM workloads')
            results = cursor.fetchall()
    """
    # Assurer que le répertoire existe
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    # Créer la connexion avec un timeout
    conn = sqlite3.connect(db_file, timeout=timeout)
    conn.execute("PRAGMA busy_timeout = 10000")  # 10 secondes de timeout
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        yield conn, cursor
    except sqlite3.Error as e:
        conn.rollback()
        raise e
    else:
        conn.commit()
    finally:
        conn.close()

def execute_query(db_file, query, params=None, fetchall=False, fetchone=False):
    """
    Exécute une requête SQL avec gestion des erreurs.
    
    Args:
        db_file (str): Chemin vers le fichier de base de données
        query (str): Requête SQL à exécuter
        params (tuple, optional): Paramètres pour la requête
        fetchall (bool): Si True, retourne tous les résultats
        fetchone (bool): Si True, retourne un seul résultat
        
    Returns:
        list/dict/bool: Résultats de la requête ou True/False selon le succès
    """
    try:
        with db_connection(db_file) as (conn, cursor):
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetchall:
                return [dict(row) for row in cursor.fetchall()]
            elif fetchone:
                row = cursor.fetchone()
                return dict(row) if row else None
            
            return True
    except sqlite3.Error as e:
        print(f"Erreur SQL: {e}")
        return False

def json_serializable(obj):
    """
    Prépare un objet pour la sérialisation JSON en le convertissant en types de base.
    
    Args:
        obj: L'objet à sérialiser
        
    Returns:
        Objet préparé pour la sérialisation JSON
    """
    if isinstance(obj, dict):
        return {k: json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_serializable(i) for i in obj]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif hasattr(obj, '__dict__'):
        return json_serializable(obj.__dict__)
    else:
        return str(obj)