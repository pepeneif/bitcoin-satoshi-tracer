import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

export default function TreeGraph({ data }) {
  const svgRef = useRef();
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });

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

    // Prepare data for D3
    const nodes = data.nodes.map((node, index) => ({
      id: `${node.txid}:${node.vout}`,
      txid: node.txid,
      vout: node.vout,
      addresses: node.addresses || [],
      index: index,
      x: 0,
      y: 0
    }));

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

    // Add circles for nodes
    nodeElements.append('circle')
      .attr('r', 25)
      .attr('fill', (d, i) => {
        // Color nodes based on their position in the trace
        const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'];
        return colors[i % colors.length];
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

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

        // Show tooltip
        let tooltipContent = `<strong>TXID:</strong> ${d.txid}<br/>`;
        tooltipContent += `<strong>VOUT:</strong> ${d.vout}<br/>`;
        if (d.addresses && d.addresses.length > 0) {
          tooltipContent += `<strong>Addresses:</strong><br/>`;
          d.addresses.forEach(addr => {
            tooltipContent += `${addr}<br/>`;
          });
        }

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

  return (
    <div style={{ width: '100%', overflow: 'hidden' }}>
      <div className="instructions">
        <strong>Interactive Controls:</strong> Drag nodes to reposition • Hover for transaction details • Click to copy TXID • Scroll to zoom in/out
      </div>
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