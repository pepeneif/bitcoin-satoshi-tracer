from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os
import logging
import time

logger = logging.getLogger(__name__)

# Read RPC configuration from environment
rpc_user = os.getenv('RPC_USER', 'user')
rpc_password = os.getenv('RPC_PASSWORD', 'pass')
rpc_host = os.getenv('RPC_HOST', '127.0.0.1')
rpc_port = os.getenv('RPC_PORT', '8332')

# Create RPC connection
rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}"
rpc = AuthServiceProxy(rpc_url)

def test_rpc_connection():
    """Test the Bitcoin RPC connection"""
    try:
        # Try to get basic blockchain info
        info = rpc.getblockchaininfo()
        return {
            'connected': True,
            'message': f'Connected to Bitcoin Core. Blocks: {info.get("blocks", "unknown")}, Chain: {info.get("chain", "unknown")}'
        }
    except JSONRPCException as e:
        logger.error(f'Bitcoin RPC error: {e}')
        return {
            'connected': False,
            'message': f'RPC Error: {e}'
        }
    except Exception as e:
        logger.error(f'Connection error: {e}')
        return {
            'connected': False,
            'message': f'Connection failed: {e}'
        }

def get_transaction_with_retry(txid, max_retries=3, delay=1):
    """Get transaction with retry logic"""
    for attempt in range(max_retries):
        try:
            return rpc.getrawtransaction(txid, True)
        except JSONRPCException as e:
            if 'No such mempool or blockchain transaction' in str(e):
                raise ValueError(f'Transaction {txid} not found')
            if attempt == max_retries - 1:
                raise e
            logger.warning(f'RPC request failed (attempt {attempt + 1}/{max_retries}): {e}')
            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            logger.warning(f'Connection error (attempt {attempt + 1}/{max_retries}): {e}')
            time.sleep(delay)

def get_utxo_history(txid, vout):
    """
    Walk backwards from the given txid/vout and yield intermediate steps
    for WebSocket streaming. This traces the satoshi history.
    """
    logger.info(f'Starting UTXO trace for {txid}:{vout}')
    
    visited = set()
    stack = [(txid, vout, 0)]  # (txid, vout, depth)
    max_depth = 100  # Prevent infinite loops
    
    while stack:
        current_txid, current_vout, depth = stack.pop()
        
        # Check depth limit
        if depth >= max_depth:
            logger.warning(f'Maximum trace depth ({max_depth}) reached')
            break
            
        # Skip if already visited
        if (current_txid, current_vout) in visited:
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
                
            # Extract address information
            vout_data = tx['vout'][current_vout]
            script_pub_key = vout_data.get('scriptPubKey', {})
            addresses = script_pub_key.get('addresses', [])
            
            # Handle newer Bitcoin Core versions that use 'address' instead of 'addresses'
            if not addresses and 'address' in script_pub_key:
                addresses = [script_pub_key['address']]
            
            # Get value if available
            value = vout_data.get('value', 0)
            
            # Yield current step
            step_data = {
                "txid": current_txid,
                "vout": current_vout,
                "addresses": addresses,
                "value": value,
                "depth": depth,
                "script_type": script_pub_key.get('type', 'unknown')
            }
            
            logger.debug(f'Yielding step: {step_data}')
            yield step_data
            
            # Add previous transactions (inputs) to the stack
            vin_list = tx.get('vin', [])
            for vin in vin_list:
                if 'txid' in vin and 'vout' in vin:
                    # Skip coinbase transactions (no previous transaction)
                    if vin.get('txid') and vin.get('txid') != '0' * 64:
                        stack.append((vin['txid'], vin['vout'], depth + 1))
                        
        except ValueError as e:
            # Transaction not found or invalid
            logger.error(f'Transaction error for {current_txid}: {e}')
            raise e
            
        except JSONRPCException as e:
            logger.error(f'RPC error processing {current_txid}:{current_vout}: {e}')
            raise Exception(f'Bitcoin RPC error: {e}')
            
        except Exception as e:
            logger.error(f'Unexpected error processing {current_txid}:{current_vout}: {e}')
            raise Exception(f'Failed to process transaction: {e}')
    
    logger.info(f'UTXO trace completed. Visited {len(visited)} transactions.')

def get_address_info(address):
    """Get information about a Bitcoin address (if available)"""
    try:
        # This requires Bitcoin Core with address index enabled
        return rpc.getaddressinfo(address)
    except JSONRPCException:
        # Address info not available
        return None
    except Exception as e:
        logger.warning(f'Failed to get address info for {address}: {e}')
        return None

def validate_txid(txid):
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