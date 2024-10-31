from typing import List, Dict, Set
from .schemas import RiskCreate, BatchRiskCreate, ValidationResult
from datetime import datetime
import networkx as nx

class RiskValidator:
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        
    def validate_single(self, risk: Dict) -> ValidationResult:
        """Validate a single risk with detailed error reporting"""
        try:
            validated = RiskCreate(**risk)
            result = ValidationResult(valid=True)
            
            # Add warnings for potential issues
            warnings = []
            if validated.probability == "High" and not validated.mitigation:
                warnings.append("High probability risks should have mitigation plans")
            if validated.due_date and validated.due_date < datetime.now() + timedelta(days=7):
                warnings.append("Due date is less than 7 days away")
                
            if warnings:
                result.warnings["general"] = warnings
                
            return result
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors={"validation": [str(e)]}
            )

    def validate_batch(self, risks: List[Dict]) -> ValidationResult:
        """Validate a batch of risks including their relationships"""
        try:
            # First pass: basic validation
            batch = BatchRiskCreate(risks=risks)
            
            # Second pass: relationship validation
            self.dependency_graph.clear()
            risk_ids = set()
            
            for risk in batch.risks:
                risk_ids.add(risk.id)
                for dep in risk.dependencies:
                    self.dependency_graph.add_edge(risk.id, dep)
            
            # Check for cycles
            try:
                cycles = list(nx.simple_cycles(self.dependency_graph))
                if cycles:
                    return ValidationResult(
                        valid=False,
                        errors={"dependencies": [f"Circular dependencies found: {cycles}"]}
                    )
            except nx.NetworkXError as e:
                return ValidationResult(
                    valid=False,
                    errors={"dependencies": [str(e)]}
                )
            
            # Check resource allocation
            total_resources = {}
            for risk in batch.risks:
                for resource, amount in risk.resource_requirements.items():
                    total_resources[resource] = total_resources.get(resource, 0) + amount
            
            # Add warnings for high resource usage
            warnings = {}
            for resource, amount in total_resources.items():
                if amount > 1000000:  # Example threshold
                    warnings[f"resource_{resource}"] = [
                        f"High resource allocation: {amount}"
                    ]
            
            return ValidationResult(valid=True, warnings=warnings)
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors={"batch": [str(e)]}
            )

    def validate_relationships(self, relationships: List[Dict]) -> ValidationResult:
        """Validate risk relationships and their impact"""
        try:
            graph = nx.DiGraph()
            
            for rel in relationships:
                graph.add_edge(rel["source_id"], rel["target_id"], 
                             weight=rel["strength"])
            
            # Check for cycles
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                return ValidationResult(
                    valid=False,
                    errors={"relationships": [f"Circular relationships found: {cycles}"]}
                )
            
            # Check for isolated nodes
            isolated = list(nx.isolates(graph))
            warnings = {}
            if isolated:
                warnings["isolated"] = [
                    f"Isolated risks found: {isolated}"
                ]
            
            # Check for critical paths
            try:
                critical_path = nx.dag_longest_path(graph, weight="weight")
                if len(critical_path) > 5:  # Example threshold
                    warnings["critical_path"] = [
                        f"Long critical path detected: {critical_path}"
                    ]
            except nx.NetworkXError:
                pass
            
            return ValidationResult(valid=True, warnings=warnings)
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors={"relationships": [str(e)]}
            ) 