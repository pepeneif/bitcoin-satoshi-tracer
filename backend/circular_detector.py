import logging
import time
from typing import Dict, List, Set, Tuple, Optional, Generator
from collections import defaultdict, deque
from dataclasses import dataclass, field
import hashlib
import json

logger = logging.getLogger(__name__)

@dataclass
class CircularPattern:
    """Represents a detected circular transaction pattern"""
    id: str
    transactions: List[Tuple[str, int]]  # List of (txid, vout) tuples
    addresses: Set[str]
    cycle_length: int
    total_value: float = 0.0
    risk_score: float = 0.0
    pattern_type: str = "unknown"
    confidence: float = 0.0
    detection_time: float = field(default_factory=time.time)
    temporal_span: float = 0.0  # Time span of the cycle in seconds
    
    def __post_init__(self):
        if not self.id:
            # Generate unique ID from transaction sequence
            tx_string = "->".join([f"{tx[0]}:{tx[1]}" for tx in self.transactions])
            self.id = hashlib.md5(tx_string.encode()).hexdigest()[:16]

@dataclass
class TransactionStep:
    """Enhanced transaction step with circular detection metadata"""
    txid: str
    vout: int
    addresses: List[str]
    value: float
    depth: int
    timestamp: Optional[float] = None
    script_type: str = "unknown"
    
