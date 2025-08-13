import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

export default function TreeGraph({ data, circularPatterns = [], addressStats = {} }) {
  const svgRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });
  const [highlightedCycle, setHighlightedCycle] = useState(null);

  useEffect(() => {
    if (!data.nodes || data.nodes.length === 0) {
      // Clear the SVG when there's no data
      const svg = d3.select(svgRef.current);
      svg.selectAll('*').remove();
      return;
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const { width, height } = dimensions;
    const margin = { top: 40, right: 40, bottom: 40, left: 40 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create main group element
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Helper function to get risk color
    const getRiskColor = (riskScore) => {
      if (riskScore >= 0.8) return '#dc3545';  // High risk - red
      if (riskScore >= 0.5) return '#fd7e14';  // Medium risk - orange
      if (riskScore >= 0.3) return '#ffc107';  // Low risk - yellow
      return '#28a745';  // Very low risk - green
    };

    // Helper function to check if node is in any circular pattern
    const getNodeCircularInfo = (nodeId) => {
      for (const pattern of circularPatterns) {
        const isInPattern = pattern.transactions?.some(tx =>
          `${tx.txid}:${tx.vout}` === nodeId
        );
        if (isInPattern) {
          return {
            isCircular: true,
            riskScore: pattern.risk_score || 0,
            cycleId: pattern.cycle_id,
            patternType: pattern.pattern_type
          };
        }
      }
      return { isCircular: false, riskScore: 0 };
    };

    // Prepare data for D3
    const nodes = data.nodes.map((node, index) => {
      const nodeId = `${node.txid}:${node.vout}`;
      const circularInfo = getNodeCircularInfo(nodeId);
      
      return {
        id: nodeId,
        txid: node.txid,
        vout: node.vout,
        addresses: node.addresses || [],
        index: index,
        x: 0,
        y: 0,
        // Enhanced properties
        isCircular: circularInfo.isCircular || node.is_circular || false,
        circularRisk: circularInfo.riskScore || node.circular_risk || 0,
        cycleId: circularInfo.cycleId || node.cycle_id,
        patternType: circularInfo.patternType,
        depth: node.depth || 0
      };
    });

    const links = data.links.map(link => ({
      source: link.source,
      target: link.target,
      id: link.id
    }));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(innerWidth / 2, innerHeight / 2))
      .force('collision', d3.forceCollide().radius(40));

    // Create links
    const linkElements = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6);

    // Create nodes
    const nodeElements = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer');

    // Add circles for nodes with enhanced styling
    nodeElements.append('circle')
      .attr('r', (d) => d.isCircular ? 30 : 25)  // Larger for circular nodes
      .attr('fill', (d, i) => {
        if (d.isCircular && d.circularRisk > 0) {
          return getRiskColor(d.circularRisk);
        }
        // Default color scheme based on depth
        const depthColors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'];
        return depthColors[d.depth % depthColors.length] || depthColors[i % depthColors.length];
      })
      .attr('stroke', (d) => {
        if (d.isCircular) {
          return d.circularRisk > 0.7 ? '#dc3545' : '#ffc107';  // Red or yellow border for circular
        }
        return '#fff';
      })
      .attr('stroke-width', (d) => d.isCircular ? 3 : 2)
      .style('filter', (d) => {
        if (d.isCircular && d.circularRisk > 0.7) {
          return 'drop-shadow(0px 0px 6px rgba(220, 53, 69, 0.6))';  // Glow effect for high risk
        }
        return null;
      });

    // Add circular pattern indicator
    nodeElements.filter(d => d.isCircular)
      .append('circle')
      .attr('r', 35)
      .attr('fill', 'none')
      .attr('stroke', '#ff6b6b')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,5')
      .style('opacity', 0.7)
      .append('animateTransform')
      .attr('attributeName', 'transform')
      .attr('attributeType', 'XML')
      .attr('type', 'rotate')
      .attr('from', '0 0 0')
      .attr('to', '360 0 0')
      .attr('dur', '3s')
      .attr('repeatCount', 'indefinite');

    // Add VOUT text inside circles
    nodeElements.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .attr('fill', 'white')
      .text(d => d.vout);

    // Add TXID labels below nodes
    nodeElements.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '45px')
      .attr('font-size', '10px')
      .attr('font-family', 'monospace')
      .attr('fill', '#333')
      .text(d => `${d.txid.substring(0, 8)}...${d.txid.substring(56)}`);

    // Add addresses below TXID (if available)
    nodeElements.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '60px')
      .attr('font-size', '9px')
      .attr('fill', '#666')
      .text(d => {
        if (d.addresses && d.addresses.length > 0) {
          const addr = d.addresses[0];
          return addr.length > 20 ? `${addr.substring(0, 10)}...${addr.substring(addr.length - 8)}` : addr;
        }
        return '';
      });

    // Add tooltips
    const tooltip = d3.select('body').append('div')
      .attr('class', 'tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('color', 'white')
      .style('padding', '10px')
      .style('border-radius', '5px')
      .style('font-size', '12px')
      .style('font-family', 'monospace')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', 1000);

    nodeElements
      .on('mouseover', function(event, d) {
        // Highlight connected links
        linkElements
          .style('stroke', link =>
            (link.source.id === d.id || link.target.id === d.id) ? '#ff0000' : '#999'
          )
          .style('stroke-width', link =>
            (link.source.id === d.id || link.target.id === d.id) ? 3 : 2
          );

        // Highlight circular pattern if applicable
        if (d.isCircular && d.cycleId) {
          setHighlightedCycle(d.cycleId);
          // Highlight all nodes in the same cycle
          nodeElements.selectAll('circle')
            .style('opacity', node => {
              return node.cycleId === d.cycleId ? 1 : 0.3;
            });
        }

        // Enhanced tooltip with circular information
        let tooltipContent = `<div style="max-width: 300px;">`;
        tooltipContent += `<strong>TXID:</strong> ${d.txid}<br/>`;
        tooltipContent += `<strong>VOUT:</strong> ${d.vout}<br/>`;
        tooltipContent += `<strong>Depth:</strong> ${d.depth}<br/>`;
        
        if (d.isCircular) {
          tooltipContent += `<hr style="margin: 8px 0; border: 1px solid #ffc107;">`;
          tooltipContent += `<strong>🔄 Circular Transaction</strong><br/>`;
          tooltipContent += `<strong>Risk Score:</strong> ${(d.circularRisk * 100).toFixed(1)}%<br/>`;
          if (d.patternType) {
            tooltipContent += `<strong>Pattern:</strong> ${d.patternType.replace(/_/g, ' ')}<br/>`;
          }
          if (d.cycleId) {
            tooltipContent += `<strong>Cycle ID:</strong> ${d.cycleId}<br/>`;
          }
        }
        
        if (d.addresses && d.addresses.length > 0) {
          tooltipContent += `<hr style="margin: 8px 0;">`;
          tooltipContent += `<strong>Addresses (${d.addresses.length}):</strong><br/>`;
          d.addresses.slice(0, 3).forEach(addr => {
            const stats = addressStats[addr];
            const riskIndicator = stats?.risk > 0.7 ? '🔴' : stats?.risk > 0.4 ? '🟡' : '🟢';
            tooltipContent += `${riskIndicator} ${addr}<br/>`;
          });
          if (d.addresses.length > 3) {
            tooltipContent += `<em>... and ${d.addresses.length - 3} more</em><br/>`;
          }
        }
        
        tooltipContent += `</div>`;

        tooltip.transition()
          .duration(200)
          .style('opacity', 0.9);
        tooltip.html(tooltipContent)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 28) + 'px');
      })
      .on('mouseout', function() {
        // Reset link highlighting
        linkElements
          .style('stroke', '#999')
          .style('stroke-width', 2);

        // Reset node highlighting
        nodeElements.selectAll('circle')
          .style('opacity', 1);

        setHighlightedCycle(null);

        // Hide tooltip
        tooltip.transition()
          .duration(500)
          .style('opacity', 0);
      })
      .on('click', function(event, d) {
        // Copy TXID to clipboard on click
        navigator.clipboard.writeText(d.txid).then(() => {
          console.log('TXID copied to clipboard:', d.txid);
          
          // Show brief feedback
          const feedback = d3.select('body').append('div')
            .style('position', 'absolute')
            .style('background', '#4CAF50')
            .style('color', 'white')
            .style('padding', '5px 10px')
            .style('border-radius', '3px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', 1001)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 30) + 'px')
            .text('TXID copied!');
            
          feedback.transition()
            .duration(1500)
            .style('opacity', 0)
            .remove();
        }).catch(err => {
          console.error('Failed to copy TXID:', err);
        });
      });

    // Add drag behavior
    const drag = d3.drag()
      .on('start', function(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', function(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', function(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    nodeElements.call(drag);

    // Update positions on each tick
    simulation.on('tick', () => {
      linkElements
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      nodeElements
        .attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Clean up tooltip on unmount
    return () => {
      tooltip.remove();
    };

  }, [data, dimensions]);

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      const container = svgRef.current?.parentElement;
      if (container) {
        setDimensions({
          width: Math.max(800, container.clientWidth - 40),
          height: Math.max(600, window.innerHeight * 0.6)
        });
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Initial call

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!data.nodes || data.nodes.length === 0) {
    return (
      <div className="empty-state">
        <h3>🔍 No trace data available</h3>
        <p>Enter a Bitcoin transaction ID (TXID) and output index (VOUT) above, then click "Trace UTXO" to begin exploring the satoshi journey.</p>
      </div>
    );
  }

  // Function to highlight a specific circular pattern
  const highlightCircularPattern = (cycleId) => {
    if (!svgRef.current) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll('.node circle')
      .style('opacity', d => d.cycleId === cycleId ? 1 : 0.3);
    
    setHighlightedCycle(cycleId);
    
    // Auto-reset after 3 seconds
    setTimeout(() => {
      svg.selectAll('.node circle').style('opacity', 1);
      setHighlightedCycle(null);
    }, 3000);
  };

  return (
    <div style={{ width: '100%', overflow: 'hidden' }}>
      {/* Enhanced instructions with circular pattern info */}
      <div className="instructions">
        <strong>Interactive Controls:</strong> Drag nodes to reposition • Hover for transaction details • Click to copy TXID • Scroll to zoom in/out
        {circularPatterns.length > 0 && (
          <>
            <br/>
            <strong>🔄 Circular Patterns:</strong>
            <span style={{ color: '#dc3545' }}>● High Risk</span> •
            <span style={{ color: '#fd7e14' }}>● Medium Risk</span> •
            <span style={{ color: '#ffc107' }}>● Low Risk</span>
            {circularPatterns.length > 0 && (
              <span> • {circularPatterns.length} pattern{circularPatterns.length !== 1 ? 's' : ''} detected</span>
            )}
          </>
        )}
      </div>
      
      {/* Circular patterns legend/controls */}
      {circularPatterns.length > 0 && (
        <div style={{
          background: '#f8f9fa',
          border: '1px solid #dee2e6',
          borderRadius: '6px',
          padding: '10px',
          marginBottom: '10px',
          fontSize: '12px'
        }}>
          <strong>Detected Circular Patterns:</strong>
          <div style={{ display: 'flex', gap: '10px', marginTop: '5px', flexWrap: 'wrap' }}>
            {circularPatterns.slice(0, 5).map((pattern, index) => (
              <button
                key={pattern.cycle_id || index}
                onClick={() => highlightCircularPattern(pattern.cycle_id)}
                style={{
                  background: getRiskColor(pattern.risk_score || 0),
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '11px',
                  cursor: 'pointer',
                  opacity: highlightedCycle === pattern.cycle_id ? 1 : 0.8
                }}
                title={`${pattern.pattern_type || 'Unknown'} - Risk: ${((pattern.risk_score || 0) * 100).toFixed(1)}%`}
              >
                {pattern.cycle_id?.substring(0, 8) || `Pattern ${index + 1}`}
              </button>
            ))}
            {circularPatterns.length > 5 && (
              <span style={{ color: '#6c757d', alignSelf: 'center' }}>
                +{circularPatterns.length - 5} more
              </span>
            )}
          </div>
        </div>
      )}

      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        style={{
          border: '1px solid #ddd',
          borderRadius: '8px',
          backgroundColor: '#fdfdfd'
        }}
      />
    </div>
  );
}