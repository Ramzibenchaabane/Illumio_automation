#illumio/models/__init__.py
"""
Package de modèles de données pour l'application Illumio Toolbox.

Ce package contient des classes de modèles typés pour représenter 
les différentes entités manipulées par l'application.
"""

from .traffic_flow import Source, Destination, Service, TrafficFlow, TrafficQuery
from .rule import Provider, Consumer, RuleService, Rule, RuleSet
from .workload import Interface, WorkloadLabel, Workload

__all__ = [
    'Source',
    'Destination',
    'Service',
    'TrafficFlow',
    'TrafficQuery',
    'Provider',
    'Consumer',
    'RuleService',
    'Rule',
    'RuleSet',
    'Interface',
    'WorkloadLabel',
    'Workload'
]