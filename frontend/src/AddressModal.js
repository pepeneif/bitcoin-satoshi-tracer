import React, { useState, useMemo } from 'react';
import './AddressModal.css';

const AddressModal = ({ 
  isOpen, 
  onClose, 
  addresses = [], 
  addressStats = {}, 
  circularData = null 
}) => {
  const [activeTab, setActiveTab] = useState('addresses');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('frequency');

  // Filter and sort addresses
  const filteredAddresses = useMemo(() => {
    let filtered = addresses.filter(addr => {
      // Search filter
      if (searchTerm && !addr.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }
      
      // Type filter
      if (filterType !== 'all') {
        const addrType = getAddressType(addr);
        if (addrType !== filterType) {
          return false;
        }
      }
      
      return true;
    });

    // Sort addresses
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'frequency':
          return (addressStats[b]?.frequency || 0) - (addressStats[a]?.frequency || 0);
        case 'risk':
          return (addressStats[b]?.risk || 0) - (addressStats[a]?.risk || 0);
        case 'depth':
          return (addressStats[a]?.first_depth || 0) - (addressStats[b]?.first_depth || 0);
        case 'alphabetical':
          return a.localeCompare(b);
        default:
          return 0;
      }
    });

    return filtered;
  }, [addresses, searchTerm, filterType, sortBy, addressStats]);

  const getAddressType = (address) => {
    if (!address) return 'unknown';
    if (address.startsWith('1')) return 'p2pkh';
    if (address.startsWith('3')) return 'p2sh';
    if (address.startsWith('bc1q')) return 'p2wpkh';
    if (address.startsWith('bc1p')) return 'p2tr';
    return 'unknown';
  };

  const getAddressTypeIcon = (type) => {
    const icons = {
      'p2pkh': '🔑',
      'p2sh': '📜',
      'p2wpkh': '⚡',
      'p2tr': '🌟',
      'unknown': '❓'
    };
    return icons[type] || '❓';
  };

  const getRiskColor = (risk) => {
    if (risk >= 0.8) return '#dc3545';  // High risk - red
    if (risk >= 0.5) return '#fd7e14';  // Medium risk - orange
    if (risk >= 0.3) return '#ffc107';  // Low risk - yellow
    return '#28a745';  // Very low risk - green
  };

  const copyAddress = async (address) => {
    try {
      await navigator.clipboard.writeText(address);
      // Show brief feedback
      const button = document.activeElement;
      if (button) {
        const originalText = button.textContent;
        button.textContent = '✓ Copied!';
        button.style.backgroundColor = '#28a745';
        setTimeout(() => {
          button.textContent = originalText;
          button.style.backgroundColor = '';
        }, 1500);
      }
    } catch (err) {
      console.error('Failed to copy address:', err);
      alert('Failed to copy address to clipboard');
    }
  };

  const exportAddresses = (format) => {
    let content = '';
    let filename = '';
    let mimeType = '';

    const exportData = filteredAddresses.map(addr => ({
      address: addr,
      type: getAddressType(addr),
      frequency: addressStats[addr]?.frequency || 1,
      risk: addressStats[addr]?.risk || 0,
      first_depth: addressStats[addr]?.first_depth || 0,
      is_circular: addressStats[addr]?.is_circular || false
    }));

    switch (format) {
      case 'csv':
        content = 'Address,Type,Frequency,Risk Score,First Depth,Circular\n';
        content += exportData.map(item => 
          `"${item.address}","${item.type}",${item.frequency},${item.risk.toFixed(3)},${item.first_depth},${item.is_circular}`
        ).join('\n');
        filename = 'bitcoin_addresses.csv';
        mimeType = 'text/csv';
        break;

      case 'json':
        content = JSON.stringify(exportData, null, 2);
        filename = 'bitcoin_addresses.json';
        mimeType = 'application/json';
        break;

      case 'txt':
        content = exportData.map(item => item.address).join('\n');
        filename = 'bitcoin_addresses.txt';
        mimeType = 'text/plain';
        break;

      default:
        return;
    }

    // Create download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const openBlockchainExplorer = (address) => {
    const url = `https://blockstream.info/address/${address}`;
    window.open(url, '_blank');
  };

  if (!isOpen) return null;

  return (
    <div className="address-modal-overlay" onClick={onClose}>
      <div className="address-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📍 Address Analysis</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-tabs">
          <button 
            className={activeTab === 'addresses' ? 'tab-active' : 'tab'} 
            onClick={() => setActiveTab('addresses')}
          >
            📝 Addresses ({addresses.length})
          </button>
          {circularData && (
            <button 
              className={activeTab === 'circular' ? 'tab-active' : 'tab'} 
              onClick={() => setActiveTab('circular')}
            >
              🔄 Circular Analysis ({circularData.total_cycles || 0})
            </button>
          )}
          <button 
            className={activeTab === 'export' ? 'tab-active' : 'tab'} 
            onClick={() => setActiveTab('export')}
          >
            📤 Export
          </button>
        </div>

        <div className="modal-content">
          {activeTab === 'addresses' && (
            <div className="addresses-tab">
              <div className="search-controls">
                <input
                  type="text"
                  placeholder="Search addresses..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                
                <select 
                  value={filterType} 
                  onChange={(e) => setFilterType(e.target.value)}
                  className="filter-select"
                >
                  <option value="all">All Types</option>
                  <option value="p2pkh">P2PKH (Legacy)</option>
                  <option value="p2sh">P2SH (Script)</option>
                  <option value="p2wpkh">P2WPKH (SegWit)</option>
                  <option value="p2tr">P2TR (Taproot)</option>
                </select>
                
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value)}
                  className="sort-select"
                >
                  <option value="frequency">Sort by Frequency</option>
                  <option value="risk">Sort by Risk</option>
                  <option value="depth">Sort by Depth</option>
                  <option value="alphabetical">Sort Alphabetically</option>
                </select>
              </div>

              <div className="addresses-list">
                {filteredAddresses.map((address, index) => {
                  const stats = addressStats[address] || {};
                  const addressType = getAddressType(address);
                  const riskScore = stats.risk || 0;
                  
                  return (
                    <div key={index} className="address-item">
                      <div className="address-header">
                        <span className="address-type">
                          {getAddressTypeIcon(addressType)} {addressType.toUpperCase()}
                        </span>
                        {stats.is_circular && (
                          <span className="circular-badge">🔄 Circular</span>
                        )}
                        <span 
                          className="risk-badge" 
                          style={{ backgroundColor: getRiskColor(riskScore) }}
                        >
                          Risk: {(riskScore * 100).toFixed(1)}%
                        </span>
                      </div>
                      
                      <div className="address-text">
                        <code>{address}</code>
                      </div>
                      
                      <div className="address-stats">
                        <span>Frequency: {stats.frequency || 1}</span>
                        <span>First at depth: {stats.first_depth || 0}</span>
                      </div>
                      
                      <div className="address-actions">
                        <button 
                          onClick={() => copyAddress(address)}
                          className="action-button copy-button"
                        >
                          📋 Copy
                        </button>
                        <button 
                          onClick={() => openBlockchainExplorer(address)}
                          className="action-button explore-button"
                        >
                          🔍 Explore
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === 'circular' && circularData && (
            <div className="circular-tab">
              <div className="circular-summary">
                <div className="summary-grid">
                  <div className="summary-card">
                    <h4>Total Cycles</h4>
                    <div className="summary-value">{circularData.total_cycles}</div>
                  </div>
                  <div className="summary-card">
                    <h4>High Risk</h4>
                    <div className="summary-value">{circularData.high_risk_cycles}</div>
                  </div>
                  <div className="summary-card">
                    <h4>Avg Risk Score</h4>
                    <div className="summary-value">
                      {(circularData.average_risk_score * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="summary-card">
                    <h4>Total Value</h4>
                    <div className="summary-value">
                      {circularData.total_circular_value?.toFixed(8) || '0'} BTC
                    </div>
                  </div>
                </div>
              </div>

              <div className="cycles-list">
                <h4>Detected Circular Patterns</h4>
                {circularData.cycles?.map((cycle, index) => (
                  <div key={cycle.id || index} className="cycle-item">
                    <div className="cycle-header">
                      <span className="cycle-id">ID: {cycle.id}</span>
                      <span 
                        className="cycle-risk" 
                        style={{ backgroundColor: getRiskColor(cycle.risk_score) }}
                      >
                        Risk: {(cycle.risk_score * 100).toFixed(1)}%
                      </span>
                      <span className="cycle-type">{cycle.pattern_type}</span>
                    </div>
                    
                    <div className="cycle-details">
                      <span>Length: {cycle.cycle_length} transactions</span>
                      <span>Confidence: {(cycle.confidence * 100).toFixed(1)}%</span>
                      <span>Value: {cycle.total_value?.toFixed(8) || '0'} BTC</span>
                    </div>
                    
                    <div className="cycle-addresses">
                      <strong>Involved Addresses ({cycle.addresses?.length || 0}):</strong>
                      <div className="address-chips">
                        {cycle.addresses?.slice(0, 3).map((addr, i) => (
                          <span key={i} className="address-chip">
                            {addr.substring(0, 8)}...{addr.substring(addr.length - 6)}
                          </span>
                        ))}
                        {cycle.addresses?.length > 3 && (
                          <span className="address-chip more">
                            +{cycle.addresses.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'export' && (
            <div className="export-tab">
              <h4>Export Address Data</h4>
              <p>Export the collected addresses in various formats for external analysis.</p>
              
              <div className="export-options">
                <div className="export-format">
                  <h5>📊 CSV Format</h5>
                  <p>Includes address, type, frequency, risk score, and circular information</p>
                  <button 
                    onClick={() => exportAddresses('csv')}
                    className="export-button csv-button"
                  >
                    💾 Download CSV
                  </button>
                </div>
                
                <div className="export-format">
                  <h5>📋 JSON Format</h5>
                  <p>Structured data format for programmatic analysis</p>
                  <button 
                    onClick={() => exportAddresses('json')}
                    className="export-button json-button"
                  >
                    💾 Download JSON
                  </button>
                </div>
                
                <div className="export-format">
                  <h5>📝 Text Format</h5>
                  <p>Simple list of addresses, one per line</p>
                  <button 
                    onClick={() => exportAddresses('txt')}
                    className="export-button txt-button"
                  >
                    💾 Download TXT
                  </button>
                </div>
              </div>
              
              <div className="export-stats">
                <h5>Export Summary</h5>
                <ul>
                  <li>Total Addresses: {addresses.length}</li>
                  <li>Filtered Addresses: {filteredAddresses.length}</li>
                  <li>Address Types: {new Set(addresses.map(getAddressType)).size}</li>
                  <li>High Risk Addresses: {addresses.filter(addr => (addressStats[addr]?.risk || 0) > 0.7).length}</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AddressModal;