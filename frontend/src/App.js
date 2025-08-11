import React, { useState } from 'react';
import io from 'socket.io-client';
import TreeGraph from './TreeGraph';

const socket = io('http://localhost:5000');

function App() {
  const [treeData, setTreeData] = useState({ nodes: [], links: [] });

  const startTrace = () => {
    socket.emit('trace_utxo', { txid: 'your-txid', vout: 0 });
  };

  socket.on('trace_update', (step) => {
    setTreeData((prev) => ({
      nodes: [...prev.nodes, step],
      links: [...prev.links]
    }));
  });

  return (
    <div>
      <button onClick={startTrace}>Trace UTXO</button>
      <TreeGraph data={treeData} />
    </div>
  );
}

export default App;