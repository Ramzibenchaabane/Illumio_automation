#illumio/parsers/ip_list_parser.py
"""
Parseur spécialisé pour les listes d'IPs Illumio.

Ce module contient des méthodes pour transformer les données brutes des listes d'IPs
provenant de l'API Illumio PCE en structures normalisées.
"""
import json
import ipaddress
from typing import Any, Dict, List, Optional, Union

from .api_response_parser import ApiResponseParser


class IPListParser:
    """Classe pour parser les listes d'IPs Illumio."""
    
    @staticmethod
    def parse_ip_list(ip_list_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse une liste d'IPs individuelle.
        
        Args:
            ip_list_data: Données brutes de la liste d'IPs
            
        Returns:
            Dictionnaire normalisé de la liste d'IPs
        """
        # Si ip_list_data est un objet ou contient des données JSON brutes
        if not isinstance(ip_list_data, dict):
            if hasattr(ip_list_data, '__dict__'):
                ip_list_data = ip_list_data.__dict__
            else:
                return {
                    'error': f"Type de liste d'IPs non supporté: {type(ip_list_data)}",
                    'raw_data': str(ip_list_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        raw_data = ip_list_data.get('raw_data')
        if isinstance(raw_data, str):
            parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
            if parsed_raw_data:
                # Fusion des données
                source_data = {**parsed_raw_data, **ip_list_data}
            else:
                source_data = ip_list_data
        else:
            source_data = ip_list_data
        
        # Extraction de l'ID de la liste d'IPs
        ip_list_id = source_data.get('id')
        if not ip_list_id and 'href' in source_data:
            ip_list_id = ApiResponseParser.extract_id_from_href(source_data['href'])
        
        # Construction de la liste d'IPs normalisée
        normalized_ip_list = {
            'id': ip_list_id,
            'href': source_data.get('href'),
            'name': source_data.get('name'),
            'description': source_data.get('description'),
            'created_at': source_data.get('created_at'),
            'updated_at': source_data.get('updated_at'),
            'ip_ranges': IPListParser._parse_ip_ranges(source_data.get('ip_ranges', [])),
            'fqdns': IPListParser._parse_fqdns(source_data.get('fqdns', []))
        }
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_ip_list:
            normalized_ip_list['raw_data'] = json.dumps(source_data) if isinstance(source_data, dict) else str(source_data)
        
        return normalized_ip_list
    
    @staticmethod
    def parse_ip_lists(ip_lists_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse une liste de listes d'IPs.
        
        Args:
            ip_lists_data: Liste des données brutes de listes d'IPs
            
        Returns:
            Liste de dictionnaires normalisés
        """
        if not ip_lists_data:
            return []
            
        normalized_ip_lists = []
        for ip_list in ip_lists_data:
            try:
                normalized_ip_list = IPListParser.parse_ip_list(ip_list)
                normalized_ip_lists.append(normalized_ip_list)
            except Exception as e:
                # Ajouter une liste d'IPs avec indication d'erreur
                normalized_ip_lists.append({
                    'error': f"Erreur de parsing: {str(e)}",
                    'raw_data': json.dumps(ip_list) if isinstance(ip_list, dict) else str(ip_list)
                })
        
        return normalized_ip_lists
    
    @staticmethod
    def _parse_ip_ranges(ip_ranges_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les plages d'IPs d'une liste d'IPs.
        
        Args:
            ip_ranges_data: Données brutes des plages d'IPs
            
        Returns:
            Liste de plages d'IPs normalisées
        """
        if not ip_ranges_data or not isinstance(ip_ranges_data, list):
            return []
        
        normalized_ranges = []
        for ip_range in ip_ranges_data:
            if not isinstance(ip_range, dict):
                continue
            
            # Extraction des IPs
            from_ip = ip_range.get('from_ip')
            to_ip = ip_range.get('to_ip', from_ip)
            
            # Déterminer s'il s'agit d'une plage ou d'une IP unique
            is_range = from_ip != to_ip and to_ip is not None
            
            # Construction de la plage normalisée
            normalized_range = {
                'from_ip': from_ip,
                'to_ip': to_ip,
                'description': ip_range.get('description'),
                'exclusion': bool(ip_range.get('exclusion')),
                'is_range': is_range
            }
            
            # Ajouter des informations supplémentaires si possible
            try:
                # Calculer le nombre d'IPs dans la plage
                if is_range and from_ip and to_ip:
                    start_ip = int(ipaddress.IPv4Address(from_ip))
                    end_ip = int(ipaddress.IPv4Address(to_ip))
                    normalized_range['ip_count'] = end_ip - start_ip + 1
                else:
                    normalized_range['ip_count'] = 1
            except Exception:
                # Ignorer si on ne peut pas calculer le nombre d'IPs
                pass
            
            normalized_ranges.append(normalized_range)
        
        return normalized_ranges
    
    @staticmethod
    def _parse_fqdns(fqdns_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les FQDNs d'une liste d'IPs.
        
        Args:
            fqdns_data: Données brutes des FQDNs
            
        Returns:
            Liste de FQDNs normalisés
        """
        if not fqdns_data or not isinstance(fqdns_data, list):
            return []
        
        normalized_fqdns = []
        for fqdn in fqdns_data:
            if not isinstance(fqdn, dict):
                continue
            
            # Construction du FQDN normalisé
            normalized_fqdn = {
                'fqdn': fqdn.get('fqdn'),
                'description': fqdn.get('description')
            }
            
            normalized_fqdns.append(normalized_fqdn)
        
        return normalized_fqdns
    
    @staticmethod
    def contains_ip(ip_list: Dict[str, Any], ip_address: str) -> bool:
        """
        Vérifie si une adresse IP est contenue dans une liste d'IPs.
        
        Args:
            ip_list: Liste d'IPs normalisée
            ip_address: Adresse IP à vérifier
            
        Returns:
            True si l'IP est dans la liste, False sinon
        """
        if not ip_list or not ip_address:
            return False
        
        # Récupérer les plages d'IPs
        ip_ranges = ip_list.get('ip_ranges', [])
        if not ip_ranges:
            return False
        
        try:
            # Convertir l'adresse IP en entier pour comparaison
            ip_int = int(ipaddress.IPv4Address(ip_address))
            
            for ip_range in ip_ranges:
                # Ignorer les exclusions
                if ip_range.get('exclusion'):
                    continue
                
                from_ip = ip_range.get('from_ip')
                to_ip = ip_range.get('to_ip', from_ip)
                
                if not from_ip:
                    continue
                
                # Convertir les IPs de la plage en entiers
                start_ip = int(ipaddress.IPv4Address(from_ip))
                
                if to_ip:
                    end_ip = int(ipaddress.IPv4Address(to_ip))
                else:
                    end_ip = start_ip
                
                # Vérifier si l'IP est dans la plage
                if start_ip <= ip_int <= end_ip:
                    return True
            
            return False
        except Exception:
            # En cas d'erreur, considérer que l'IP n'est pas dans la liste
            return False
    
    @staticmethod
    def get_ip_list_info_from_database(db, ip_list_id: str) -> Dict[str, Any]:
        """
        Récupère les informations d'une liste d'IPs depuis la base de données.
        Cette méthode facilite l'intégration avec _get_entity_details dans export_handler.py.
        
        Args:
            db: Instance de la base de données
            ip_list_id: ID de la liste d'IPs
            
        Returns:
            dict: Informations de la liste d'IPs ou dictionnaire vide si non trouvée
        """
        if not ip_list_id or not db:
            return {}
            
        try:
            # Récupérer la liste d'IPs depuis la base de données
            conn, cursor = db.connect()
            
            cursor.execute('''
            SELECT name, description, raw_data FROM ip_lists WHERE id = ?
            ''', (ip_list_id,))
            
            row = cursor.fetchone()
            
            if not row:
                db.close(conn)
                return {}
                
            # Convertir sqlite3.Row en dictionnaire
            ip_list_data = dict(row)
            ip_list_data['id'] = ip_list_id
            
            # Récupérer les plages d'IPs
            cursor.execute('''
            SELECT * FROM ip_ranges WHERE ip_list_id = ?
            ''', (ip_list_id,))
            
            ip_ranges = []
            for range_row in cursor.fetchall():
                range_data = dict(range_row)
                ip_ranges.append({
                    'from_ip': range_data['from_ip'],
                    'to_ip': range_data['to_ip'],
                    'description': range_data.get('description'),
                    'exclusion': bool(range_data.get('exclusion', 0))
                })
            
            # Récupérer les FQDNs
            cursor.execute('''
            SELECT * FROM fqdns WHERE ip_list_id = ?
            ''', (ip_list_id,))
            
            fqdns = []
            for fqdn_row in cursor.fetchall():
                fqdn_data = dict(fqdn_row)
                fqdns.append({
                    'fqdn': fqdn_data['fqdn'],
                    'description': fqdn_data.get('description')
                })
            
            db.close(conn)
            
            # Si raw_data existe et contient des données JSON valides, les utiliser
            if 'raw_data' in ip_list_data and ip_list_data['raw_data']:
                try:
                    raw_data = json.loads(ip_list_data['raw_data'])
                    # Fusionner avec les données existantes mais préserver l'ID, le nom, etc.
                    combined_data = {**raw_data, **ip_list_data}
                    
                    # Assurer que les plages d'IPs et FQDNs de la base sont utilisés
                    if ip_ranges:
                        combined_data['ip_ranges'] = ip_ranges
                    if fqdns:
                        combined_data['fqdns'] = fqdns
                    
                    return IPListParser.parse_ip_list(combined_data)
                except json.JSONDecodeError:
                    pass
            
            # Si raw_data n'est pas utilisable, construire avec les données disponibles
            ip_list_data['ip_ranges'] = ip_ranges
            ip_list_data['fqdns'] = fqdns
            
            # Normaliser les données avec le parseur
            return IPListParser.parse_ip_list(ip_list_data)
                
        except Exception as e:
            print(f"Erreur lors de la récupération de la liste d'IPs {ip_list_id}: {e}")
            if conn:
                db.close(conn)
            return {}
    
    @staticmethod
    def get_ip_list_display_name(ip_list: Optional[Union[Dict[str, Any], str]]) -> str:
        """
        Retourne un nom d'affichage pour une liste d'IPs.
        
        Args:
            ip_list: Données de la liste d'IPs ou ID
            
        Returns:
            str: Nom d'affichage de la liste d'IPs
        """
        if not ip_list:
            return "N/A"
            
        if isinstance(ip_list, dict):
            # Préférer le nom sur l'ID
            if ip_list.get('name'):
                return ip_list['name']
            elif ip_list.get('id'):
                return f"IP List {ip_list['id']}"
            else:
                return "Liste d'IPs inconnue"
        else:
            # Si c'est juste une chaîne, la retourner comme ID
            return f"IP List {ip_list}"
    
    @staticmethod
    def format_ip_list_for_display(ip_list: Optional[Union[Dict[str, Any], str]]) -> str:
        """
        Formate une liste d'IPs pour l'affichage, avec des informations détaillées si disponibles.
        
        Args:
            ip_list: Données de la liste d'IPs ou ID
            
        Returns:
            str: Représentation formatée de la liste d'IPs
        """
        if not ip_list:
            return "N/A"
            
        if isinstance(ip_list, dict):
            ip_list_name = IPListParser.get_ip_list_display_name(ip_list)
            
            # Ajouter des détails sur les plages si disponibles
            ip_ranges = ip_list.get('ip_ranges', [])
            if ip_ranges and isinstance(ip_ranges, list) and len(ip_ranges) > 0:
                # Limiter le nombre de plages à afficher pour ne pas surcharger
                max_ranges_to_show = 3
                
                range_descriptions = []
                for i, ip_range in enumerate(ip_ranges[:max_ranges_to_show]):
                    from_ip = ip_range.get('from_ip')
                    to_ip = ip_range.get('to_ip')
                    
                    if from_ip == to_ip or not to_ip:
                        range_descriptions.append(from_ip)
                    else:
                        range_descriptions.append(f"{from_ip} - {to_ip}")
                
                if len(ip_ranges) > max_ranges_to_show:
                    range_descriptions.append(f"... et {len(ip_ranges) - max_ranges_to_show} autres plages")
                
                if range_descriptions:
                    return f"{ip_list_name} ({', '.join(range_descriptions)})"
            
            return ip_list_name
        else:
            # Si c'est juste une chaîne, la retourner comme ID
            return f"IP List {ip_list}"