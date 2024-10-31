from graphviz import Digraph
from typing import Dict, List
from .state_machine import StateMachine, Transition

class StateMachineVisualizer:
    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        
    def generate_dot(self) -> Digraph:
        dot = Digraph(comment='Risk State Machine')
        dot.attr(rankdir='LR')  # Left to right layout
        
        # Node styling
        dot.attr('node', shape='circle')
        
        # Add states
        for from_state in self.state_machine.transitions:
            dot.node(from_state)
            for to_state in self.state_machine.transitions[from_state]:
                dot.node(to_state)
                
                # Get transition details
                transition = self.state_machine.transitions[from_state][to_state]
                label = f"{len(transition.conditions)} conditions\n"
                label += f"{len(transition.required_fields)} required fields"
                
                # Add edge with details
                dot.edge(from_state, to_state, label=label)
        
        return dot 