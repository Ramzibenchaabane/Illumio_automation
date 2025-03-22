#illumio/models/traffic_flow.py
"""
Modèles de données pour les flux de trafic et requêtes Illumio.

Ce module définit les classes de modèles typés pour représenter
les flux de trafic et les requêtes d'analyse.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


@dataclass
class Source:
    """Représente une source dans un flux de trafic."""
    ip: Optional[str] = None
    workload_id: Optional[str] = None
    workload_href: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Source':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Extraire workload_id si disponible
        workload_id = None
        workload_href = None
        
        if 'workload' in data and isinstance(data['workload'], dict):
            workload = data['workload']
            if 'href' in workload:
                workload_href = workload['href']
                # Extraire l'ID de l'URL
                workload_id = workload_href.split('/')[-1] if workload_href else None
        
        return cls(
            ip=data.get('ip'),
            workload_id=workload_id,
            workload_href=workload_href
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire."""
        result = {}
        
        if self.ip:
            result['ip'] = self.ip
        
        if self.workload_id or self.workload_href:
            workload = {}
            if self.workload_href:
                workload['href'] = self.workload_href
            
            result['workload'] = workload
        
        return result


@dataclass
class Destination:
    """Représente une destination dans un flux de trafic."""
    ip: Optional[str] = None
    workload_id: Optional[str] = None
    workload_href: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Destination':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Extraire workload_id si disponible
        workload_id = None
        workload_href = None
        
        if 'workload' in data and isinstance(data['workload'], dict):
            workload = data['workload']
            if 'href' in workload:
                workload_href = workload['href']
                # Extraire l'ID de l'URL
                workload_id = workload_href.split('/')[-1] if workload_href else None
        
        return cls(
            ip=data.get('ip'),
            workload_id=workload_id,
            workload_href=workload_href
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire."""
        result = {}
        
        if self.ip:
            result['ip'] = self.ip
        
        if self.workload_id or self.workload_href:
            workload = {}
            if self.workload_href:
                workload['href'] = self.workload_href
            
            result['workload'] = workload
        
        return result


@dataclass
class Service:
    """Représente un service dans un flux de trafic."""
    name: Optional[str] = None
    port: Optional[int] = None
    proto: Optional[int] = None  # Numéro de protocole IP
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Service':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        port = data.get('port')
        if port is not None:
            try:
                port = int(port)
            except (ValueError, TypeError):
                port = None
        
        proto = data.get('proto')
        if proto is not None:
            try:
                proto = int(proto)
            except (ValueError, TypeError):
                proto = None
        
        return cls(
            name=data.get('name'),
            port=port,
            proto=proto
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire."""
        result = {}
        
        if self.name:
            result['name'] = self.name
        
        if self.port is not None:
            result['port'] = self.port
        
        if self.proto is not None:
            result['proto'] = self.proto
        
        return result


@dataclass
class TrafficFlow:
    """Représente un flux de trafic Illumio."""
    src: Source = field(default_factory=Source)
    dst: Destination = field(default_factory=Destination)
    service: Service = field(default_factory=Service)
    policy_decision: Optional[str] = None
    flow_direction: Optional[str] = None
    num_connections: Optional[int] = None
    first_detected: Optional[str] = None
    last_detected: Optional[str] = None
    rule_href: Optional[str] = None
    rule_name: Optional[str] = None
    query_id: Optional[str] = None
    id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrafficFlow':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Convertir num_connections en entier si possible
        num_connections = data.get('num_connections')
        if num_connections is not None:
            try:
                num_connections = int(num_connections)
            except (ValueError, TypeError):
                num_connections = None
        
        # Créer les objets imbriqués
        src = Source.from_dict(data.get('src', {}))
        dst = Destination.from_dict(data.get('dst', {}))
        service = Service.from_dict(data.get('service', {}))
        
        # Créer l'instance
        return cls(
            src=src,
            dst=dst,
            service=service,
            policy_decision=data.get('policy_decision'),
            flow_direction=data.get('flow_direction'),
            num_connections=num_connections,
            first_detected=data.get('first_detected'),
            last_detected=data.get('last_detected'),
            rule_href=data.get('rule_href'),
            rule_name=data.get('rule_name'),
            query_id=data.get('query_id'),
            id=data.get('id')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire."""
        result = {
            'src': self.src.to_dict(),
            'dst': self.dst.to_dict(),
            'service': self.service.to_dict(),
            'policy_decision': self.policy_decision,
            'flow_direction': self.flow_direction,
            'num_connections': self.num_connections
        }
        
        # Ajouter les champs optionnels
        if self.first_detected:
            result['first_detected'] = self.first_detected
        
        if self.last_detected:
            result['last_detected'] = self.last_detected
        
        if self.rule_href:
            result['rule_href'] = self.rule_href
        
        if self.rule_name:
            result['rule_name'] = self.rule_name
        
        if self.query_id:
            result['query_id'] = self.query_id
        
        if self.id is not None:
            result['id'] = self.id
        
        return result


@dataclass
class TrafficQuery:
    """Représente une requête d'analyse de trafic Illumio."""
    id: Optional[str] = None
    query_name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    rules_status: Optional[str] = None
    rules_completed_at: Optional[str] = None
    sources: Optional[Dict[str, Any]] = None
    destinations: Optional[Dict[str, Any]] = None
    services: Optional[Dict[str, Any]] = None
    policy_decisions: Optional[List[str]] = None
    max_results: int = 10000
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrafficQuery':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Convertir max_results en entier si possible
        max_results = data.get('max_results', 10000)
        try:
            max_results = int(max_results)
        except (ValueError, TypeError):
            max_results = 10000
        
        return cls(
            id=data.get('id'),
            query_name=data.get('query_name'),
            status=data.get('status'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            created_at=data.get('created_at'),
            completed_at=data.get('completed_at'),
            rules_status=data.get('rules_status'),
            rules_completed_at=data.get('rules_completed_at'),
            sources=data.get('sources'),
            destinations=data.get('destinations'),
            services=data.get('services'),
            policy_decisions=data.get('policy_decisions'),
            max_results=max_results
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire."""
        result = {
            'query_name': self.query_name,
            'max_results': self.max_results
        }
        
        # Ajouter les champs optionnels
        if self.id:
            result['id'] = self.id
        
        if self.status:
            result['status'] = self.status
        
        if self.start_date:
            result['start_date'] = self.start_date
        
        if self.end_date:
            result['end_date'] = self.end_date
        
        if self.sources:
            result['sources'] = self.sources
        
        if self.destinations:
            result['destinations'] = self.destinations
        
        if self.services:
            result['services'] = self.services
        
        if self.policy_decisions:
            result['policy_decisions'] = self.policy_decisions
        
        return result