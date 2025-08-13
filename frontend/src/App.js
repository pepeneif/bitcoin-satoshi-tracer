import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import TreeGraph from './TreeGraph';
import AddressModal from './AddressModal';
import './App.css';

function App() {
  const [treeData, setTreeData] = useState({ nodes: [], links: [] });
  const [txid, setTxid] = useState('');
  const [vout, setVout] = useState(0);
  const [traceDepth, setTraceDepth] = useState(20);
  const [enableCircularDetection, setEnableCircularDetection] = useState(true);
  const [isTracing, setIsTracing] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const socketRef = useRef(null);
  
  // Address collection and management
  const [allAddresses, setAllAddresses] = useState(new Set());
  const [addressStats, setAddressStats] = useState({});
  const [showAddressModal, setShowAddressModal] = useState(false);
  
  // Circular transaction detection
  const [circularPatterns, setCircularPatterns] = useState([]);
  const [circularAnalysis, setCircularAnalysis] = useState(null);
  const [circularAlerts, setCircularAlerts] = useState([]);

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

    // New socket event handlers for enhanced features
    socket.on('addresses_update', (data) => {
      console.log('Received address update:', data);
      if (data.addresses && Array.isArray(data.addresses)) {
        setAllAddresses(prev => {
          const newSet = new Set(prev);
          data.addresses.forEach(addr => newSet.add(addr));
          return newSet;
        });

        // Update address statistics
        setAddressStats(prev => {
          const updated = { ...prev };
          data.addresses.forEach(addr => {
            if (!updated[addr]) {
              updated[addr] = {
                frequency: 1,
                first_depth: data.depth || 0,
                is_circular: data.is_circular || false,
                risk: data.circular_risk || 0
              };
            } else {
              updated[addr].frequency += 1;
              updated[addr].is_circular = updated[addr].is_circular || data.is_circular;
              updated[addr].risk = Math.max(updated[addr].risk, data.circular_risk || 0);
            }
          });
          return updated;
        });
      }
    });

    socket.on('circular_pattern_detected', (data) => {
      console.log('Circular pattern detected:', data);
      setCircularPatterns(prev => [...prev, data]);
      
      // Add to alerts
      setCircularAlerts(prev => [...prev, {
        id: data.cycle_id,
        message: `Circular pattern detected: ${data.pattern_type} (Risk: ${(data.risk_score * 100).toFixed(1)}%)`,
        risk: data.risk_score,
        timestamp: Date.now()
      }]);
    });

    socket.on('circular_analysis_complete', (data) => {
      console.log('Circular analysis complete:', data);
      setCircularAnalysis(data.analysis);
      
      if (data.all_addresses) {
        setAllAddresses(new Set(data.all_addresses));
      }
    });

    socket.on('addresses_collected', (data) => {
      console.log('Final address collection:', data);
      if (data.all_addresses) {
        setAllAddresses(new Set(data.all_addresses));
      }
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

    if (traceDepth < 1 || traceDepth > 100) {
      setError('Trace depth must be between 1 and 100 transactions');
      return;
    }

    if (!socketRef.current || !socketRef.current.connected) {
      setError('Not connected to backend. Please wait for connection or refresh the page.');
      return;
    }

    // Reset all state
    setTreeData({ nodes: [], links: [] });
    setAllAddresses(new Set());
    setAddressStats({});
    setCircularPatterns([]);
    setCircularAnalysis(null);
    setCircularAlerts([]);
    setError('');
    setIsTracing(true);
    setStatus(`Starting trace (depth: ${traceDepth}, circular detection: ${enableCircularDetection ? 'enabled' : 'disabled'})...`);

    // Emit enhanced trace request
    socketRef.current.emit('trace_utxo', {
      txid: txid.trim(),
      vout: parseInt(vout),
      trace_depth: parseInt(traceDepth),
      enable_circular_detection: enableCircularDetection
    });
  };

  const stopTrace = () => {
    setIsTracing(false);
    setStatus('Trace stopped by user');
  };

  const clearData = () => {
    setTreeData({ nodes: [], links: [] });
    setAllAddresses(new Set());
    setAddressStats({});
    setCircularPatterns([]);
    setCircularAnalysis(null);
    setCircularAlerts([]);
    setError('');
    setStatus('');
  };

  const dismissAlert = (alertId) => {
    setCircularAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  return (
    <div className="bitcoin-tracer">
      <div className="header">
        <h1>Bitcoin Satoshi Tracer</h1>
        <p>Trace the journey of a satoshi from any UTXO back to its origin block</p>
      </div>

      <div className="input-section">
        <div className="input-row">
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
        </div>

        <div className="input-row">
          <div className="input-group">
            <label className="input-label">
              Trace Depth: {traceDepth} transactions
            </label>
            <div className="slider-container">
              <input
                type="range"
                min="1"
                max="100"
                value={traceDepth}
                onChange={(e) => setTraceDepth(e.target.value)}
                className="depth-slider"
                disabled={isTracing}
              />
              <div className="slider-labels">
                <span>1</span>
                <span>20 (default)</span>
                <span>100</span>
              </div>
            </div>
          </div>

          <div className="input-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={enableCircularDetection}
                onChange={(e) => setEnableCircularDetection(e.target.checked)}
                disabled={isTracing}
              />
              🔄 Enable Circular Transaction Detection
            </label>
          </div>
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
          <button
            onClick={() => setShowAddressModal(true)}
            className="btn btn-info"
            disabled={allAddresses.size === 0}
          >
            📍 View Addresses ({allAddresses.size})
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

      {/* Circular Pattern Alerts */}
      {circularAlerts.length > 0 && (
        <div className="alerts-section">
          {circularAlerts.map((alert, index) => (
            <div
              key={alert.id || index}
              className={`alert alert-circular ${alert.risk > 0.7 ? 'high-risk' : alert.risk > 0.4 ? 'medium-risk' : 'low-risk'}`}
            >
              <span className="alert-icon">⚠️</span>
              <span className="alert-message">{alert.message}</span>
              <button
                className="alert-dismiss"
                onClick={() => dismissAlert(alert.id)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Trace Results */}
      <div className="results-section">
        <div className="results-header">
          <h2 className="results-title">Trace Results</h2>
          <div className="results-stats">
            <div className="stat-item">
              <span className="stat-label">Transactions:</span>
              <span className="stat-value">{treeData.nodes.length}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Addresses:</span>
              <span className="stat-value">{allAddresses.size}</span>
            </div>
            {circularPatterns.length > 0 && (
              <div className="stat-item circular-stat">
                <span className="stat-label">🔄 Circular Patterns:</span>
                <span className="stat-value">{circularPatterns.length}</span>
              </div>
            )}
          </div>
        </div>
        
        {isTracing && (
          <div className="loading-indicator">
            <div className="loading-spinner"></div>
            <span>
              Tracing in progress... Found {treeData.nodes.length} transactions, {allAddresses.size} addresses
              {circularPatterns.length > 0 && `, ${circularPatterns.length} circular patterns`}
            </span>
          </div>
        )}
        
        <div className="graph-container">
          <TreeGraph
            data={treeData}
            circularPatterns={circularPatterns}
            addressStats={addressStats}
          />
        </div>
      </div>

      {/* Address Modal */}
      <AddressModal
        isOpen={showAddressModal}
        onClose={() => setShowAddressModal(false)}
        addresses={Array.from(allAddresses)}
        addressStats={addressStats}
        circularData={circularAnalysis}
      />
    </div>
  );
}

export default App;