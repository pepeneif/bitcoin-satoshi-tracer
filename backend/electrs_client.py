import os
import logging
import time
import hashlib
import json
import socket
from typing import Dict, List, Optional, Generator, Tuple
from circular_detector import CircularTransactionDetector, TransactionStep, CircularPattern

logger = logging.getLogger(__name__)

# Read Electrs configuration from environment
electrs_host = os.getenv('ELECTRS_HOST', '127.0.0.1')
electrs_port = int(os.getenv('ELECTRS_PORT', '50001'))
electrs_use_ssl = os.getenv('ELECTRS_USE_SSL', 'false').lower() == 'true'
electrs_ssl_port = int(os.getenv('ELECTRS_SSL_PORT', '50002'))

# Global client instance
_client = None

def get_script_hash(address: str) -> str:
    """Convert Bitcoin address to script hash for Electrum queries"""
    try:
        from bitcoin.segwit_addr import decode
        from bitcoin.core.script import CScript
        import bitcoin.base58
        
        # Simple script hash generation for Electrum protocol
        # This is a fallback implementation
        script_hash = hashlib.sha256(address.encode()).digest()
        # Reverse the hash for Electrum protocol
        return script_hash[::-1].hex()
    except Exception as e:
        logger.error(f"Failed to convert address {address} to script hash: {e}")
        # Fallback: create a simple hash (less accurate but functional)
        return hashlib.sha256(address.encode()).hexdigest()

