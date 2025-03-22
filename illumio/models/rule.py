#illumio/models/rule.py
"""
Modèles de données pour les règles de sécurité Illumio.

Ce module définit les classes de modèles typés pour représenter
les règles de sécurité et leurs composants.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union


@dataclass
class Provider:
    """Représente un fournisseur (source) dans une règle de sécurité."""
    type: str  # 'ams', 'label', 'label_group', 'workload', 'ip_list'
    value: str
    id: Optional[str] = None
    href: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Provider':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls(type='unknown', value='unknown')
        
        if 'type' in data and 'value' in data:
            # Déjà dans notre format normalisé
            return cls(
                type=data['type'],
                value=data['value'],
                id=data.get('id'),
                href=data.get('href')
            )
        
        # Déterminer le type et la valeur
        if 'actors' in data and data['actors'] == 'ams':
            return cls(type='ams', value='All Managed Systems')
        
        elif 'label' in data and isinstance(data['label'], dict):
            label = data['label']
            key = label.get('key', '')
            value = label.get('value', '')
            href = label.get('href')
            label_id = href.split('/')[-1] if href else None
            
            return cls(
                type='label',
                value=f"{key}:{value}",
                id=label_id,
                href=href
            )
        
        elif 'label_group' in data and isinstance(data['label_group'], dict):
            lg = data['label_group']
            href = lg.get('href')
            lg_id = href.split('/')[-1] if href else None
            name = lg.get('name', f"Group {lg_id}")
            
            return cls(
                type='label_group',
                value=name,
                id=lg_id,
                href=href
            )
        
        elif 'workload' in data and isinstance(data['workload'], dict):
            wl = data['workload']
            href = wl.get('href')
            wl_id = href.split('/')[-1] if href else None
            name = wl.get('name', f"Workload {wl_id}")
            
            return cls(
                type='workload',
                value=name,
                id=wl_id,
                href=href
            )
        
        elif 'ip_list' in data and isinstance(data['ip_list'], dict):
            ip = data['ip_list']
            href = ip.get('href')
            ip_id = href.split('/')[-1] if href else None
            name = ip.get('name', f"IP List {ip_id}")
            
            return cls(
                type='ip_list',
                value=name,
                id=ip_id,
                href=href
            )
        
        return cls(type='unknown', value=str(data))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        if self.type == 'ams':
            return {'actors': 'ams'}
        
        elif self.type == 'label':
            # Extraire la clé et la valeur du format key:value
            if ':' in self.value:
                key, value = self.value.split(':', 1)
                return {'label': {'key': key, 'value': value}}
            else:
                return {'label': {'key': self.value, 'value': ''}}
        
        elif self.type == 'label_group' and self.href:
            return {'label_group': {'href': self.href}}
        
        elif self.type == 'workload' and self.href:
            return {'workload': {'href': self.href}}
        
        elif self.type == 'ip_list' and self.href:
            return {'ip_list': {'href': self.href}}
        
        # Cas par défaut pour l'API
        if self.type == 'label_group' and self.id:
            return {'label_group': {'href': f"/api/v2/orgs/1/sec_policy/active/label_groups/{self.id}"}}
        
        elif self.type == 'workload' and self.id:
            return {'workload': {'href': f"/api/v2/orgs/1/workloads/{self.id}"}}
        
        elif self.type == 'ip_list' and self.id:
            return {'ip_list': {'href': f"/api/v2/orgs/1/sec_policy/active/ip_lists/{self.id}"}}
        
        # Fallback
        return {'value': self.value, 'type': self.type}


# Consumer est fonctionnellement identique à Provider mais créé pour sémantique
@dataclass
class Consumer:
    """Représente un consommateur (destination) dans une règle de sécurité."""
    type: str  # 'ams', 'label', 'label_group', 'workload', 'ip_list'
    value: str
    id: Optional[str] = None
    href: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Consumer':
        """Crée une instance depuis un dictionnaire."""
        provider = Provider.from_dict(data)
        return cls(
            type=provider.type,
            value=provider.value,
            id=provider.id,
            href=provider.href
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        provider = Provider(
            type=self.type,
            value=self.value,
            id=self.id,
            href=self.href
        )
        return provider.to_dict()


@dataclass
class RuleService:
    """Représente un service dans une règle de sécurité."""
    type: str  # 'service' ou 'proto'
    id: Optional[str] = None
    name: Optional[str] = None
    href: Optional[str] = None
    proto: Optional[int] = None
    port: Optional[int] = None
    to_port: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleService':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls(type='unknown')
        
        if 'type' in data:
            # Déjà dans notre format normalisé
            result = cls(
                type=data['type'],
                id=data.get('id'),
                name=data.get('name'),
                href=data.get('href'),
                proto=data.get('proto'),
                port=data.get('port'),
                to_port=data.get('to_port')
            )
            return result
        
        # Nouveau parsing
        if 'href' in data:
            # Service référencé
            href = data['href']
            service_id = href.split('/')[-1] if href else None
            name = data.get('name', f"Service {service_id}")
            
            return cls(
                type='service',
                id=service_id,
                name=name,
                href=href
            )
            
        elif 'proto' in data:
            # Protocole défini directement
            proto = data['proto']
            try:
                proto = int(proto)
            except (ValueError, TypeError):
                proto = None
                
            port = data.get('port')
            try:
                port = int(port)
            except (ValueError, TypeError):
                port = None
                
            to_port = data.get('to_port')
            try:
                to_port = int(to_port)
            except (ValueError, TypeError):
                to_port = None
                
            return cls(
                type='proto',
                proto=proto,
                port=port,
                to_port=to_port
            )
            
        return cls(type='unknown')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        if self.type == 'service' and self.href:
            return {'href': self.href}
        
        elif self.type == 'service' and self.id:
            return {'href': f"/api/v2/orgs/1/sec_policy/active/services/{self.id}"}
        
        elif self.type == 'proto' and self.proto is not None:
            result = {'proto': self.proto}
            
            if self.port is not None:
                result['port'] = self.port
                
            if self.to_port is not None and self.to_port != self.port:
                result['to_port'] = self.to_port
                
            return result
            
        # Fallback
        return {'type': self.type}


@dataclass
class Rule:
    """Représente une règle de sécurité Illumio."""
    id: Optional[str] = None
    href: Optional[str] = None
    rule_set_id: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    providers: List[Provider] = field(default_factory=list)
    consumers: List[Consumer] = field(default_factory=list)
    services: List[RuleService] = field(default_factory=list)
    resolve_labels_as: Optional[str] = None
    sec_connect: bool = False
    unscoped_consumers: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Extraire l'ID si nécessaire
        rule_id = data.get('id')
        href = data.get('href')
        if not rule_id and href:
            rule_id = href.split('/')[-1]
        
        # Convertir les providers
        providers_data = data.get('providers', [])
        if isinstance(providers_data, str):
            try:
                import json
                providers_data = json.loads(providers_data)
            except json.JSONDecodeError:
                providers_data = []
                
        providers = [Provider.from_dict(p) for p in providers_data if isinstance(p, dict)]
        
        # Convertir les consumers
        consumers_data = data.get('consumers', [])
        if isinstance(consumers_data, str):
            try:
                import json
                consumers_data = json.loads(consumers_data)
            except json.JSONDecodeError:
                consumers_data = []
                
        consumers = [Consumer.from_dict(c) for c in consumers_data if isinstance(c, dict)]
        
        # Convertir les services
        services_data = data.get('ingress_services', [])
        if isinstance(services_data, str):
            try:
                import json
                services_data = json.loads(services_data)
            except json.JSONDecodeError:
                services_data = []
                
        services = [RuleService.from_dict(s) for s in services_data if isinstance(s, dict)]
        
        # Créer l'instance
        return cls(
            id=rule_id,
            href=href,
            rule_set_id=data.get('rule_set_id'),
            description=data.get('description'),
            enabled=bool(data.get('enabled', True)),
            providers=providers,
            consumers=consumers,
            services=services,
            resolve_labels_as=data.get('resolve_labels_as'),
            sec_connect=bool(data.get('sec_connect', False)),
            unscoped_consumers=bool(data.get('unscoped_consumers', False))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        result = {
            'enabled': self.enabled,
            'providers': [p.to_dict() for p in self.providers],
            'consumers': [c.to_dict() for c in self.consumers],
            'ingress_services': [s.to_dict() for s in self.services],
            'sec_connect': self.sec_connect,
            'unscoped_consumers': self.unscoped_consumers
        }
        
        if self.description:
            result['description'] = self.description
            
        if self.resolve_labels_as:
            result['resolve_labels_as'] = self.resolve_labels_as
            
        if self.id:
            result['id'] = self.id
            
        if self.href:
            result['href'] = self.href
            
        if self.rule_set_id:
            result['rule_set_id'] = self.rule_set_id
            
        return result


@dataclass
class RuleSet:
    """Représente un ensemble de règles (rule set) Illumio."""
    id: Optional[str] = None
    href: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    pversion: str = 'draft'  # 'draft' ou 'active'
    rules: List[Rule] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleSet':
        """Crée une instance depuis un dictionnaire."""
        if not data:
            return cls()
        
        # Extraire l'ID si nécessaire
        rule_set_id = data.get('id')
        href = data.get('href')
        if not rule_set_id and href:
            rule_set_id = href.split('/')[-1]
        
        # Extraire les règles
        rules_data = data.get('rules', [])
        rules = []
        
        for rule_data in rules_data:
            if isinstance(rule_data, dict):
                # Ajouter l'ID du rule set à chaque règle
                rule_data = rule_data.copy()
                rule_data['rule_set_id'] = rule_set_id
                rules.append(Rule.from_dict(rule_data))
        
        # Créer l'instance
        return cls(
            id=rule_set_id,
            href=href,
            name=data.get('name'),
            description=data.get('description'),
            enabled=bool(data.get('enabled', True)),
            pversion=data.get('pversion', 'draft'),
            rules=rules
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'instance en dictionnaire pour l'API."""
        result = {
            'name': self.name,
            'enabled': self.enabled
        }
        
        if self.description:
            result['description'] = self.description
            
        if self.id:
            result['id'] = self.id
            
        if self.href:
            result['href'] = self.href
            
        # Ajouter les règles si elles existent
        if self.rules:
            result['rules'] = [r.to_dict() for r in self.rules]
            
        return result