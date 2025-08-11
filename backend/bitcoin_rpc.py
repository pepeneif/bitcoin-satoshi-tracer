from bitcoinrpc.authproxy import AuthServiceProxy
import os

rpc_user = os.getenv('RPC_USER', 'user')
rpc_password = os.getenv('RPC_PASSWORD', 'pass')
rpc_host = os.getenv('RPC_HOST', '127.0.0.1')
rpc_port = os.getenv('RPC_PORT', '8332')

rpc = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")

def get_utxo_history(txid, vout):
    # This should walk backwards from the given txid/vout
    # and yield intermediate steps for WebSocket streaming
    visited = set()
    stack = [(txid, vout)]
    while stack:
        current_txid, current_vout = stack.pop()
        if (current_txid, current_vout) in visited:
            continue
        visited.add((current_txid, current_vout))
        tx = rpc.getrawtransaction(current_txid, True)
        yield {"txid": current_txid, "vout": current_vout, "addresses": tx['vout'][current_vout].get('scriptPubKey', {}).get('addresses', [])}
        vin_list = tx.get('vin', [])
        for vin in vin_list:
            if 'txid' in vin:
                stack.append((vin['txid'], vin['vout']))