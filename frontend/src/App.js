import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import TreeGraph from './TreeGraph';
import './App.css';

function App() {
  const [treeData, setTreeData] = useState({ nodes: [], links: [] });
  const [txid, setTxid] = useState('');
  const [vout, setVout] = useState(0);
  const [isTracing, setIsTracing] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const socketRef = useRef(null);

  // Determine backend URL - use current domain with port 5000
  const getBackendUrl = () => {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:5000';
    }
    return `http://${window.location.hostname}:5000`;
  };

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io(getBackendUrl(), {
      transports: ['websocket', 'polling']
    });

    const socket = socketRef.current;

    socket.on('connect', () => {
      console.log('Connected to backend');
      setStatus('Connected to backend');
      setError('');
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from backend');
      setStatus('Disconnected from backend');
    });

    socket.on('connect_error', (err) => {
      console.error('Connection error:', err);
      setError(`Connection failed: ${err.message}`);
      setStatus('Connection failed');
    });

    socket.on('trace_update', (step) => {
      console.log('Received trace update:', step);
      setTreeData((prev) => {
        const newNodes = [...prev.nodes, step];
        const newLinks = [...prev.links];
        
        // Create link from previous node to current node (if not the first node)
        if (prev.nodes.length > 0) {
          const lastNode = prev.nodes[prev.nodes.length - 1];
          newLinks.push({
            source: `${lastNode.txid}:${lastNode.vout}`,
            target: `${step.txid}:${step.vout}`,
            id: `${lastNode.txid}:${lastNode.vout}-${step.txid}:${step.vout}`
          });
        }
        
        return { nodes: newNodes, links: newLinks };
      });
    });

    socket.on('trace_complete', () => {
      console.log('Trace completed');
      setIsTracing(false);
      setStatus('Trace completed successfully');
    });

    socket.on('trace_error', (errorData) => {
      console.error('Trace error:', errorData);
      setError(`Trace failed: ${errorData.message || errorData}`);
      setIsTracing(false);
      setStatus('Trace failed');
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const validateTxid = (txid) => {
    // Bitcoin transaction IDs are 64 character hex strings
    const txidRegex = /^[a-fA-F0-9]{64}$/;
    return txidRegex.test(txid);
  };

  const startTrace = () => {
    if (!txid.trim()) {
      setError('Please enter a transaction ID (TXID)');
      return;
    }

    if (!validateTxid(txid.trim())) {
      setError('Invalid TXID format. TXID must be a 64-character hexadecimal string.');
      return;
    }

    if (vout < 0) {
      setError('VOUT must be a non-negative integer');
      return;
    }

    if (!socketRef.current || !socketRef.current.connected) {
      setError('Not connected to backend. Please wait for connection or refresh the page.');
      return;
    }

    // Reset state
    setTreeData({ nodes: [], links: [] });
    setError('');
    setIsTracing(true);
    setStatus('Starting trace...');

    // Emit trace request
    socketRef.current.emit('trace_utxo', {
      txid: txid.trim(),
      vout: parseInt(vout)
    });
  };

  const stopTrace = () => {
    setIsTracing(false);
    setStatus('Trace stopped by user');
  };

  const clearData = () => {
    setTreeData({ nodes: [], links: [] });
    setError('');
    setStatus('');
  };

  return (
    <div className="bitcoin-tracer">
      <div className="header">
        <h1>Bitcoin Satoshi Tracer</h1>
        <p>Trace the journey of a satoshi from any UTXO back to its origin block</p>
      </div>

      <div className="input-section">
        <div className="input-group">
          <label className="input-label">
            Transaction ID (TXID):
          </label>
          <input
            type="text"
            value={txid}
            onChange={(e) => setTxid(e.target.value)}
            placeholder="Enter Bitcoin transaction ID (64 hex characters)"
            className="input-field txid-input"
            disabled={isTracing}
          />
        </div>
        
        <div className="input-group">
          <label className="input-label">
            Output Index (VOUT):
          </label>
          <input
            type="number"
            value={vout}
            onChange={(e) => setVout(e.target.value)}
            placeholder="0"
            min="0"
            className="input-field vout-input"
            disabled={isTracing}
          />
        </div>
        
        <div className="button-group">
          {!isTracing ? (
            <button
              onClick={startTrace}
              className="btn btn-primary"
            >
              🔍 Trace UTXO
            </button>
          ) : (
            <button
              onClick={stopTrace}
              className="btn btn-danger"
            >
              ⏹️ Stop Trace
            </button>
          )}
          <button
            onClick={clearData}
            className="btn btn-secondary"
            disabled={isTracing}
          >
            🗑️ Clear Results
          </button>
        </div>
      </div>

      {/* Status and Error Display */}
      <div className="status-section">
        {status && (
          <div className="alert alert-info">
            <strong>Status:</strong> {status}
          </div>
        )}
        {error && (
          <div className="alert alert-error">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      {/* Trace Results */}
      <div className="results-section">
        <div className="results-header">
          <h2 className="results-title">Trace Results</h2>
          <div className="results-counter">
            {treeData.nodes.length} transactions found
          </div>
        </div>
        
        {isTracing && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
            <span>Tracing in progress... Found {treeData.nodes.length} transactions so far.</span>
          </div>
        )}
        
        <div className="graph-container">
          <TreeGraph data={treeData} />
        </div>
      </div>
    </div>
  );
}

export default App;