# illumio/db_utils.py
"""
Fonctions utilitaires pour la gestion de la base de données.
"""
import os
import sqlite3
import json
import time
import random
import logging
from contextlib import contextmanager
from typing import Tuple, List, Dict, Any, Optional, Union, Callable

from .exceptions import DatabaseConnectionError, DatabaseQueryError, DatabaseLockError

# Configurer le logging
logger = logging.getLogger(__name__)

@contextmanager
def db_connection(db_file: str, timeout: float = 60.0, immediate: bool = False, retries: int = 5):
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
    
    Raises:
        DatabaseConnectionError: Si la connexion échoue
        DatabaseLockError: Si la base de données reste verrouillée après plusieurs tentatives
    """
    # Assurer que le répertoire existe
    try:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
    except Exception as e:
        raise DatabaseConnectionError(f"Impossible de créer le répertoire pour la base de données: {e}")
    
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
                    logger.warning(f"Base de données verrouillée, nouvelle tentative dans {wait_time:.2f}s ({attempt}/{retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    conn.rollback()
                    raise DatabaseQueryError(query="Transaction en cours", error=e) from e
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
                logger.warning(f"Base de données verrouillée lors de la connexion, nouvelle tentative dans {wait_time:.2f}s ({attempt}/{retries})...")
                time.sleep(wait_time)
            else:
                raise DatabaseConnectionError(f"Erreur de connexion à la base de données: {e}") from e
        except Exception as e:
            raise DatabaseConnectionError(f"Erreur inattendue lors de la connexion à la base de données: {e}") from e
    
    # Si on arrive ici, toutes les tentatives ont échoué
    if last_exception:
        raise DatabaseLockError(f"Base de données verrouillée après {retries} tentatives: {last_exception}")
    else:
        raise DatabaseConnectionError("Échec de la connexion à la base de données après plusieurs tentatives")

def execute_query(db_file: str, query: str, params: Optional[Tuple] = None, 
                  fetchall: bool = False, fetchone: bool = False, 
                  immediate: bool = False, retries: int = 5) -> Union[List[Dict[str, Any]], Dict[str, Any], bool]:
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
    
    Raises:
        DatabaseQueryError: Si l'exécution de la requête échoue
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
    except (DatabaseConnectionError, DatabaseLockError) as e:
        # Remonter les erreurs de connexion
        raise
    except sqlite3.Error as e:
        # Transformer les erreurs SQLite en erreurs d'application
        sanitized_query = ' '.join(query.split()[:10]) + "..." if len(query.split()) > 10 else query
        raise DatabaseQueryError(query=sanitized_query, error=e) from e

def db_retry(max_retries: int = 5, backoff_factor: float = 0.5, 
             exceptions: Tuple = (sqlite3.OperationalError,)) -> Callable:
    """
    Décorateur pour réessayer les opérations de base de données en cas d'erreur.
    
    Args:
        max_retries (int): Nombre maximal de tentatives
        backoff_factor (float): Facteur d'augmentation du temps d'attente
        exceptions (tuple): Exceptions qui déclenchent les réessais
        
    Returns:
        Callable: Décorateur configuré
    
    Example:
        @db_retry(max_retries=3, backoff_factor=1.0)
        def my_database_function(param1, param2):
            # Code qui peut lever une exception SQLite
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        # Si nous avons atteint le nombre maximal de tentatives, propager l'exception
                        raise
                    
                    # Calculer le temps d'attente avec jitter
                    wait_time = backoff_factor * (2 ** (retries - 1)) + random.uniform(0, 0.1)
                    logger.warning(f"Erreur DB: {e}. Nouvelle tentative {retries}/{max_retries} dans {wait_time:.2f}s")
                    time.sleep(wait_time)
        return wrapper
    return decorator

def json_serializable(obj: Any) -> Any:
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