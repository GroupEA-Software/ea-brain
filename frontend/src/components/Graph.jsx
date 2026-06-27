import React, { useEffect, useRef, useCallback, useState } from 'react';
import { getGraph } from '../api';
import '../styles/graph.css';

const DEFAULTS = { repulsion: 10000, attraction: 0.002, damping: 0.85, centering: 0.006 };

export default function Graph() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const stateRef = useRef({
    nodes: [], edges: [], physics: [],
    dragNode: null, isDragging: false, dragOffX: 0, dragOffY: 0,
    viewX: 0, viewY: 0, scale: 1, hoverNode: null, animFrame: null, time: 0,
  });
  const [info, setInfo] = useState({ nodes: 0, edges: 0 });
  const [params, setParams] = useState(DEFAULTS);
  const [showControls, setShowControls] = useState(false);
  const paramsRef = useRef(DEFAULTS);

  const updateParam = (key, val) => {
    const v = parseFloat(val);
    setParams(p => ({ ...p, [key]: v }));
    paramsRef.current[key] = v;
  };

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
  }, []);

  const renderGraph = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const s = stateRef.current;
    const { physics: pts, edges, viewX, viewY, scale, hoverNode, time } = s;
    const w = canvas.width, h = canvas.height;
    if (!w || !h) return;

    ctx.clearRect(0, 0, w, h);

    const darkBg = '#0a0a1a';
    ctx.fillStyle = darkBg;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(viewX, viewY);
    ctx.scale(scale, scale);

    const connectedSet = new Set();
    if (hoverNode) {
      edges.forEach(e => {
        if (e.source === hoverNode.id || e.target === hoverNode.id) {
          connectedSet.add(e.source);
          connectedSet.add(e.target);
        }
      });
    }

    for (const edge of edges) {
      const src = pts.find(n => n.id === edge.source);
      const tgt = pts.find(n => n.id === edge.target);
      if (!src || !tgt) continue;

      const weight = edge.weight || 0.3;
      const hl = hoverNode && connectedSet.has(edge.source) && connectedSet.has(edge.target);
      const alpha = hl ? 0.6 : (0.08 + weight * 0.5);
      const glowSize = hl ? 18 + weight * 12 : 6 + weight * 10;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);

      const gradient = ctx.createLinearGradient(src.x, src.y, tgt.x, tgt.y);
      gradient.addColorStop(0, `rgba(120, 80, 255, ${alpha})`);
      gradient.addColorStop(0.5, `rgba(0, 200, 255, ${alpha})`);
      gradient.addColorStop(1, `rgba(120, 80, 255, ${alpha})`);
      ctx.strokeStyle = gradient;

      ctx.shadowColor = `rgba(0, 200, 255, ${alpha * 0.6})`;
      ctx.shadowBlur = glowSize;
      ctx.lineWidth = hl ? 2.5 : (0.5 + weight * 1.5);
      ctx.stroke();

      ctx.shadowBlur = 0;
      ctx.restore();
    }

    for (const node of pts) {
      const isHover = hoverNode && hoverNode.id === node.id;
      const isConnected = hoverNode && connectedSet.has(node.id);
      const baseR = node.r;
      const pulse = isHover ? 0 : Math.sin(time * 0.002 + node.x * 0.01) * 1.5;
      const r = (isHover ? baseR * 1.6 : baseR) + pulse;

      const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 2.5);
      if (isHover) {
        gradient.addColorStop(0, 'rgba(0, 220, 255, 0.95)');
        gradient.addColorStop(0.3, 'rgba(0, 180, 255, 0.6)');
        gradient.addColorStop(1, 'rgba(0, 100, 255, 0)');
      } else if (isConnected) {
        gradient.addColorStop(0, 'rgba(168, 85, 247, 0.85)');
        gradient.addColorStop(0.3, 'rgba(120, 50, 220, 0.5)');
        gradient.addColorStop(1, 'rgba(80, 30, 180, 0)');
      } else {
        gradient.addColorStop(0, 'rgba(180, 180, 220, 0.7)');
        gradient.addColorStop(0.3, 'rgba(120, 120, 180, 0.3)');
        gradient.addColorStop(1, 'rgba(60, 60, 120, 0)');
      }

      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.shadowColor = isHover ? '#00d4ff' : (isConnected ? '#a855f7' : 'rgba(150, 150, 200, 0.3)');
      ctx.shadowBlur = isHover ? 30 : (isConnected ? 18 : 8);
      ctx.fill();

      ctx.shadowBlur = 0;

      if (isHover || scale > 0.35) {
        ctx.fillStyle = isHover ? '#fff' : 'rgba(200, 200, 230, 0.8)';
        ctx.font = `${Math.max(9, 11)}px 'Space Grotesk', sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(node.label.length > 28 ? node.label.slice(0, 28) + '\u2026' : node.label,
          node.x, node.y + r + 16);
      }
    }

    ctx.restore();
  }, []);

  const runPhysics = useCallback(() => {
    const s = stateRef.current;
    const pts = s.physics;
    if (!pts.length) return;
    const p = paramsRef.current;
    const rep = p.repulsion, attr = p.attraction, damp = p.damping, centerF = p.centering;
    const canvas = canvasRef.current;
    const w = canvas?.width || 800, h = canvas?.height || 600;

    for (let i = 0; i < pts.length; i++) {
      let fx = 0, fy = 0;
      const a = pts[i];
      fx += (w / 2 - a.x) * centerF * (a.hasEdges ? 1 : 0.3);
      fy += (h / 2 - a.y) * centerF * (a.hasEdges ? 1 : 0.3);

      for (let j = i + 1; j < pts.length; j++) {
        const b = pts[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = rep / (dist * dist + 50);
        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
      }

      for (const edge of s.edges) {
        const si = pts.findIndex(n => n.id === edge.source);
        const ti = pts.findIndex(n => n.id === edge.target);
        if (si === i && ti >= 0) {
          fx += (pts[ti].x - a.x) * attr;
          fy += (pts[ti].y - a.y) * attr;
        }
        if (ti === i && si >= 0) {
          fx += (pts[si].x - a.x) * attr;
          fy += (pts[si].y - a.y) * attr;
        }
      }

      a.vx = (a.vx + fx) * damp;
      a.vy = (a.vy + fy) * damp;
      a.x += a.vx;
      a.y += a.vy;
    }
  }, []);

  const gameLoop = useCallback(() => {
    const s = stateRef.current;
    runPhysics();
    renderGraph();
    s.time += 16;
    s.animFrame = requestAnimationFrame(gameLoop);
  }, [runPhysics, renderGraph]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await getGraph();
        const s = stateRef.current;
        s.nodes = data.nodes || [];
        s.edges = data.edges || [];

        resizeCanvas();
        const canvas = canvasRef.current;
        const w = canvas?.width || 800, h = canvas?.height || 600;

        const connected = new Set();
        s.edges.forEach(e => { connected.add(e.source); connected.add(e.target); });

        s.physics = s.nodes.map(n => {
          const hasEdges = connected.has(n.id);
          return {
            id: n.id, label: n.label || n.id,
            x: w / 2 + (hasEdges ? (Math.random() - 0.5) * w * 0.3 : (Math.random() - 0.5) * w * 0.6),
            y: h / 2 + (hasEdges ? (Math.random() - 0.5) * h * 0.3 : (Math.random() - 0.5) * h * 0.6),
            vx: 0, vy: 0,
            r: Math.max(5, Math.min(14, (n.size || 1) * 3)),
            hasEdges,
          };
        });

        setInfo({ nodes: s.nodes.length, edges: s.edges.length });
        if (s.animFrame) cancelAnimationFrame(s.animFrame);
        s.time = 0;
        gameLoop();
      } catch (_) {}
    };

    const onShow = () => { resizeCanvas(); };
    window.addEventListener('graph-show', onShow);
    loadData();

    return () => {
      window.removeEventListener('graph-show', onShow);
      if (stateRef.current.animFrame) cancelAnimationFrame(stateRef.current.animFrame);
    };
  }, [resizeCanvas, gameLoop]);

  useEffect(() => { resizeCanvas(); }, [resizeCanvas]);

  const getMousePos = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { mx: 0, my: 0 };
    const rect = canvas.getBoundingClientRect();
    const s = stateRef.current;
    return {
      mx: (e.clientX - rect.left - s.viewX) / s.scale,
      my: (e.clientY - rect.top - s.viewY) / s.scale,
    };
  };

  const handleMouseDown = (e) => {
    const s = stateRef.current;
    const { mx, my } = getMousePos(e);
    for (const node of s.physics) {
      const dx = mx - node.x, dy = my - node.y;
      if (dx * dx + dy * dy < (node.r * 2) * (node.r * 2)) {
        s.dragNode = node;
        s.isDragging = true;
        s.dragOffX = node.x - mx;
        s.dragOffY = node.y - my;
        return;
      }
    }
    s.isDragging = true;
    s.dragOffX = e.clientX - s.viewX;
    s.dragOffY = e.clientY - s.viewY;
  };

  const handleMouseMove = (e) => {
    const s = stateRef.current;
    const { mx, my } = getMousePos(e);
    let found = null;
    for (const node of s.physics) {
      const dx = mx - node.x, dy = my - node.y;
      if (dx * dx + dy * dy < (node.r * 3) * (node.r * 3)) { found = node; break; }
    }
    s.hoverNode = found;
    const canvas = canvasRef.current;
    if (canvas) canvas.style.cursor = found ? 'pointer' : 'grab';
    if (s.isDragging && s.dragNode) {
      s.dragNode.x = mx + s.dragOffX;
      s.dragNode.y = my + s.dragOffY;
    } else if (s.isDragging && !s.dragNode) {
      s.viewX = e.clientX - s.dragOffX;
      s.viewY = e.clientY - s.dragOffY;
    }
  };

  const handleMouseUp = () => {
    const s = stateRef.current;
    s.isDragging = false;
    s.dragNode = null;
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const s = stateRef.current;
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    s.scale = Math.max(0.2, Math.min(4, s.scale * delta));
  };

  const touchRef = useRef({ dist: 0, lastX: 0, lastY: 0, singleId: null });
  const handleTouchStart = (e) => {
    if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      touchRef.current.dist = Math.sqrt(dx * dx + dy * dy);
      touchRef.current.singleId = null;
    } else if (e.touches.length === 1) {
      const s = stateRef.current;
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const mx = (e.touches[0].clientX - rect.left - s.viewX) / s.scale;
      const my = (e.touches[0].clientY - rect.top - s.viewY) / s.scale;
      let hitNode = null;
      for (const node of s.physics) {
        const dx = mx - node.x, dy = my - node.y;
        if (dx * dx + dy * dy < (node.r * 2) * (node.r * 2)) { hitNode = node; break; }
      }
      if (hitNode) {
        s.dragNode = hitNode;
        s.isDragging = true;
        s.dragOffX = hitNode.x - mx;
        s.dragOffY = hitNode.y - my;
      } else {
        touchRef.current.lastX = e.touches[0].clientX;
        touchRef.current.lastY = e.touches[0].clientY;
        touchRef.current.singleId = e.touches[0].identifier;
      }
    }
  };
  const handleTouchMove = (e) => {
    if (e.touches.length === 2) {
      e.preventDefault();
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const s = stateRef.current;
      if (touchRef.current.dist > 0) {
        s.scale = Math.max(0.2, Math.min(4, s.scale * (dist / touchRef.current.dist)));
      }
      touchRef.current.dist = dist;
    } else if (e.touches.length === 1 && touchRef.current.singleId !== null) {
      const touch = e.touches[0];
      if (touch.identifier !== touchRef.current.singleId) return;
      const s = stateRef.current;
      if (s.dragNode) {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        const mx = (touch.clientX - rect.left - s.viewX) / s.scale;
        const my = (touch.clientY - rect.top - s.viewY) / s.scale;
        s.dragNode.x = mx + s.dragOffX;
        s.dragNode.y = my + s.dragOffY;
      } else {
        s.viewX += touch.clientX - touchRef.current.lastX;
        s.viewY += touch.clientY - touchRef.current.lastY;
        touchRef.current.lastX = touch.clientX;
        touchRef.current.lastY = touch.clientY;
      }
    }
  };
  const handleTouchEnd = () => {
    const s = stateRef.current;
    s.isDragging = false;
    s.dragNode = null;
    touchRef.current.singleId = null;
  };

  const handleRefresh = async () => {
    try {
      const data = await getGraph();
      const s = stateRef.current;
      s.nodes = data.nodes || [];
      s.edges = data.edges || [];
      setInfo({ nodes: s.nodes.length, edges: s.edges.length });
    } catch (_) {}
  };

  const handleReset = () => {
    setParams(DEFAULTS);
    paramsRef.current = { ...DEFAULTS };
  };

  const slider = (label, key, min, max, step) => (
    <div className="graph-slider-row">
      <span className="graph-slider-label">{label}</span>
      <input type="range" min={min} max={max} step={step} value={params[key]}
        onChange={e => updateParam(key, e.target.value)}
        className="graph-slider" />
      <span className="graph-slider-val">{params[key].toFixed(step < 0.01 ? 3 : (step < 0.1 ? 2 : 0))}</span>
    </div>
  );

  return (
    <div className="view graph-view">
      <div className="graph-container" ref={containerRef}>
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
          onTouchCancel={handleTouchEnd}
        />
        {showControls && (
          <div className="graph-controls-panel">
            <div className="graph-controls-header">
              <span>Fisica del grafo</span>
              <button className="btn btn-secondary" style={{ fontSize: 11, padding: '2px 8px' }} onClick={handleReset}>Reset</button>
            </div>
            {slider('Repulsion', 'repulsion', 1000, 50000, 100)}
            {slider('Atraccion', 'attraction', 0.0001, 0.02, 0.0001)}
            {slider('Amortiguacion', 'damping', 0.5, 0.99, 0.01)}
            {slider('Centrado', 'centering', 0.001, 0.05, 0.001)}
          </div>
        )}
        <div className="graph-controls">
          <span className="graph-info">{info.nodes} nodos &bull; {info.edges} aristas</span>
          <button className="btn btn-secondary btn-sm" onClick={() => setShowControls(!showControls)}>
            {showControls ? 'Ocultar' : 'Ajustes'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handleRefresh}>Refrescar</button>
          <span className="graph-legend">
            <span className="legend-dot" style={{ background: '#7850ff' }} /> &lt; 0.6
            <span className="legend-dot" style={{ background: '#00c8ff' }} /> &ge; 0.8
          </span>
        </div>
      </div>
    </div>
  );
}
