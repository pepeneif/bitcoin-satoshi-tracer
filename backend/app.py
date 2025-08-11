from flask import Flask, request
from flask_socketio import SocketIO, emit
from bitcoin_rpc import get_utxo_history

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('trace_utxo')
def trace_utxo(data):
    txid = data.get('txid')
    vout = data.get('vout')
    for step in get_utxo_history(txid, vout):
        emit('trace_update', step)
    emit('trace_complete')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)