class CircularTransactionDetector:
    """Advanced circular transaction detection system"""
    
    def __init__(self, max_cycle_length: int = 15):
        self.max_cycle_length = max_cycle_length
        self.transaction_graph = defaultdict(list)  # txid:vout -> [(next_txid, next_vout)]
        self.reverse_graph = defaultdict(list)      # txid:vout -> [(prev_txid, prev_vout)]
        self.address_to_transactions = defaultdict(set)  # address -> set of (txid, vout)
        self.transaction_to_addresses = {}          # (txid, vout) -> set of addresses
        self.transaction_metadata = {}              # (txid, vout) -> TransactionStep
        self.detected_cycles = []                   # List of CircularPattern objects
        self.visited_paths = set()                  # Cache for path analysis
        
        # Risk scoring weights
        self.risk_weights = {
            'cycle_length': 0.15,
            'complexity': 0.20,
            'value_concentration': 0.15,
            'timing_patterns': 0.10,
            'address_diversity': 0.15,
            'known_services': 0.10,
            'fresh_addresses': 0.10,
            'equal_splits': 0.05
        }
        
    def add_transaction_step(self, step: TransactionStep) -> List[CircularPattern]:
        """Add a transaction step and detect new circular patterns"""
        tx_key = (step.txid, step.vout)
        
        # Store transaction metadata
        self.transaction_metadata[tx_key] = step
        
        # Update address mappings
        if step.addresses:
            self.transaction_to_addresses[tx_key] = set(step.addresses)
            for addr in step.addresses:
                self.address_to_transactions[addr].add(tx_key)
        
        # Detect new cycles involving this transaction
        new_cycles = self._detect_cycles_from_transaction(tx_key)
        
        # Add to detected cycles
        for cycle in new_cycles:
            if self._is_valid_cycle(cycle):
                cycle.risk_score = self._calculate_risk_score(cycle)
                cycle.pattern_type = self._classify_pattern(cycle)
                cycle.confidence = self._calculate_confidence(cycle)
                self.detected_cycles.append(cycle)
        
        return new_cycles
    
    def add_transaction_link(self, from_tx: Tuple[str, int], to_tx: Tuple[str, int]):
        """Add a link between two transactions in the trace"""
        self.transaction_graph[from_tx].append(to_tx)
        self.reverse_graph[to_tx].append(from_tx)
    
    def _detect_cycles_from_transaction(self, tx_key: Tuple[str, int]) -> List[CircularPattern]:
        """Detect cycles that include the given transaction"""
        cycles = []
        
        # Method 1: Address-based cycle detection
        cycles.extend(self._detect_address_cycles(tx_key))
        
        # Method 2: Transaction path cycle detection
        cycles.extend(self._detect_path_cycles(tx_key))
        
        # Method 3: Strongly connected components
        cycles.extend(self._detect_scc_cycles(tx_key))
        
        return cycles
    
    def _detect_address_cycles(self, tx_key: Tuple[str, int]) -> List[CircularPattern]:
        """Detect cycles based on address reappearance"""
        cycles = []
        
        if tx_key not in self.transaction_to_addresses:
            return cycles
        
        current_addresses = self.transaction_to_addresses[tx_key]
        
        for addr in current_addresses:
            # Find all transactions involving this address
            addr_transactions = self.address_to_transactions[addr]
            
            if len(addr_transactions) > 1:
                # Look for potential cycles
                for other_tx in addr_transactions:
                    if other_tx != tx_key:
                        cycle_path = self._find_path_between_transactions(other_tx, tx_key)
                        if cycle_path and len(cycle_path) <= self.max_cycle_length:
                            # Found a potential cycle
                            cycle = self._create_circular_pattern(cycle_path, addr)
                            if cycle:
                                cycles.append(cycle)
        
        return cycles
    
    def _detect_path_cycles(self, tx_key: Tuple[str, int]) -> List[CircularPattern]:
        """Detect cycles in transaction paths using DFS"""
        cycles = []
        visited = set()
        path = []
        
        def dfs(current_tx, target_tx, depth):
            if depth > self.max_cycle_length:
                return
            
            if current_tx in visited:
                # Found a cycle
                cycle_start = path.index(current_tx)
                cycle_path = path[cycle_start:] + [current_tx]
                if len(cycle_path) > 2:  # Minimum cycle length
                    cycle = self._create_circular_pattern_from_path(cycle_path)
                    if cycle:
                        cycles.append(cycle)
                return
            
            visited.add(current_tx)
            path.append(current_tx)
            
            # Explore outgoing edges
            for next_tx in self.transaction_graph.get(current_tx, []):
                dfs(next_tx, target_tx, depth + 1)
            
            # Backtrack
            visited.remove(current_tx)
            path.pop()
        
        # Start DFS from the current transaction
        dfs(tx_key, tx_key, 0)
        
        return cycles
    
    def _detect_scc_cycles(self, tx_key: Tuple[str, int]) -> List[CircularPattern]:
        """Detect strongly connected components (advanced cycle detection)"""
        cycles = []
        
        # Simplified SCC detection for transaction subgraph
        # In a real implementation, you'd use Tarjan's or Kosaraju's algorithm
        visited = set()
        component = []
        
        def dfs_component(tx):
            if tx in visited or len(component) > self.max_cycle_length:
                return
            
            visited.add(tx)
            component.append(tx)
            
            for next_tx in self.transaction_graph.get(tx, []):
                if next_tx not in visited:
                    dfs_component(next_tx)
        
        # Check if this transaction is part of a strongly connected component
        if tx_key not in visited:
            dfs_component(tx_key)
            
            if len(component) > 2:
                # Check if it's actually circular
                if self._is_strongly_connected(component):
                    cycle = self._create_circular_pattern_from_path(component)
                    if cycle:
                        cycles.append(cycle)
        
        return cycles
    
    def _find_path_between_transactions(self, start_tx: Tuple[str, int], end_tx: Tuple[str, int]) -> Optional[List[Tuple[str, int]]]:
        """Find path between two transactions using BFS"""
        if start_tx == end_tx:
            return [start_tx]
        
        queue = deque([(start_tx, [start_tx])])
        visited = {start_tx}
        
        while queue:
            current_tx, path = queue.popleft()
            
            if len(path) > self.max_cycle_length:
                continue
            
            for next_tx in self.transaction_graph.get(current_tx, []):
                if next_tx == end_tx:
                    return path + [next_tx]
                
                if next_tx not in visited:
                    visited.add(next_tx)
                    queue.append((next_tx, path + [next_tx]))
        
        return None
    
    def _create_circular_pattern(self, path: List[Tuple[str, int]], trigger_address: str) -> Optional[CircularPattern]:
        """Create a CircularPattern object from a detected cycle"""
        if len(path) < 3:  # Minimum cycle length
            return None
        
        # Collect all addresses involved in the cycle
        all_addresses = set()
        total_value = 0.0
        
        for tx_key in path:
            if tx_key in self.transaction_to_addresses:
                all_addresses.update(self.transaction_to_addresses[tx_key])
            if tx_key in self.transaction_metadata:
                total_value += self.transaction_metadata[tx_key].value
        
        cycle = CircularPattern(
            id="",  # Will be auto-generated
            transactions=path,
            addresses=all_addresses,
            cycle_length=len(path),
            total_value=total_value
        )
        
        return cycle
    
    def _create_circular_pattern_from_path(self, path: List[Tuple[str, int]]) -> Optional[CircularPattern]:
        """Create CircularPattern from a transaction path"""
        return self._create_circular_pattern(path, "")
    
    def _is_valid_cycle(self, cycle: CircularPattern) -> bool:
        """Validate if a detected cycle is legitimate"""
        # Check minimum requirements
        if cycle.cycle_length < 3 or cycle.cycle_length > self.max_cycle_length:
            return False
        
        # Check if we've already detected this cycle
        cycle_signature = tuple(sorted(cycle.transactions))
        if cycle_signature in self.visited_paths:
            return False
        
        self.visited_paths.add(cycle_signature)
        return True
    
    def _is_strongly_connected(self, component: List[Tuple[str, int]]) -> bool:
        """Check if a component is strongly connected"""
        # Simplified check - in practice, you'd want more robust verification
        if len(component) < 3:
            return False
        
        # Check if there are enough edges to form cycles
        edge_count = sum(len(self.transaction_graph.get(tx, [])) for tx in component)
        return edge_count >= len(component)
    
    def _calculate_risk_score(self, cycle: CircularPattern) -> float:
        """Calculate comprehensive risk score for a circular pattern"""
        factors = {
            'cycle_length': self._score_cycle_length(cycle),
            'complexity': self._score_complexity(cycle),
            'value_concentration': self._score_value_patterns(cycle),
            'timing_patterns': self._score_timing_patterns(cycle),
            'address_diversity': self._score_address_diversity(cycle),
            'known_services': self._score_service_involvement(cycle),
            'fresh_addresses': self._score_fresh_addresses(cycle),
            'equal_splits': self._score_equal_splitting(cycle)
        }
        
        weighted_score = sum(
            factors[factor] * self.risk_weights[factor] 
            for factor in factors
        )
        
        return min(1.0, max(0.0, weighted_score))
    
    def _score_cycle_length(self, cycle: CircularPattern) -> float:
        """Score based on cycle length (shorter cycles are more suspicious)"""
        if cycle.cycle_length <= 3:
            return 0.9  # Very suspicious
        elif cycle.cycle_length <= 5:
            return 0.7  # Suspicious
        elif cycle.cycle_length <= 8:
            return 0.5  # Moderate
        else:
            return 0.3  # Less suspicious
    
    def _score_complexity(self, cycle: CircularPattern) -> float:
        """Score based on transaction complexity"""
        # Higher address-to-transaction ratio suggests more complex mixing
        if len(cycle.addresses) == 0:
            return 0.0
        
        complexity_ratio = len(cycle.transactions) / len(cycle.addresses)
        return min(1.0, complexity_ratio / 3.0)  # Normalize to 0-1
    
    def _score_value_patterns(self, cycle: CircularPattern) -> float:
        """Score based on value distribution patterns"""
        if cycle.total_value == 0:
            return 0.0
        
        # Analyze value distribution across transactions
        values = []
        for tx_key in cycle.transactions:
            if tx_key in self.transaction_metadata:
                values.append(self.transaction_metadata[tx_key].value)
        
        if not values:
            return 0.0
        
        # Check for equal or similar values (indicating structured mixing)
        value_variance = self._calculate_variance(values)
        avg_value = sum(values) / len(values)
        
        if avg_value > 0:
            cv = (value_variance ** 0.5) / avg_value  # Coefficient of variation
            return max(0.0, 1.0 - cv)  # Lower variance = higher suspicion
        
        return 0.0
    
    def _score_timing_patterns(self, cycle: CircularPattern) -> float:
        """Score based on temporal patterns"""
        timestamps = []
        for tx_key in cycle.transactions:
            if tx_key in self.transaction_metadata:
                metadata = self.transaction_metadata[tx_key]
                if metadata.timestamp:
                    timestamps.append(metadata.timestamp)
        
        if len(timestamps) < 2:
            return 0.0
        
        # Check for regular intervals (automated mixing)
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        interval_variance = self._calculate_variance(intervals)
        
        # Regular intervals are more suspicious
        if interval_variance < 3600:  # Less than 1 hour variance
            return 0.8
        elif interval_variance < 86400:  # Less than 1 day variance
            return 0.5
        else:
            return 0.2
    
    def _score_address_diversity(self, cycle: CircularPattern) -> float:
        """Score based on address diversity and types"""
        if not cycle.addresses:
            return 0.0
        
        # Check address types
        address_types = set()
        for addr in cycle.addresses:
            addr_type = self._classify_address_type(addr)
            address_types.add(addr_type)
        
        # More diverse address types = potentially more sophisticated
        diversity_score = len(address_types) / 4.0  # Normalize (P2PKH, P2SH, P2WPKH, P2WSH)
        return min(1.0, diversity_score)
    
    def _score_service_involvement(self, cycle: CircularPattern) -> float:
        """Score based on known service involvement"""
        # This would integrate with known address databases
        # For now, return neutral score
        return 0.5
    
    def _score_fresh_addresses(self, cycle: CircularPattern) -> float:
        """Score based on fresh address usage"""
        # Higher score for cycles with many single-use addresses
        # This would require blockchain analysis - simplified for now
        return 0.5
    
    def _score_equal_splitting(self, cycle: CircularPattern) -> float:
        """Score based on equal value splitting patterns"""
        values = []
        for tx_key in cycle.transactions:
            if tx_key in self.transaction_metadata:
                values.append(self.transaction_metadata[tx_key].value)
        
        if len(values) < 3:
            return 0.0
        
        # Check for equal splits (common in mixing)
        equal_count = 0
        for i in range(len(values) - 1):
            if abs(values[i] - values[i+1]) < 0.001:  # Very close values
                equal_count += 1
        
        return equal_count / (len(values) - 1)
    
    def _classify_pattern(self, cycle: CircularPattern) -> str:
        """Classify the type of circular pattern"""
        if cycle.cycle_length <= 3:
            return "immediate_return"
        elif cycle.cycle_length <= 6:
            return "short_cycle"
        elif cycle.cycle_length <= 10:
            return "medium_cycle"
        else:
            return "long_cycle"
        
        # Additional classification based on characteristics
        if cycle.risk_score > 0.8:
            return "high_risk_mixing"
        elif len(cycle.addresses) > cycle.cycle_length * 2:
            return "complex_mixing"
        else:
            return "standard_circulation"
    
    def _calculate_confidence(self, cycle: CircularPattern) -> float:
        """Calculate confidence in the cycle detection"""
        factors = []
        
        # Path completeness
        complete_transactions = sum(1 for tx in cycle.transactions if tx in self.transaction_metadata)
        completeness = complete_transactions / len(cycle.transactions)
        factors.append(completeness)
        
        # Address consistency
        if cycle.addresses:
            address_consistency = len(set(cycle.addresses)) / len(cycle.addresses)
            factors.append(address_consistency)
        
        # Structural consistency
        if cycle.cycle_length >= 3:
            factors.append(0.8)  # Base confidence for valid cycles
        
        return sum(factors) / len(factors) if factors else 0.0
    
    def _classify_address_type(self, address: str) -> str:
        """Classify Bitcoin address type"""
        if not address:
            return "unknown"
        
        if address.startswith('1'):
            return "p2pkh"
        elif address.startswith('3'):
            return "p2sh"
        elif address.startswith('bc1q'):
            return "p2wpkh"
        elif address.startswith('bc1p'):
            return "p2tr"
        else:
            return "unknown"
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def generate_analysis_report(self) -> Dict:
        """Generate comprehensive analysis report"""
        if not self.detected_cycles:
            return {
                'total_cycles': 0,
                'high_risk_cycles': 0,
                'analysis_summary': 'No circular patterns detected',
                'cycles': []
            }
        
        high_risk_cycles = [c for c in self.detected_cycles if c.risk_score > 0.7]
        
        cycle_data = []
        for cycle in self.detected_cycles:
            cycle_data.append({
                'id': cycle.id,
                'cycle_length': cycle.cycle_length,
                'risk_score': cycle.risk_score,
                'pattern_type': cycle.pattern_type,
                'confidence': cycle.confidence,
                'total_value': cycle.total_value,
                'addresses': list(cycle.addresses),
                'transactions': [{'txid': tx[0], 'vout': tx[1]} for tx in cycle.transactions]
            })
        
        return {
            'total_cycles': len(self.detected_cycles),
            'high_risk_cycles': len(high_risk_cycles),
            'average_risk_score': sum(c.risk_score for c in self.detected_cycles) / len(self.detected_cycles),
            'pattern_types': list(set(c.pattern_type for c in self.detected_cycles)),
            'total_circular_value': sum(c.total_value for c in self.detected_cycles),
            'analysis_summary': f'Detected {len(self.detected_cycles)} circular patterns with {len(high_risk_cycles)} high-risk cases',
            'cycles': cycle_data
        }
    
    def get_cycles_by_risk(self, min_risk: float = 0.5) -> List[CircularPattern]:
        """Get cycles above a certain risk threshold"""
        return [cycle for cycle in self.detected_cycles if cycle.risk_score >= min_risk]
    
    def get_cycles_by_pattern_type(self, pattern_type: str) -> List[CircularPattern]:
        """Get cycles of a specific pattern type"""
        return [cycle for cycle in self.detected_cycles if cycle.pattern_type == pattern_type]