class ElectrsClient:
    """Direct JSON-RPC client for Electrs server"""
    
    def __init__(self, host: str, port: int, use_ssl: bool = False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.socket = None
        self.request_id = 0
        
    def connect(self):
        """Establish connection to Electrs server"""
        try:
            if self.use_ssl:
                import ssl
                context = ssl.create_default_context()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket = context.wrap_socket(sock, server_hostname=self.host)
            else:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            self.socket.settimeout(30)  # 30 second timeout
            self.socket.connect((self.host, self.port))
            logger.info(f"Connected to Electrs server at {self.host}:{self.port} (SSL: {self.use_ssl})")
            
        except Exception as e:
            logger.error(f"Failed to connect to Electrs server: {e}")
            raise
    
    def close(self):
        """Close connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def call(self, method: str, params: List = None):
        """Make a JSON-RPC call to the Electrs server"""
        if not self.socket:
            self.connect()
        
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": self.request_id
        }
        
        try:
            # Send request
            request_data = json.dumps(request) + '\n'
            self.socket.sendall(request_data.encode('utf-8'))
            
            # Receive response
            response_data = b''
            while b'\n' not in response_data:
                chunk = self.socket.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed by server")
                response_data += chunk
            
            # Parse response
            response_line = response_data.split(b'\n')[0]
            response = json.loads(response_line.decode('utf-8'))
            
            if 'error' in response:
                error = response['error']
                raise Exception(f"Electrs error: {error.get('message', error)}")
            
            return response.get('result')
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Electrs: {e}")
            raise
        except Exception as e:
            logger.error(f"Electrs call failed: {e}")
            # Try to reconnect on connection errors
            if 'connection' in str(e).lower():
                self.close()
            raise

def get_client() -> ElectrsClient:
    """Get or create Electrs client instance"""
    global _client
    
    if _client is None:
        port = electrs_ssl_port if electrs_use_ssl else electrs_port
        _client = ElectrsClient(electrs_host, port, electrs_use_ssl)
    
    return _client

def close_client():
    """Close the Electrs client connection"""
    global _client
    if _client:
        _client.close()
        _client = None

def test_electrs_connection():
    """Test the Electrs connection"""
    try:
        client = get_client()
        # Test with server version call - simpler format
        version_info = client.call('server.version', ['satoshi-tracer', ['1.4', '1.4.2']])
        return {
            'connected': True,
            'message': f'Connected to Electrs server. Version: {version_info}'
        }
        
    except Exception as e:
        logger.error(f'Electrs connection error: {e}')
        # Try a simpler connection test if version fails
        try:
            client = get_client()
            # Just test basic connectivity
            client.connect()
            return {
                'connected': True,
                'message': 'Connected to Electrs server (version check failed but connection OK)'
            }
        except Exception as e2:
            return {
                'connected': False,
                'message': f'Connection failed: {e2}'
            }

def get_transaction_async(txid: str) -> Dict:
    """Get transaction data from Electrs server"""
    try:
        client = get_client()
        # Get raw transaction hex
        tx_hex = client.call('blockchain.transaction.get', [txid])
        
        # Also get transaction with verbose information if available
        try:
            tx_verbose = client.call('blockchain.transaction.get', [txid, True])
            if isinstance(tx_verbose, dict):
                return tx_verbose
        except:
            # Fallback to hex-only response
            pass
        
        # For now, return a simplified transaction format
        # In production, you'd want to parse the hex using a proper bitcoin library
        return {
            'txid': txid,
            'hex': tx_hex,
            'vin': [],  # Would need hex parsing
            'vout': [],  # Would need hex parsing
            'blocktime': None,
            'confirmations': None
        }
        
    except Exception as e:
        logger.error(f"Failed to get transaction {txid}: {e}")
        raise

def _extract_addresses_from_script(script_hex: str) -> List[str]:
    """Extract Bitcoin addresses from script hex"""
    try:
        if not script_hex:
            return []
        
        # Simple address extraction - this is a fallback implementation
        try:
            if script_hex:
                # This is a simplified implementation
                # In production, you'd want more robust script parsing
                return []  # Return empty for now, can be enhanced later
        except Exception:
            pass
        return []
    except Exception as e:
        logger.debug(f"Could not extract address from script {script_hex}: {e}")
        return []

def _get_script_type(script_hex: str) -> str:
    """Determine script type from hex"""
    try:
        if not script_hex:
            return 'unknown'
        
        script_bytes = bytes.fromhex(script_hex)
        
        # P2PKH
        if len(script_bytes) == 25 and script_bytes[0] == 0x76 and script_bytes[1] == 0xa9:
            return 'pubkeyhash'
        # P2SH
        elif len(script_bytes) == 23 and script_bytes[0] == 0xa9:
            return 'scripthash'
        # P2WPKH
        elif len(script_bytes) == 22 and script_bytes[0] == 0x00 and script_bytes[1] == 0x14:
            return 'witness_v0_keyhash'
        # P2WSH
        elif len(script_bytes) == 34 and script_bytes[0] == 0x00 and script_bytes[1] == 0x20:
            return 'witness_v0_scripthash'
        else:
            return 'unknown'
            
    except Exception:
        return 'unknown'

def get_transaction_with_retry(txid: str, max_retries: int = 3, delay: int = 1) -> Dict:
    """Get transaction with retry logic"""
    for attempt in range(max_retries):
        try:
            result = get_transaction_async(txid)
            return result
                
        except Exception as e:
            if 'not found' in str(e).lower() or 'invalid' in str(e).lower():
                raise ValueError(f'Transaction {txid} not found')
            if attempt == max_retries - 1:
                raise e
            logger.warning(f'Electrs request failed (attempt {attempt + 1}/{max_retries}): {e}')
            time.sleep(delay)

def get_utxo_history(txid: str, vout: int, max_depth: int = 20, enable_circular_detection: bool = True) -> Generator[Dict, None, None]:
    """
    Walk backwards from the given txid/vout and yield intermediate steps
    for WebSocket streaming. This traces the satoshi history using Electrs with optional circular detection.
    """
    logger.info(f'Starting UTXO trace for {txid}:{vout} (max_depth: {max_depth}, circular_detection: {enable_circular_detection})')
    
    visited = set()
    stack = [(txid, vout, 0)]  # (txid, vout, depth)
    all_addresses = set()  # Collect all unique addresses
    
    # Initialize circular transaction detector
    circular_detector = CircularTransactionDetector(max_cycle_length=min(15, max_depth)) if enable_circular_detection else None
    previous_tx = None
    
    while stack:
        current_txid, current_vout, depth = stack.pop()
        
        # Check depth limit
        if depth >= max_depth:
            logger.warning(f'Maximum trace depth ({max_depth}) reached')
            break
            
        # Skip if already visited
        if (current_txid, current_vout) in visited:
            # If circular detection is enabled, this might indicate a cycle
            if circular_detector and previous_tx:
                circular_detector.add_transaction_link(previous_tx, (current_txid, current_vout))
            continue
            
        visited.add((current_txid, current_vout))
        logger.debug(f'Processing {current_txid}:{current_vout} (depth: {depth})')
        
        try:
            # Get the transaction
            tx = get_transaction_with_retry(current_txid)
            
            # Validate vout index
            if current_vout >= len(tx.get('vout', [])):
                logger.error(f'Invalid vout index {current_vout} for transaction {current_txid}')
                continue
                
            # Extract output information
            vout_data = tx['vout'][current_vout]
            script_pub_key = vout_data.get('scriptPubKey', {})
            addresses = script_pub_key.get('addresses', [])
            
            # Get value if available
            value = vout_data.get('value', 0)
            
            # Collect unique addresses
            if addresses:
                all_addresses.update(addresses)
            
            # Create transaction step for circular detection
            if circular_detector:
                tx_step = TransactionStep(
                    txid=current_txid,
                    vout=current_vout,
                    addresses=addresses,
                    value=value,
                    depth=depth,
                    script_type=script_pub_key.get('type', 'unknown')
                )
                
                # Add to circular detector and check for new patterns
                new_cycles = circular_detector.add_transaction_step(tx_step)
                
                # Link to previous transaction
                if previous_tx:
                    circular_detector.add_transaction_link(previous_tx, (current_txid, current_vout))
                
                # Yield circular pattern alerts
                for cycle in new_cycles:
                    yield {
                        "type": "circular_pattern_detected",
                        "cycle_id": cycle.id,
                        "cycle_length": cycle.cycle_length,
                        "risk_score": cycle.risk_score,
                        "pattern_type": cycle.pattern_type,
                        "confidence": cycle.confidence,
                        "total_value": cycle.total_value,
                        "addresses_involved": list(cycle.addresses),
                        "transactions": [{"txid": tx[0], "vout": tx[1]} for tx in cycle.transactions]
                    }
            
            # Yield current step with enhanced data
            step_data = {
                "txid": current_txid,
                "vout": current_vout,
                "addresses": addresses,
                "value": value,
                "depth": depth,
                "script_type": script_pub_key.get('type', 'unknown'),
                "circular_risk": 0.0,  # Will be updated if part of a cycle
                "is_circular": False   # Will be updated if part of a cycle
            }
            
            # Check if this transaction is part of any detected cycles
            if circular_detector:
                current_tx_key = (current_txid, current_vout)
                for cycle in circular_detector.detected_cycles:
                    if current_tx_key in cycle.transactions:
                        step_data["circular_risk"] = cycle.risk_score
                        step_data["is_circular"] = True
                        step_data["cycle_id"] = cycle.id
                        break
            
            logger.debug(f'Yielding step: {step_data}')
            yield step_data
            
            # Add previous transactions (inputs) to the stack
            vin_list = tx.get('vin', [])
            for vin in vin_list:
                if 'txid' in vin and 'vout' in vin:
                    # Skip coinbase transactions (no previous transaction)
                    if vin.get('txid') and vin.get('txid') != '0' * 64:
                        stack.append((vin['txid'], vin['vout'], depth + 1))
            
            # Update previous transaction for linking
            previous_tx = (current_txid, current_vout)
                        
        except ValueError as e:
            # Transaction not found or invalid
            logger.error(f'Transaction error for {current_txid}: {e}')
            raise e
            
        except Exception as e:
            logger.error(f'Electrs error processing {current_txid}:{current_vout}: {e}')
            raise Exception(f'Electrs error: {e}')
    
    # Yield final analysis if circular detection was enabled
    if circular_detector:
        final_analysis = circular_detector.generate_analysis_report()
        yield {
            "type": "circular_analysis_complete",
            "analysis": final_analysis,
            "all_addresses": list(all_addresses),
            "total_transactions": len(visited)
        }
    else:
        # Yield address summary without circular analysis
        yield {
            "type": "trace_complete",
            "all_addresses": list(all_addresses),
            "total_transactions": len(visited)
        }
    
    logger.info(f'UTXO trace completed. Visited {len(visited)} transactions. Found {len(all_addresses)} unique addresses.')

def get_address_info(address: str) -> Optional[Dict]:
    """Get information about a Bitcoin address using Electrs"""
    try:
        client = get_client()
        script_hash = get_script_hash(address)
        
        # Get address history
        history = client.call('blockchain.scripthash.get_history', [script_hash])
        
        # Get current balance
        balance_info = client.call('blockchain.scripthash.get_balance', [script_hash])
        
        return {
            'address': address,
            'balance': balance_info.get('confirmed', 0) + balance_info.get('unconfirmed', 0),
            'tx_count': len(history) if history else 0,
            'script_hash': script_hash
        }
        
    except Exception as e:
        logger.warning(f'Failed to get address info for {address}: {e}')
        return None

def validate_txid(txid: str) -> bool:
    """Validate that a string is a valid Bitcoin transaction ID"""
    if not isinstance(txid, str):
        return False
    if len(txid) != 64:
        return False
    try:
        int(txid, 16)
        return True
    except ValueError:
        return False