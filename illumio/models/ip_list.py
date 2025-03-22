# illumio/models/ip_list.py
"""
Modèles de données pour les listes d'IPs Illumio.

Ce module définit les classes de modèles typés pour représenter
les listes d'IPs, plages d'IPs et FQDNs.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
import ipaddress


@dataclass
class IPRange:
    """Représente une plage d'adresses IP dans une liste d'IPs."""
    from_ip: str
    to_ip: Optional[str] = None
    description: Optional[str] = None
    exclusion: bool = False
    
    def __post_init__(self):
        """Validation après initialisation."""
        # Si to_ip n'est pas défini, utiliser from_ip (IP unique)
        if not self.to_ip:
            self.to_ip = self.from_ip
        
        # Valider que les adresses IP sont correctes
        try:
            ipaddress.ip_address(self.from_ip)
            ipaddress.ip_address(self.to_ip)
        except ValueError as e:
            raise ValueError(f"Adresse IP invalide: {e}")
        
        # Vérifier que from_ip <= to_ip
        if int(ipaddress.ip_address(self.from_ip)) > int(ipaddress.ip_address(self.to_ip)):
            raise ValueError(f"La plage est inversée: {self.from_ip} > {self.to_ip}")
    
    @property
    def is_single_ip(self) -> bool:
        """Indique si cette plage représente une seule adresse IP."""
        return self.from_ip == self.to_ip
    
    @property
    def ip_count(self) -> int:
        """Calcule le nombre d'adresses IP dans la plage."""
        try:
            start_ip = int(ipaddress.ip_address(self.from_ip))
            end_ip = int(ipaddress.ip_address(self.to_ip))
            return end_ip - start_ip + 1
        except (ValueError, TypeError):
            return 1  # En cas d'erreur, considérer qu'il y a une seule IP
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPRange':
        """
        Crée une instance d'IPRange à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la plage d'IPs
            
        Returns:
            Instance d'IPRange
        
        Raises:
            ValueError: Si des données obligatoires sont manquantes ou invalides
        """
        if not data:
            raise ValueError("Données de plage d'IPs manquantes")
        
        from_ip = data.get('from_ip')
        if not from_ip:
            raise ValueError("Adresse IP de début manquante")
        
        return cls(
            from_ip=from_ip,
            to_ip=data.get('to_ip', from_ip),
            description=data.get('description'),
            exclusion=bool(data.get('exclusion', False))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant la plage d'IPs
        """
        result = {
            'from_ip': self.from_ip,
            'to_ip': self.to_ip
        }
        
        if self.description:
            result['description'] = self.description
        
        if self.exclusion:
            result['exclusion'] = True
        
        return result
    
    def contains_ip(self, ip: str) -> bool:
        """
        Vérifie si l'adresse IP est contenue dans cette plage.
        
        Args:
            ip: Adresse IP à vérifier
            
        Returns:
            True si l'IP est dans la plage, False sinon
        """
        try:
            ip_int = int(ipaddress.ip_address(ip))
            start_ip = int(ipaddress.ip_address(self.from_ip))
            end_ip = int(ipaddress.ip_address(self.to_ip))
            
            return start_ip <= ip_int <= end_ip
        except ValueError:
            return False


@dataclass
class FQDN:
    """Représente un Fully Qualified Domain Name (FQDN) dans une liste d'IPs."""
    fqdn: str
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FQDN':
        """
        Crée une instance de FQDN à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du FQDN
            
        Returns:
            Instance de FQDN
        
        Raises:
            ValueError: Si des données obligatoires sont manquantes
        """
        if not data:
            raise ValueError("Données de FQDN manquantes")
        
        fqdn = data.get('fqdn')
        if not fqdn:
            raise ValueError("FQDN manquant")
        
        return cls(
            fqdn=fqdn,
            description=data.get('description')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant le FQDN
        """
        result = {
            'fqdn': self.fqdn
        }
        
        if self.description:
            result['description'] = self.description
        
        return result


@dataclass
class IPList:
    """Représente une liste d'IPs Illumio avec ses plages et FQDNs."""
    name: str
    id: Optional[str] = None
    href: Optional[str] = None
    description: Optional[str] = None
    ip_ranges: List[IPRange] = field(default_factory=list)
    fqdns: List[FQDN] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPList':
        """
        Crée une instance d'IPList à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données de la liste d'IPs
            
        Returns:
            Instance d'IPList
        
        Raises:
            ValueError: Si des données obligatoires sont manquantes
        """
        if not data:
            raise ValueError("Données de liste d'IPs manquantes")
        
        # Extraire l'ID à partir du href si nécessaire
        ip_list_id = data.get('id')
        href = data.get('href')
        if not ip_list_id and href:
            ip_list_id = href.split('/')[-1]
        
        # Vérifier le nom
        name = data.get('name')
        if not name:
            raise ValueError("Nom de liste d'IPs manquant")
        
        # Extraire les plages d'IPs
        ip_ranges = []
        for range_data in data.get('ip_ranges', []):
            if isinstance(range_data, dict):
                try:
                    ip_ranges.append(IPRange.from_dict(range_data))
                except ValueError:
                    # Ignorer les plages invalides
                    pass
        
        # Extraire les FQDNs
        fqdns = []
        for fqdn_data in data.get('fqdns', []):
            if isinstance(fqdn_data, dict):
                try:
                    fqdns.append(FQDN.from_dict(fqdn_data))
                except ValueError:
                    # Ignorer les FQDNs invalides
                    pass
        
        return cls(
            name=name,
            id=ip_list_id,
            href=href,
            description=data.get('description'),
            ip_ranges=ip_ranges,
            fqdns=fqdns,
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            Dictionnaire représentant la liste d'IPs
        """
        result = {
            'name': self.name
        }
        
        # Ajouter les champs optionnels s'ils existent
        if self.id:
            result['id'] = self.id
        
        if self.href:
            result['href'] = self.href
        
        if self.description:
            result['description'] = self.description
        
        if self.created_at:
            result['created_at'] = self.created_at
        
        if self.updated_at:
            result['updated_at'] = self.updated_at
        
        # Convertir les plages d'IPs et FQDNs
        if self.ip_ranges:
            result['ip_ranges'] = [ip_range.to_dict() for ip_range in self.ip_ranges]
        
        if self.fqdns:
            result['fqdns'] = [fqdn.to_dict() for fqdn in self.fqdns]
        
        return result
    
    def add_ip(self, ip: str, description: Optional[str] = None, exclusion: bool = False) -> None:
        """
        Ajoute une adresse IP à la liste.
        
        Args:
            ip: Adresse IP à ajouter
            description: Description optionnelle
            exclusion: Si True, cette IP est une exclusion
        
        Raises:
            ValueError: Si l'adresse IP est invalide
        """
        try:
            ipaddress.ip_address(ip)
            self.ip_ranges.append(IPRange(
                from_ip=ip,
                to_ip=ip,
                description=description,
                exclusion=exclusion
            ))
        except ValueError as e:
            raise ValueError(f"Adresse IP invalide: {e}")
    
    def add_ip_range(self, 
                   from_ip: str, 
                   to_ip: str, 
                   description: Optional[str] = None, 
                   exclusion: bool = False) -> None:
        """
        Ajoute une plage d'IPs à la liste.
        
        Args:
            from_ip: Adresse IP de début
            to_ip: Adresse IP de fin
            description: Description optionnelle
            exclusion: Si True, cette plage est une exclusion
        
        Raises:
            ValueError: Si les adresses IP sont invalides
        """
        self.ip_ranges.append(IPRange(
            from_ip=from_ip,
            to_ip=to_ip,
            description=description,
            exclusion=exclusion
        ))
    
    def add_fqdn(self, fqdn: str, description: Optional[str] = None) -> None:
        """
        Ajoute un FQDN à la liste.
        
        Args:
            fqdn: FQDN à ajouter
            description: Description optionnelle
        
        Raises:
            ValueError: Si le FQDN est invalide
        """
        if not fqdn:
            raise ValueError("FQDN manquant")
        
        self.fqdns.append(FQDN(
            fqdn=fqdn,
            description=description
        ))
    
    def contains_ip(self, ip: str) -> bool:
        """
        Vérifie si l'adresse IP est contenue dans cette liste.
        
        Args:
            ip: Adresse IP à vérifier
            
        Returns:
            True si l'IP est dans la liste, False sinon
        """
        try:
            # Vérifier d'abord les exclusions
            for ip_range in self.ip_ranges:
                if ip_range.exclusion and ip_range.contains_ip(ip):
                    return False
            
            # Ensuite vérifier les inclusions
            for ip_range in self.ip_ranges:
                if not ip_range.exclusion and ip_range.contains_ip(ip):
                    return True
            
            return False
        except Exception:
            return False
    
    @property
    def ip_count(self) -> int:
        """
        Calcule le nombre total d'adresses IP dans la liste (excluant les exclusions).
        
        Returns:
            Nombre d'adresses IP
        """
        total = 0
        for ip_range in self.ip_ranges:
            if not ip_range.exclusion:
                total += ip_range.ip_count
        return total