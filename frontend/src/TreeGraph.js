import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function TreeGraph({ data }) {
  const ref = useRef();

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll('*').remove();
    // D3 rendering logic here
  }, [data]);

  return <svg ref={ref} width={800} height={600}></svg>;
}