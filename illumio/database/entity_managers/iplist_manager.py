# illumio/database/entity_managers/iplist_manager.py
"""
Gestionnaire des listes d'IPs dans la base de données.
"""
import json
import sqlite3
from typing import List, Dict, Any, Optional, Union, Tuple

from ...db_utils import db_connection
from ...converters.entity_converter import EntityConverter
from ...parsers.ip_list_parser import IPListParser
from ...utils.response import ApiResponse, handle_exceptions


class IPListManager:
    """Gère les opérations de base de données pour les listes d'IPs."""
    
    def __init__(self, db_file: str):
        """
        Initialise le gestionnaire de listes d'IPs.
        
        Args:
            db_file (str): Chemin vers le fichier de base de données
        """
        self.db_file = db_file
    
    def init_tables(self) -> bool:
        """
        Initialise les tables nécessaires pour les listes d'IPs.
        
        Returns:
            bool: True si l'initialisation réussit, False sinon
        """
        try:
            with db_connection(self.db_file) as (conn, cursor):
                # Table IP Lists
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_lists (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    raw_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Table IP Ranges (liée à IP Lists)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_ranges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_list_id TEXT,
                    from_ip TEXT,
                    to_ip TEXT,
                    description TEXT,
                    exclusion INTEGER,
                    FOREIGN KEY (ip_list_id) REFERENCES ip_lists (id)
                )
                ''')
                
                # Table FQDN (liée à IP Lists)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS fqdns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_list_id TEXT,
                    fqdn TEXT,
                    description TEXT,
                    FOREIGN KEY (ip_list_id) REFERENCES ip_lists (id)
                )
                ''')
                
                # Création d'index pour améliorer les performances
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ip_ranges_ip_list_id ON ip_ranges(ip_list_id)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fqdns_ip_list_id ON fqdns(ip_list_id)
                ''')
                
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ip_ranges_ips ON ip_ranges(from_ip, to_ip)
                ''')
                
            return True
        except sqlite3.Error as e:
            print(f"Erreur lors de l'initialisation des tables des listes d'IPs: {e}")
            return False
    
    @handle_exceptions
    def store(self, ip_lists: List[Dict[str, Any]]) -> ApiResponse:
        """
        Stocke les listes d'IPs dans la base de données.
        
        Args:
            ip_lists (list): Liste des listes d'IPs à stocker
            
        Returns:
            ApiResponse: Réponse indiquant le succès ou l'échec avec détails
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Vider les tables liées pour mise à jour
            cursor.execute("DELETE FROM ip_ranges")
            cursor.execute("DELETE FROM fqdns")
            
            stored_count = 0
            
            for ip_list_data in ip_lists:
                # Parser la liste d'IPs pour la normaliser
                ip_list = IPListParser.parse_ip_list(ip_list_data)
                
                # Extraire l'ID depuis l'URL href
                ip_list_id = ip_list.get('id')
                if not ip_list_id:
                    continue
                
                # Insérer ou mettre à jour la liste d'IPs
                db_ip_list = {
                    'id': ip_list_id,
                    'name': ip_list.get('name'),
                    'description': ip_list.get('description'),
                    'raw_data': json.dumps(ip_list)
                }
                
                query, params = EntityConverter.prepare_for_insert("ip_lists", db_ip_list)
                cursor.execute(query, params)
                stored_count += 1
                
                # Insérer les plages d'IPs
                for ip_range in ip_list.get('ip_ranges', []):
                    # Convertir pour stockage en DB
                    db_ip_range = {
                        'ip_list_id': ip_list_id,
                        'from_ip': ip_range.get('from_ip'),
                        'to_ip': ip_range.get('to_ip', ip_range.get('from_ip')),
                        'description': ip_range.get('description', ''),
                        'exclusion': 1 if ip_range.get('exclusion') else 0
                    }
                    
                    query, params = EntityConverter.prepare_for_insert("ip_ranges", db_ip_range)
                    cursor.execute(query, params)
                
                # Insérer les FQDNs
                for fqdn_entry in ip_list.get('fqdns', []):
                    # Convertir pour stockage en DB
                    db_fqdn = {
                        'ip_list_id': ip_list_id,
                        'fqdn': fqdn_entry.get('fqdn'),
                        'description': fqdn_entry.get('description', '')
                    }
                    
                    query, params = EntityConverter.prepare_for_insert("fqdns", db_fqdn)
                    cursor.execute(query, params)
        
        return ApiResponse.success(
            data={"stored_count": stored_count},
            message=f"{stored_count} listes d'IPs stockées avec succès"
        )
    
    @handle_exceptions
    def get(self, ip_list_id: str) -> ApiResponse:
        """
        Récupère une liste d'IPs par son ID avec ses plages et FQDNs.
        
        Args:
            ip_list_id (str): ID de la liste d'IPs à récupérer
            
        Returns:
            ApiResponse: Réponse contenant la liste d'IPs ou une erreur
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Récupérer la liste d'IPs
            cursor.execute('''
            SELECT * FROM ip_lists WHERE id = ?
            ''', (ip_list_id,))
            
            ip_list_row = cursor.fetchone()
            if not ip_list_row:
                return ApiResponse.error(
                    message=f"Liste d'IPs avec ID {ip_list_id} non trouvée",
                    code=404
                )
            
            ip_list = dict(ip_list_row)
            
            # Extraire raw_data si présent
            if 'raw_data' in ip_list and isinstance(ip_list['raw_data'], str):
                try:
                    ip_list['parsed_data'] = json.loads(ip_list['raw_data'])
                except (json.JSONDecodeError, TypeError):
                    ip_list['parsed_data'] = None
            
            # Récupérer les plages d'IPs
            cursor.execute('''
            SELECT * FROM ip_ranges WHERE ip_list_id = ? ORDER BY id
            ''', (ip_list_id,))
            
            ip_list['ip_ranges'] = [dict(row) for row in cursor.fetchall()]
            
            # Récupérer les FQDNs
            cursor.execute('''
            SELECT * FROM fqdns WHERE ip_list_id = ? ORDER BY id
            ''', (ip_list_id,))
            
            ip_list['fqdns'] = [dict(row) for row in cursor.fetchall()]
            
            # Calculer des statistiques
            ip_count = 0
            for ip_range in ip_list['ip_ranges']:
                if ip_range.get('from_ip') == ip_range.get('to_ip'):
                    ip_count += 1  # Une seule IP
                else:
                    try:
                        # Essayer de calculer le nombre d'IPs dans la plage
                        import ipaddress
                        start_ip = int(ipaddress.IPv4Address(ip_range.get('from_ip')))
                        end_ip = int(ipaddress.IPv4Address(ip_range.get('to_ip')))
                        ip_count += max(0, end_ip - start_ip + 1)
                    except (ValueError, TypeError):
                        # En cas d'erreur, supposer une seule IP
                        ip_count += 1
            
            ip_list['statistics'] = {
                'range_count': len(ip_list['ip_ranges']),
                'fqdn_count': len(ip_list['fqdns']),
                'estimated_ip_count': ip_count
            }
            
            return ApiResponse.success(
                data={"ip_list": ip_list}
            )
    
    @handle_exceptions
    def get_all(self) -> ApiResponse:
        """
        Récupère toutes les listes d'IPs (sans les détails des plages).
        
        Returns:
            ApiResponse: Réponse contenant la liste des listes d'IPs
        """
        with db_connection(self.db_file) as (conn, cursor):
            cursor.execute('''
            SELECT * FROM ip_lists ORDER BY name
            ''')
            
            ip_lists = []
            for row in cursor.fetchall():
                ip_list = dict(row)
                
                # Compter seulement le nombre de plages et de FQDNs
                cursor.execute('''
                SELECT COUNT(*) as count FROM ip_ranges WHERE ip_list_id = ?
                ''', (ip_list['id'],))
                
                range_count = cursor.fetchone()['count']
                
                cursor.execute('''
                SELECT COUNT(*) as count FROM fqdns WHERE ip_list_id = ?
                ''', (ip_list['id'],))
                
                fqdn_count = cursor.fetchone()['count']
                
                ip_list['statistics'] = {
                    'range_count': range_count,
                    'fqdn_count': fqdn_count
                }
                
                ip_lists.append(ip_list)
            
            return ApiResponse.success(
                data={
                    "ip_lists": ip_lists,
                    "count": len(ip_lists)
                }
            )
    
    @handle_exceptions
    def find_ip_in_lists(self, ip_address: str) -> ApiResponse:
        """
        Trouve toutes les listes d'IPs qui contiennent l'adresse IP spécifiée.
        
        Args:
            ip_address (str): Adresse IP à rechercher
            
        Returns:
            ApiResponse: Réponse contenant les listes d'IPs correspondantes
        """
        try:
            # Convertir l'adresse IP en entier pour les comparaisons
            import ipaddress
            ip_int = int(ipaddress.IPv4Address(ip_address))
            
            with db_connection(self.db_file) as (conn, cursor):
                # Requête pour trouver les listes contenant cette IP
                cursor.execute('''
                SELECT ipl.* FROM ip_lists ipl
                JOIN ip_ranges ipr ON ipl.id = ipr.ip_list_id
                WHERE (
                    CAST(inet_aton(ipr.from_ip) AS UNSIGNED) <= CAST(inet_aton(?) AS UNSIGNED)
                    AND CAST(inet_aton(ipr.to_ip) AS UNSIGNED) >= CAST(inet_aton(?) AS UNSIGNED)
                )
                AND ipr.exclusion = 0
                GROUP BY ipl.id
                ORDER BY ipl.name
                ''', (ip_address, ip_address))
                
                matching_lists = []
                
                # Si la requête avancée avec inet_aton échoue, utiliser une approche plus simple
                if not cursor.rowcount:
                    cursor.execute('''
                    SELECT DISTINCT ipl.* FROM ip_lists ipl
                    JOIN ip_ranges ipr ON ipl.id = ipr.ip_list_id
                    ''')
                    
                    all_ip_lists = []
                    for row in cursor.fetchall():
                        ip_list = dict(row)
                        
                        # Récupérer toutes les plages pour ce IP list
                        cursor.execute('''
                        SELECT * FROM ip_ranges WHERE ip_list_id = ? AND exclusion = 0
                        ''', (ip_list['id'],))
                        
                        ranges = [dict(r) for r in cursor.fetchall()]
                        
                        # Vérifier manuellement si l'IP est dans l'une des plages
                        for ip_range in ranges:
                            try:
                                from_ip = ip_range.get('from_ip')
                                to_ip = ip_range.get('to_ip', from_ip)
                                
                                if from_ip and to_ip:
                                    start_ip = int(ipaddress.IPv4Address(from_ip))
                                    end_ip = int(ipaddress.IPv4Address(to_ip))
                                    
                                    if start_ip <= ip_int <= end_ip:
                                        ip_list['matching_range'] = ip_range
                                        matching_lists.append(ip_list)
                                        break
                            except (ValueError, TypeError):
                                continue
                else:
                    # La requête avancée a fonctionné
                    matching_lists = [dict(row) for row in cursor.fetchall()]
                
                return ApiResponse.success(
                    data={
                        "ip_lists": matching_lists,
                        "count": len(matching_lists),
                        "ip_address": ip_address
                    },
                    message=f"Trouvé {len(matching_lists)} listes d'IPs contenant {ip_address}"
                )
        
        except (ValueError, TypeError) as e:
            return ApiResponse.error(
                message=f"Adresse IP invalide: {ip_address}",
                code=400
            )
    
    @handle_exceptions
    def delete(self, ip_list_id: str) -> ApiResponse:
        """
        Supprime une liste d'IPs et ses plages/FQDNs associés.
        
        Args:
            ip_list_id (str): ID de la liste d'IPs à supprimer
            
        Returns:
            ApiResponse: Réponse indiquant le succès ou l'échec
        """
        with db_connection(self.db_file) as (conn, cursor):
            # Vérifier que la liste existe
            cursor.execute('''
            SELECT COUNT(*) as count FROM ip_lists WHERE id = ?
            ''', (ip_list_id,))
            
            if cursor.fetchone()['count'] == 0:
                return ApiResponse.error(
                    message=f"Liste d'IPs avec ID {ip_list_id} non trouvée",
                    code=404
                )
            
            # Supprimer d'abord les plages et FQDNs
            cursor.execute('DELETE FROM ip_ranges WHERE ip_list_id = ?', (ip_list_id,))
            ranges_deleted = cursor.rowcount
            
            cursor.execute('DELETE FROM fqdns WHERE ip_list_id = ?', (ip_list_id,))
            fqdns_deleted = cursor.rowcount
            
            # Puis supprimer la liste d'IPs
            cursor.execute('DELETE FROM ip_lists WHERE id = ?', (ip_list_id,))
            
            return ApiResponse.success(
                data={
                    "ranges_deleted": ranges_deleted,
                    "fqdns_deleted": fqdns_deleted
                },
                message=f"Liste d'IPs {ip_list_id} supprimée avec succès"
            )