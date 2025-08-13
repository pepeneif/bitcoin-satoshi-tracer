from flask import Flask
from flask_socketio import SocketIO, emit
from electrs_client import get_utxo_history
import logging
import sys
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", logger=True)

@socketio.on('connect')
def handle_connect():
    from flask import request
    logger.info(f'Client connected: {request.sid}')
    emit('status', {'message': 'Connected to Bitcoin Tracer backend (Electrs)'})

@socketio.on('disconnect')
def handle_disconnect():
    from flask import request
    logger.info(f'Client disconnected: {request.sid}')

@socketio.on('trace_utxo')
def handle_trace_utxo(data):
    try:
        logger.info(f'Received trace request: {data}')
        
        # Validate input data
        if not data or not isinstance(data, dict):
            emit('trace_error', {'message': 'Invalid request data'})
            return
            
        txid = data.get('txid')
        vout = data.get('vout')
        
        # Validate TXID
        if not txid or not isinstance(txid, str):
            emit('trace_error', {'message': 'TXID is required and must be a string'})
            return
            
        txid = txid.strip()
        if len(txid) != 64:
            emit('trace_error', {'message': 'TXID must be exactly 64 characters long'})
            return
            
        try:
            # Validate that TXID is hexadecimal
            int(txid, 16)
        except ValueError:
            emit('trace_error', {'message': 'TXID must be a valid hexadecimal string'})
            return
        
        # Validate VOUT
        if vout is None:
            emit('trace_error', {'message': 'VOUT is required'})
            return
            
        try:
            vout = int(vout)
            if vout < 0:
                emit('trace_error', {'message': 'VOUT must be a non-negative integer'})
                return
        except (ValueError, TypeError):
            emit('trace_error', {'message': 'VOUT must be a valid integer'})
            return
        
        logger.info(f'Starting trace for TXID: {txid}, VOUT: {vout}')
        emit('status', {'message': f'Starting trace for {txid}:{vout}'})
        
        # Counter for traced transactions
        trace_count = 0
        max_trace_depth = 100  # Prevent infinite loops
        
        try:
            for step in get_utxo_history(txid, vout):
                trace_count += 1
                logger.info(f'Traced step {trace_count}: {step.get("txid", "unknown")}:{step.get("vout", "unknown")}')
                
                # Add some metadata to the step
                step_with_metadata = {
                    **step,
                    'trace_index': trace_count,
                    'timestamp': None  # Could be enhanced to include block timestamp
                }
                
                emit('trace_update', step_with_metadata)
                
                # Safety check to prevent excessive traces
                if trace_count >= max_trace_depth:
                    logger.warning(f'Trace depth limit reached ({max_trace_depth}). Stopping trace.')
                    emit('trace_error', {
                        'message': f'Trace depth limit reached ({max_trace_depth} transactions). This might indicate a very long transaction chain or a potential loop.'
                    })
                    return
                    
        except Exception as trace_error:
            logger.error(f'Error during trace execution: {str(trace_error)}')
            logger.error(traceback.format_exc())
            
            # Determine the type of error and provide appropriate message
            error_message = str(trace_error)
            if 'connection' in error_message.lower():
                error_message = 'Failed to connect to Electrs server. Please check your Electrs configuration.'
            elif 'authentication' in error_message.lower() or 'unauthorized' in error_message.lower():
                error_message = 'Electrs server authentication failed. Please check your server configuration.'
            elif 'not found' in error_message.lower() or 'invalid' in error_message.lower():
                error_message = f'Transaction {txid} not found. Please verify the TXID is correct and the transaction exists.'
            else:
                error_message = f'Trace failed: {error_message}'
                
            emit('trace_error', {'message': error_message})
            return
        
        logger.info(f'Trace completed successfully. Total transactions traced: {trace_count}')
        emit('trace_complete', {'total_transactions': trace_count})
        
    except Exception as e:
        logger.error(f'Unexpected error in trace_utxo handler: {str(e)}')
        logger.error(traceback.format_exc())
        emit('trace_error', {'message': f'Unexpected server error: {str(e)}'})

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    try:
        # Test Electrs connection
        from electrs_client import test_electrs_connection
        electrs_status = test_electrs_connection()
        return {
            'status': 'healthy',
            'electrs_connected': electrs_status['connected'],
            'electrs_message': electrs_status['message']
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }, 500

if __name__ == '__main__':
    logger.info('Starting Bitcoin Satoshi Tracer backend (Electrs)...')
    try:
        # Test Electrs connection on startup
        from electrs_client import test_electrs_connection
        electrs_status = test_electrs_connection()
        if electrs_status['connected']:
            logger.info(f'Electrs connection successful: {electrs_status["message"]}')
        else:
            logger.warning(f'Electrs connection failed: {electrs_status["message"]}')
            logger.warning('Server will start but tracing may not work until Electrs connection is fixed.')
    except Exception as e:
        logger.error(f'Failed to test Electrs connection on startup: {e}')
    
    logger.info('Starting Flask-SocketIO server on 0.0.0.0:5000')
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)