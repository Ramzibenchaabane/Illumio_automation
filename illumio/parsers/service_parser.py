#illumio/parsers/service_parser.py
"""
Parseur spécialisé pour les services Illumio.

Ce module contient des méthodes pour transformer les données brutes des services
provenant de l'API Illumio PCE en structures normalisées.
"""
import json
from typing import Any, Dict, List, Optional, Union

from .api_response_parser import ApiResponseParser


class ServiceParser:
    """Classe pour parser les services Illumio."""
    
    @staticmethod
    def parse_service(service_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse un service individuel.
        
        Args:
            service_data: Données brutes du service
            
        Returns:
            Dictionnaire normalisé du service
        """
        # Si service_data est un objet ou contient des données JSON brutes
        if not isinstance(service_data, dict):
            if hasattr(service_data, '__dict__'):
                service_data = service_data.__dict__
            else:
                return {
                    'error': f"Type de service non supporté: {type(service_data)}",
                    'raw_data': str(service_data)
                }
        
        # Si le dictionnaire contient raw_data comme chaîne, l'extraire
        raw_data = service_data.get('raw_data')
        if isinstance(raw_data, str):
            parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
            if parsed_raw_data:
                # Fusion des données
                source_data = {**parsed_raw_data, **service_data}
            else:
                source_data = service_data
        else:
            source_data = service_data
        
        # Extraction de l'ID du service
        service_id = source_data.get('id')
        if not service_id and 'href' in source_data:
            service_id = ApiResponseParser.extract_id_from_href(source_data['href'])
        
        # Construction du service normalisé
        normalized_service = {
            'id': service_id,
            'href': source_data.get('href'),
            'name': source_data.get('name'),
            'description': source_data.get('description'),
            'created_at': source_data.get('created_at'),
            'updated_at': source_data.get('updated_at'),
            'service_ports': ServiceParser._parse_service_ports(source_data.get('service_ports', []))
        }
        
        # Conserver les données brutes pour référence
        if 'raw_data' not in normalized_service:
            normalized_service['raw_data'] = json.dumps(source_data) if isinstance(source_data, dict) else str(source_data)
        
        return normalized_service
    
    @staticmethod
    def parse_services(services_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse une liste de services.
        
        Args:
            services_data: Liste des données brutes de services
            
        Returns:
            Liste de dictionnaires normalisés
        """
        if not services_data:
            return []
            
        normalized_services = []
        for service in services_data:
            try:
                normalized_service = ServiceParser.parse_service(service)
                normalized_services.append(normalized_service)
            except Exception as e:
                # Ajouter un service avec indication d'erreur
                normalized_services.append({
                    'error': f"Erreur de parsing: {str(e)}",
                    'raw_data': json.dumps(service) if isinstance(service, dict) else str(service)
                })
        
        return normalized_services
    
    @staticmethod
    def _parse_service_ports(service_ports_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse les ports d'un service.
        
        Args:
            service_ports_data: Données brutes des ports de service
            
        Returns:
            Liste de ports de service normalisés
        """
        if not service_ports_data or not isinstance(service_ports_data, list):
            return []
        
        normalized_ports = []
        for port in service_ports_data:
            if not isinstance(port, dict):
                continue
            
            # Extraction du protocole et des ports
            proto = port.get('proto')
            from_port = port.get('port')
            to_port = port.get('to_port', from_port)
            
            # Construction du port normalisé
            normalized_port = {
                'proto': proto,
                'port': from_port,
                'to_port': to_port,
                'icmp_type': port.get('icmp_type'),
                'icmp_code': port.get('icmp_code')
            }
            
            normalized_ports.append(normalized_port)
        
        return normalized_ports
    
    @staticmethod
    def find_matching_services(proto: int, port: Optional[int] = None, services_data: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Trouve les services correspondant à un protocole et un port.
        
        Args:
            proto: Numéro de protocole
            port: Numéro de port (optionnel)
            services_data: Liste des services à rechercher (optionnel)
            
        Returns:
            Liste des services correspondants
        """
        if not services_data:
            return []
            
        matching_services = []
        for service in services_data:
            try:
                # Si le service est déjà normalisé, l'utiliser directement
                if 'service_ports' in service:
                    service_ports = service['service_ports']
                elif 'raw_data' in service:
                    # Essayer d'extraire service_ports de raw_data
                    raw_data = service['raw_data']
                    if isinstance(raw_data, str):
                        parsed_raw_data = ApiResponseParser.safe_json_loads(raw_data, {})
                        service_ports = parsed_raw_data.get('service_ports', [])
                    elif isinstance(raw_data, dict):
                        service_ports = raw_data.get('service_ports', [])
                    else:
                        service_ports = []
                else:
                    service_ports = []
                
                # Vérifier si l'un des ports du service correspond
                for service_port in service_ports:
                    if not isinstance(service_port, dict):
                        continue
                        
                    # Vérifier le protocole
                    if service_port.get('proto') != proto:
                        continue
                    
                    # Si le port est spécifié, vérifier qu'il est dans la plage
                    if port is not None:
                        from_port = service_port.get('port')
                        to_port = service_port.get('to_port', from_port)
                        
                        if from_port is None or to_port is None:
                            continue
                            
                        if not (from_port <= port <= to_port):
                            continue
                    
                    # Le service correspond
                    matching_services.append(service)
                    break  # Ne pas ajouter le même service plusieurs fois
            
            except Exception as e:
                # Ignorer ce service en cas d'erreur
                continue
        
        return matching_services
    
    @staticmethod
    def get_service_info_from_database(db, service_id: str) -> Dict[str, Any]:
        """
        Récupère les informations d'un service depuis la base de données.
        Cette méthode facilite l'intégration avec _get_entity_details dans export_handler.py.
        
        Args:
            db: Instance de la base de données
            service_id: ID du service
            
        Returns:
            dict: Informations du service ou dictionnaire vide si non trouvé
        """
        if not service_id or not db:
            return {}
            
        try:
            # Récupérer le service depuis la base de données
            conn, cursor = db.connect()
            
            cursor.execute('''
            SELECT * FROM services WHERE id = ?
            ''', (service_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return {}
                
            service_data = dict(row)
            
            # Récupérer les ports du service
            cursor.execute('''
            SELECT * FROM service_ports WHERE service_id = ?
            ''', (service_id,))
            
            service_ports = []
            for port_row in cursor.fetchall():
                port_data = dict(port_row)
                service_ports.append({
                    'proto': port_data.get('protocol'),
                    'port': port_data.get('port'),
                    'to_port': port_data.get('to_port')
                })
            
            # Ajouter les ports au service
            service_data['service_ports'] = service_ports
            
            db.close(conn)
            
            # Normaliser les données avec le parseur
            return ServiceParser.parse_service(service_data)
                
        except Exception as e:
            print(f"Erreur lors de la récupération du service {service_id}: {e}")
            return {}
    
    @staticmethod
    def get_service_display_name(service: Optional[Union[Dict[str, Any], str]]) -> str:
        """
        Retourne un nom d'affichage pour un service.
        
        Args:
            service: Données du service ou ID
            
        Returns:
            str: Nom d'affichage du service
        """
        if not service:
            return "N/A"
            
        if isinstance(service, dict):
            # Préférer le nom sur l'ID
            if service.get('name'):
                return service['name']
            elif service.get('id'):
                return f"Service {service['id']}"
            else:
                # Si on a des ports, les formater
                ports = service.get('service_ports', [])
                if ports and isinstance(ports, list) and len(ports) > 0:
                    port_info = ports[0]
                    proto = port_info.get('proto')
                    port = port_info.get('port')
                    to_port = port_info.get('to_port')
                    
                    proto_name = "TCP" if proto == 6 else "UDP" if proto == 17 else f"Proto {proto}"
                    
                    if port and to_port and port != to_port:
                        return f"{proto_name}: {port}-{to_port}"
                    elif port:
                        return f"{proto_name}: {port}"
                    else:
                        return proto_name
                
                return "Service inconnu"
        else:
            # Si c'est juste une chaîne, la retourner comme ID
            return f"Service {service}"
    
    @staticmethod
    def format_service_for_display(service: Optional[Union[Dict[str, Any], str]]) -> str:
        """
        Formate un service pour l'affichage, avec des informations détaillées si disponibles.
        
        Args:
            service: Données du service ou ID
            
        Returns:
            str: Représentation formatée du service
        """
        if not service:
            return "N/A"
            
        if isinstance(service, dict):
            service_name = ServiceParser.get_service_display_name(service)
            
            # Ajouter des détails sur les ports si disponibles
            ports = service.get('service_ports', [])
            if ports and isinstance(ports, list) and len(ports) > 0:
                port_descriptions = []
                
                for port_info in ports:
                    proto = port_info.get('proto')
                    port = port_info.get('port')
                    to_port = port_info.get('to_port')
                    
                    proto_name = "TCP" if proto == 6 else "UDP" if proto == 17 else f"Proto {proto}"
                    
                    if port and to_port and port != to_port:
                        port_descriptions.append(f"{proto_name}: {port}-{to_port}")
                    elif port:
                        port_descriptions.append(f"{proto_name}: {port}")
                    else:
                        port_descriptions.append(proto_name)
                
                if port_descriptions:
                    return f"{service_name} ({', '.join(port_descriptions)})"
            
            return service_name
        else:
            # Si c'est juste une chaîne, la retourner comme ID
            return f"Service {service}"
    
    @staticmethod
    def protocol_to_name(proto: Optional[int]) -> str:
        """
        Convertit un numéro de protocole en nom de protocole.
        
        Args:
            proto: Numéro de protocole
            
        Returns:
            str: Nom du protocole ou le numéro original comme chaîne
        """
        if proto is None:
            return "N/A"
            
        protocol_map = {
            1: "ICMP",
            6: "TCP",
            17: "UDP"
        }
        
        return protocol_map.get(proto, str(proto))