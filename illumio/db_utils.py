# illumio/db_utils.py
"""
Fonctions utilitaires pour la gestion de la base de données.
"""
import os
import sqlite3
import json
import time
import random
from contextlib import contextmanager

@contextmanager
def db_connection(db_file, timeout=60.0, immediate=False, retries=5):
    """
    Gestionnaire de contexte pour les connexions à la base de données avec retry et backoff.
    
    Args:
        db_file (str): Chemin vers le fichier de base de données
        timeout (float): Temps d'attente maximum en secondes pour acquérir un verrou
        immediate (bool): Si True, utilise BEGIN IMMEDIATE pour éviter les deadlocks
        retries (int): Nombre de tentatives en cas d'erreur de verrouillage
        
    Yields:
        tuple: (connection, cursor) pour la base de données
        
    Example:
        with db_connection('data/illumio.db') as (conn, cursor):
            cursor.execute('SELECT * FROM workloads')
            results = cursor.fetchall()
    """
    # Assurer que le répertoire existe
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    
    attempt = 0
    last_exception = None
    
    while attempt < retries:
        try:
            # Créer la connexion avec un timeout
            conn = sqlite3.connect(db_file, timeout=timeout)
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 secondes de busy timeout
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Utiliser BEGIN IMMEDIATE pour acquérir les verrous d'écriture immédiatement
            # Cela évite certains types de deadlocks
            if immediate:
                conn.execute("BEGIN IMMEDIATE")
            
            try:
                yield conn, cursor
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    # Si c'est une erreur de verrouillage et qu'il nous reste des tentatives,
                    # on fait un rollback et on réessaye
                    conn.rollback()
                    conn.close()
                    last_exception = e
                    attempt += 1
                    wait_time = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)  # Backoff exponentiel avec jitter
                    print(f"Base de données verrouillée, nouvelle tentative dans {wait_time:.2f}s ({attempt}/{retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    conn.rollback()
                    raise
            except Exception as e:
                conn.rollback()
                raise
            else:
                conn.commit()
                return  # Sortie réussie de la boucle
            finally:
                conn.close()
        
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                last_exception = e
                attempt += 1
                wait_time = (2 ** attempt) * 0.1 + random.uniform(0, 0.1)
                print(f"Base de données verrouillée lors de la connexion, nouvelle tentative dans {wait_time:.2f}s ({attempt}/{retries})...")
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            raise
    
    # Si on arrive ici, toutes les tentatives ont échoué
    if last_exception:
        raise last_exception
    else:
        raise sqlite3.OperationalError("Échec de la connexion à la base de données après plusieurs tentatives")

def execute_query(db_file, query, params=None, fetchall=False, fetchone=False, immediate=False, retries=5):
    """
    Exécute une requête SQL avec gestion des erreurs et retry.
    
    Args:
        db_file (str): Chemin vers le fichier de base de données
        query (str): Requête SQL à exécuter
        params (tuple, optional): Paramètres pour la requête
        fetchall (bool): Si True, retourne tous les résultats
        fetchone (bool): Si True, retourne un seul résultat
        immediate (bool): Si True, utilise BEGIN IMMEDIATE
        retries (int): Nombre de tentatives en cas d'erreur de verrouillage
        
    Returns:
        list/dict/bool: Résultats de la requête ou True/False selon le succès
    """
    try:
        with db_connection(db_file, immediate=immediate, retries=retries) as (conn, cursor):
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