# illumio/traffic_analysis/result_processing.py
"""
Processes and transforms traffic analysis results.
"""
import json
from typing import List, Dict, Any, Optional

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
        processed_flows = []
        
        for flow in flows:
            try:
                # Check if flow is stored as JSON string
                if isinstance(flow.get('raw_data'), str):
                    try:
                        raw_data = json.loads(flow.get('raw_data', '{}'))
                    except json.JSONDecodeError:
                        # If JSON decoding fails, use the original flow
                        processed_flows.append(flow)
                        continue
                else:
                    # If not a JSON string, use the flow as-is
                    raw_data = flow
                
                # Extract source and destination information
                src = raw_data.get('src', {})
                dst = raw_data.get('dst', {})
                service = raw_data.get('service', {})
                rules = raw_data.get('rules', {})
                
                # Process rule information
                rule_info = TrafficResultProcessor._extract_rule_information(rules)
                
                # Create processed flow entry
                processed_flow = {
                    'src_ip': src.get('ip'),
                    'src_workload_id': TrafficResultProcessor._extract_workload_id(src),
                    'dst_ip': dst.get('ip'),
                    'dst_workload_id': TrafficResultProcessor._extract_workload_id(dst),
                    'service_name': service.get('name'),
                    'service_port': service.get('port'),
                    'service_protocol': service.get('proto'),
                    'policy_decision': raw_data.get('policy_decision'),
                    'flow_direction': raw_data.get('flow_direction'),
                    'num_connections': raw_data.get('num_connections'),
                    'first_detected': raw_data.get('timestamp_range', {}).get('first_detected'),
                    'last_detected': raw_data.get('timestamp_range', {}).get('last_detected'),
                    'rule_href': rule_info.get('href'),
                    'rule_name': rule_info.get('name'),
                    'raw_data': flow.get('raw_data') or json.dumps(raw_data)
                }
                
                processed_flows.append(processed_flow)
            
            except Exception as e:
                print(f"Erreur lors du traitement d'un flux: {e}")
                # Optionally append the original flow if processing fails
                processed_flows.append(flow)
        
        return processed_flows
    
    @staticmethod
    def _extract_workload_id(entity: Dict[str, Any]) -> Optional[str]:
        """
        Extract workload ID from an entity (source or destination).
        
        Args:
            entity (dict): Source or destination dictionary
        
        Returns:
            Workload ID or None
        """
        workload = entity.get('workload', {})
        href = workload.get('href', '')
        return href.split('/')[-1] if href else None
    
    @staticmethod
    def _extract_rule_information(rules: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Extract rule information from various possible formats.
        
        Args:
            rules (dict): Rules dictionary from raw flow data
        
        Returns:
            Dictionary with rule href and name
        """
        # Default return if no rules found
        default_rule_info = {'href': None, 'name': None}
        
        # Handle different rule formats
        if isinstance(rules, dict) and 'sec_policy' in rules:
            # Old format before update_rules
            sec_policy = rules.get('sec_policy', {})
            return {
                'href': sec_policy.get('href'),
                'name': sec_policy.get('name')
            }
        
        elif isinstance(rules, list) and rules:
            # New format after update_rules
            first_rule = rules[0]
            return {
                'href': first_rule.get('href'),
                'name': first_rule.get('href', '').split('/')[-1]
            }
        
        return default_rule_info