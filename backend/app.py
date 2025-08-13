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
        # Validate session before processing
        from flask import request
        if not hasattr(request, 'sid') or not request.sid:
            logger.error('Invalid socket session in trace_utxo handler')
            return
        
        logger.info(f'Received trace request: {data}')
        
        # Validate input data
        if not data or not isinstance(data, dict):
            emit('trace_error', {'message': 'Invalid request data'})
            return
            
        txid = data.get('txid')
        vout = data.get('vout')
        trace_depth = data.get('trace_depth', 20)  # Default to 20
        enable_circular_detection = data.get('enable_circular_detection', True)
        
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
        
        # Validate trace depth
        try:
            trace_depth = int(trace_depth)
            trace_depth = max(1, min(trace_depth, 100))  # Clamp between 1 and 100
        except (ValueError, TypeError):
            trace_depth = 20  # Default fallback
        
        logger.info(f'Starting trace for TXID: {txid}, VOUT: {vout}, Depth: {trace_depth}, Circular Detection: {enable_circular_detection}')
        emit('status', {'message': f'Starting trace for {txid}:{vout} (depth: {trace_depth})'})
        
        # Counter for traced transactions
        trace_count = 0
        all_addresses = set()
        circular_patterns = []
        
        try:
            for step in get_utxo_history(txid, vout, max_depth=trace_depth, enable_circular_detection=enable_circular_detection):
                
                # Handle different types of events from the enhanced tracer
                if isinstance(step, dict) and step.get('type'):
                    step_type = step['type']
                    
                    if step_type == 'circular_pattern_detected':
                        # Handle circular pattern detection
                        circular_patterns.append(step)
                        logger.info(f'Circular pattern detected: {step["cycle_id"]} (risk: {step["risk_score"]:.2f})')
                        
                        # Emit circular pattern event
                        emit('circular_pattern_detected', {
                            'cycle_id': step['cycle_id'],
                            'cycle_length': step['cycle_length'],
                            'risk_score': step['risk_score'],
                            'pattern_type': step['pattern_type'],
                            'confidence': step['confidence'],
                            'total_value': step['total_value'],
                            'addresses_involved': step['addresses_involved'],
                            'transactions': step['transactions']
                        })
                        continue
                    
                    elif step_type == 'circular_analysis_complete':
                        # Handle final circular analysis
                        analysis = step['analysis']
                        all_addresses.update(step.get('all_addresses', []))
                        
                        logger.info(f'Circular analysis complete: {analysis["total_cycles"]} cycles detected')
                        
                        # Emit final analysis
                        emit('circular_analysis_complete', {
                            'analysis': analysis,
                            'all_addresses': list(all_addresses),
                            'total_transactions': step.get('total_transactions', trace_count)
                        })
                        continue
                    
                    elif step_type == 'trace_complete':
                        # Handle regular trace completion
                        all_addresses.update(step.get('all_addresses', []))
                        
                        # Emit address collection
                        emit('addresses_collected', {
                            'all_addresses': list(all_addresses),
                            'total_transactions': step.get('total_transactions', trace_count)
                        })
                        continue
                
                # Handle regular transaction steps
                if isinstance(step, dict) and 'txid' in step:
                    trace_count += 1
                    logger.info(f'Traced step {trace_count}: {step.get("txid", "unknown")}:{step.get("vout", "unknown")}')
                    
                    # Collect addresses
                    if step.get('addresses'):
                        all_addresses.update(step['addresses'])
                    
                    # Add trace metadata
                    step_with_metadata = {
                        **step,
                        'trace_index': trace_count,
                        'timestamp': None  # Could be enhanced to include block timestamp
                    }
                    
                    emit('trace_update', step_with_metadata)
                    
                    # Emit address updates for real-time collection
                    if step.get('addresses'):
                        emit('addresses_update', {
                            'addresses': step['addresses'],
                            'txid': step['txid'],
                            'vout': step['vout'],
                            'depth': step.get('depth', 0),
                            'is_circular': step.get('is_circular', False),
                            'circular_risk': step.get('circular_risk', 0.0)
                        })
                    
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
            
            # Safe error emission with connection validation
            try:
                emit('trace_error', {'message': error_message})
            except Exception as emit_error:
                logger.error(f'Failed to emit trace error: {emit_error}')
            return
        
        logger.info(f'Trace completed successfully. Total transactions traced: {trace_count}, Circular patterns: {len(circular_patterns)}')
        
        # Emit final completion event
        try:
            emit('trace_complete', {
                'total_transactions': trace_count,
                'total_addresses': len(all_addresses),
                'circular_patterns_detected': len(circular_patterns)
            })
        except Exception as emit_error:
            logger.error(f'Failed to emit trace complete: {emit_error}')
        
    except Exception as e:
        logger.error(f'Unexpected error in trace_utxo handler: {str(e)}')
        logger.error(traceback.format_exc())
        
        # Safe error emission with connection validation
        try:
            emit('trace_error', {'message': f'Unexpected server error: {str(e)}'})
        except Exception as emit_error:
            logger.error(f'Failed to emit unexpected error: {emit_error}')

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