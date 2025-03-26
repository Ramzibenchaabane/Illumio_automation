# illumio/traffic_analysis/result_processing.py
"""
Processes and transforms traffic analysis results.
"""
import json
from typing import List, Dict, Any, Optional

# Importation des parseurs
from ..parsers.traffic_flow_parser import TrafficFlowParser
from ..parsers.rule_parser import RuleParser

class TrafficResultProcessor:
    """
    Processes and transforms raw traffic flow results.
    """
    
    @staticmethod
    def process_raw_flows(flows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw traffic flows, extracting and transforming key information.
        
        Args:
            flows (list): List of raw traffic flow data
        
        Returns:
            List of processed traffic flows
        """
        # Utiliser le parseur de flux pour normaliser les données
        return TrafficFlowParser.parse_flows(flows)
    
    @staticmethod
    def extract_rule_information(rules: Any) -> List[Dict[str, Optional[str]]]:
        """
        Extracts rule information from various possible formats.
        
        Args:
            rules (dict or list): Rules data from traffic flow
            
        Returns:
            List of dictionaries with rule href and name for each rule
        """
        # Déléguer au parseur spécialisé qui retourne maintenant une liste complète
        return RuleParser.parse_rule_reference(rules)
    
    @staticmethod
    def extract_rule_hrefs(flows: List[Dict[str, Any]]) -> List[str]:
        """
        Extracts all unique rule hrefs from traffic flows.
        
        Args:
            flows (list): List of traffic flows
            
        Returns:
            List of unique rule hrefs
        """
        # Déléguer l'extraction au parseur de règles
        return RuleParser.extract_rule_hrefs(flows)
    
    @staticmethod
    def categorize_flows_by_decision(flows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorizes flows by their policy decision.
        
        Args:
            flows (list): List of traffic flows
            
        Returns:
            Dictionary with policy decisions as keys and flow lists as values
        """
        categorized = {}
        
        for flow in flows:
            decision = flow.get('policy_decision', 'unknown')
            if decision not in categorized:
                categorized[decision] = []
            
            categorized[decision].append(flow)
        
        return categorized
    
    @staticmethod
    def categorize_flows_by_rule(flows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorizes flows by the rule that allowed or blocked them.
        
        Args:
            flows (list): List of traffic flows
            
        Returns:
            Dictionary with rule hrefs as keys and flow lists as values
        """
        categorized = {}
        no_rule_key = "no_rule"
        
        for flow in flows:
            # Récupérer toutes les règles pour ce flux
            if 'rules' in flow and isinstance(flow['rules'], list):
                rules = flow['rules']
                if not rules:
                    # Aucune règle pour ce flux
                    if no_rule_key not in categorized:
                        categorized[no_rule_key] = []
                    categorized[no_rule_key].append(flow)
                    continue
                    
                # Pour chaque règle de ce flux, l'ajouter à la catégorie correspondante
                for rule in rules:
                    if not isinstance(rule, dict):
                        continue
                        
                    rule_href = rule.get('href')
                    if not rule_href:
                        continue
                        
                    if rule_href not in categorized:
                        categorized[rule_href] = []
                    
                    # Ajouter ce flux à cette règle
                    categorized[rule_href].append(flow)
            
            # Compatibilité legacy: vérifier aussi rule_href direct
            elif 'rule_href' in flow and flow['rule_href']:
                rule_href = flow['rule_href']
                if rule_href not in categorized:
                    categorized[rule_href] = []
                categorized[rule_href].append(flow)
            
            # Si aucune règle trouvée
            else:
                if no_rule_key not in categorized:
                    categorized[no_rule_key] = []
                categorized[no_rule_key].append(flow)
        
        return categorized
    
    @staticmethod
    def summarize_flows(flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates a summary of traffic flows.
        
        Args:
            flows (list): List of traffic flows
            
        Returns:
            Dictionary with summary information
        """
        if not flows:
            return {
                'total_flows': 0,
                'policy_decisions': {},
                'flows_with_rules': 0,
                'rules_percentage': 0,
                'unique_rules': 0
            }
        
        # Calculer les statistiques
        total_flows = len(flows)
        
        # Compter par décision de politique
        policy_counts = {}
        flows_with_rules = 0
        all_rule_hrefs = set()
        
        for flow in flows:
            # Comptabiliser par décision de politique
            decision = flow.get('policy_decision', 'unknown')
            if decision in policy_counts:
                policy_counts[decision] += 1
            else:
                policy_counts[decision] = 1
            
            # Vérifier s'il y a des règles associées
            has_rules = False
            
            # Option 1: Nouvelles règles multiples
            if 'rules' in flow and isinstance(flow['rules'], list) and flow['rules']:
                has_rules = True
                for rule in flow['rules']:
                    if isinstance(rule, dict) and rule.get('href'):
                        all_rule_hrefs.add(rule.get('href'))
            
            # Option 2: Règle unique legacy
            elif flow.get('rule_href'):
                has_rules = True
                all_rule_hrefs.add(flow.get('rule_href'))
            
            if has_rules:
                flows_with_rules += 1
        
        # Calculer le pourcentage de flux avec règles
        rules_percentage = (flows_with_rules / total_flows) * 100 if total_flows > 0 else 0
        
        return {
            'total_flows': total_flows,
            'policy_decisions': policy_counts,
            'flows_with_rules': flows_with_rules,
            'rules_percentage': rules_percentage,
            'unique_rules': len(all_rule_hrefs)
        }