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
    nodeMap: new Map(), edgeIdMap: new Map(), stableFrames: 0, frameCount: 0,
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
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
  }, []);

  // Neural / brain-like color palette
  const BRAIN_BG = '#0d0b1a';
  const NEURON_CORE = 'rgba(255, 180, 120, 0.9)';     // warm firing neuron
  const NEURON_GLOW = 'rgba(255, 120, 80, 0.4)';
  const CONNECTED_GLOW = 'rgba(255, 100, 150, 0.6)';
  const EDGE_COLOR = 'rgba(200, 120, 180, 0.25)';
  const EDGE_HL = 'rgba(255, 160, 100, 0.7)';
  const HOVER_NEURON = 'rgba(255, 200, 150, 0.95)';
  const BG_STARS = true;

  const renderGraph = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const s = stateRef.current;
    const { physics: pts, edges, viewX, viewY, scale, hoverNode, nodeMap } = s;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.width / dpr, h = canvas.height / dpr;
    if (!w || !h) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = BRAIN_BG;
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

    // Culling and rendering quality based on node count
    const margin = 60;
    const maxNodes = pts.length;
    const heavy = maxNodes > 200;       // skip gradients, shadows
    const moderate = maxNodes > 100;    // reduce glow
    const hideLabels = maxNodes > 180;
    const glowFactor = moderate ? 0.35 : 1.0;
    const labelAlpha = maxNodes > 120 ? '0.5' : '0.8';

    const isOnScreen = (node) => {
      const sx = node.x * scale + viewX;
      const sy = node.y * scale + viewY;
      return sx >= -margin && sx <= w + margin && sy >= -margin && sy <= h + margin;
    };

    // Edges — skip when both ends off-screen
    for (const edge of edges) {
      const src = nodeMap.get(edge.source);
      const tgt = nodeMap.get(edge.target);
      if (!src || !tgt) continue;
      if (!isOnScreen(src) && !isOnScreen(tgt)) continue;

      const weight = edge.weight || 0.3;
      const hl = hoverNode && connectedSet.has(edge.source) && connectedSet.has(edge.target);
      const alpha = hl ? 0.7 : (0.06 + weight * 0.35);
      const lineW = hl ? 2.0 : Math.max(0.4, weight * 1.2);

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.strokeStyle = hl ? EDGE_HL : EDGE_COLOR;
      ctx.lineWidth = lineW;

      if (!heavy) {
        ctx.shadowColor = hl ? 'rgba(255, 160, 100, 0.3)' : 'rgba(200, 120, 180, 0.15)';
        ctx.shadowBlur = hl ? 12 * glowFactor : 4 * glowFactor;
      }
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Nodes — drawn as glowing neurons
    for (const node of pts) {
      if (!isOnScreen(node)) continue;

      const isHover = hoverNode && hoverNode.id === node.id;
      const isConnected = hoverNode && connectedSet.has(node.id);
      const baseR = node.r;
      // No pulse — wasted CPU on large graphs, minimal visual gain
      const r = isHover ? baseR * 1.5 : baseR;

      // Outer glow (skip for heavy graphs)
      if (!heavy) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r * 3.5, 0, Math.PI * 2);
        const glowGrad = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 3.5);
        if (isHover) {
          glowGrad.addColorStop(0, 'rgba(255, 200, 150, 0.25)');
          glowGrad.addColorStop(1, 'rgba(255, 200, 150, 0)');
        } else if (isConnected) {
          glowGrad.addColorStop(0, 'rgba(255, 100, 150, 0.18)');
          glowGrad.addColorStop(1, 'rgba(255, 100, 150, 0)');
        } else {
          glowGrad.addColorStop(0, 'rgba(200, 140, 180, 0.08)');
          glowGrad.addColorStop(1, 'rgba(200, 140, 180, 0)');
        }
        ctx.fillStyle = glowGrad;
        ctx.shadowBlur = 0;
        ctx.fill();
      }

      // Node body
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);

      if (heavy) {
        ctx.fillStyle = isHover ? '#ffb478' : (isConnected ? '#ff6496' : 'rgba(180, 140, 180, 0.5)');
      } else {
        const grad = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 2);
        if (isHover) {
          grad.addColorStop(0, HOVER_NEURON);
          grad.addColorStop(0.5, 'rgba(255, 160, 100, 0.7)');
          grad.addColorStop(1, 'rgba(255, 120, 80, 0)');
        } else if (isConnected) {
          grad.addColorStop(0, 'rgba(255, 130, 160, 0.85)');
          grad.addColorStop(0.5, 'rgba(220, 80, 140, 0.5)');
          grad.addColorStop(1, 'rgba(200, 60, 120, 0)');
        } else {
          grad.addColorStop(0, NEURON_CORE);
          grad.addColorStop(0.4, 'rgba(220, 150, 140, 0.5)');
          grad.addColorStop(1, 'rgba(180, 100, 120, 0)');
        }
        ctx.fillStyle = grad;

        ctx.shadowColor = isHover ? 'rgba(255, 200, 150, 0.5)' : (isConnected ? CONNECTED_GLOW : 'rgba(200, 140, 180, 0.15)');
        ctx.shadowBlur = (isHover ? 25 : (isConnected ? 14 : 6)) * glowFactor;
      }
      ctx.fill();
      ctx.shadowBlur = 0;

      // Bright inner dot (neuron nucleus)
      ctx.beginPath();
      ctx.arc(node.x, node.y, r * 0.35, 0, Math.PI * 2);
      ctx.fillStyle = isHover ? '#ffe8d0' : (isConnected ? '#ffb0c8' : 'rgba(255, 200, 180, 0.6)');
      ctx.fill();

      // Label
      const showLabel = isHover || (scale > 0.35 && !hideLabels);
      if (showLabel) {
        ctx.fillStyle = isHover ? '#fff' : `rgba(220, 200, 210, ${labelAlpha})`;
        ctx.font = `${Math.max(9, 11)}px 'Space Grotesk', sans-serif`;
        ctx.textAlign = 'center';
        const label = node.label.length > 28 ? node.label.slice(0, 28) + '\u2026' : node.label;
        ctx.fillText(label, node.x, node.y + r + 16);
      }
    }

    ctx.restore();
  }, []);

  const runPhysics = useCallback(() => {
    const s = stateRef.current;
    const pts = s.physics;
    if (!pts.length) return 0;
    const p = paramsRef.current;
    const rep = p.repulsion, attr = p.attraction, damp = p.damping, centerF = p.centering;
    const canvas = canvasRef.current;
    const w = canvas?.width || 800, h = canvas?.height || 600;
    const nodeMap = s.nodeMap;

    const len = pts.length;

    // ── Spatial grid for O(n*k) repulsion ──
    const CELL_SIZE = 200;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (let i = 0; i < len; i++) {
      const p = pts[i];
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }
    const gw = maxX - minX + 1;
    const gh = maxY - minY + 1;
    const cols = Math.max(1, Math.ceil(gw / CELL_SIZE) + 1);
    const rows = Math.max(1, Math.ceil(gh / CELL_SIZE) + 1);

    // Bucket nodes into grid cells
    const grid = [];
    for (let i = 0; i < len; i++) {
      const p = pts[i];
      const cx = Math.max(0, Math.min(cols - 1, Math.floor((p.x - minX) / CELL_SIZE)));
      const cy = Math.max(0, Math.min(rows - 1, Math.floor((p.y - minY) / CELL_SIZE)));
      const idx = cy * cols + cx;
      if (!grid[idx]) grid[idx] = [];
      grid[idx].push(i);
    }

    let totalEnergy = 0;

    for (let i = 0; i < len; i++) {
      let fx = 0, fy = 0;
      const a = pts[i];
      const cx = Math.max(0, Math.min(cols - 1, Math.floor((a.x - minX) / CELL_SIZE)));
      const cy = Math.max(0, Math.min(rows - 1, Math.floor((a.y - minY) / CELL_SIZE)));

      // Centering force
      fx += (w / 2 - a.x) * centerF * (a.hasEdges ? 1 : 0.3);
      fy += (h / 2 - a.y) * centerF * (a.hasEdges ? 1 : 0.3);

      // Repulsion — only check same cell and 8 neighbors
      for (let dcx = -1; dcx <= 1; dcx++) {
        for (let dcy = -1; dcy <= 1; dcy++) {
          const ncx = cx + dcx;
          const ncy = cy + dcy;
          if (ncx < 0 || ncy < 0 || ncx >= cols || ncy >= rows) continue;
          const nidx = ncy * cols + ncx;
          const cell = grid[nidx];
          if (!cell) continue;
          for (const j of cell) {
            if (j <= i) continue; // process each pair once
            const b = pts[j];
            const dx = a.x - b.x, dy = a.y - b.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = rep / (dist * dist + 50);
            fx += (dx / dist) * force;
            fy += (dy / dist) * force;
          }
        }
      }

      // Attraction — use precomputed edgeIdMap for O(1) per edge
      const edges = s.edgeIdMap.get(a.id);
      if (edges) {
        for (const edge of edges) {
          const otherId = edge.source === a.id ? edge.target : edge.source;
          const other = nodeMap.get(otherId);
          if (other) {
            fx += (other.x - a.x) * attr;
            fy += (other.y - a.y) * attr;
          }
        }
      }

      a.vx = (a.vx + fx) * damp;
      a.vy = (a.vy + fy) * damp;
      a.x += a.vx;
      a.y += a.vy;
      totalEnergy += Math.abs(a.vx) + Math.abs(a.vy);
    }

    return totalEnergy;
  }, []);

  const gameLoop = useCallback(() => {
    const s = stateRef.current;
    s.frameCount = (s.frameCount || 0) + 1;

    // Adaptive framerate: skip every other physics frame when many nodes
    const shouldSkipPhysics = s.nodes.length > 100 && s.frameCount % 2 === 0;

    let energy = 1;
    if (!shouldSkipPhysics) {
      energy = runPhysics();
      if (energy < 0.1) {
        s.stableFrames = (s.stableFrames || 0) + 1;
      } else {
        s.stableFrames = 0;
      }
    } else {
      s.stableFrames = 0;
    }

    renderGraph();
    s.time += 16;

    // Pause animation if stable for > 2 seconds
    const stableThreshold = s.nodes.length > 100 ? 60 : 120;
    if (s.stableFrames > stableThreshold) {
      s.animFrame = null;
      return;
    }

    s.animFrame = requestAnimationFrame(gameLoop);
  }, [runPhysics, renderGraph]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await getGraph();
        const s = stateRef.current;
        s.nodes = data.nodes || [];
        s.edges = data.edges || [];

        // Build edge lookup map (node.id -> edges[])
        s.edgeIdMap = new Map();
        for (const edge of s.edges) {
          if (!s.edgeIdMap.has(edge.source)) s.edgeIdMap.set(edge.source, []);
          if (!s.edgeIdMap.has(edge.target)) s.edgeIdMap.set(edge.target, []);
          s.edgeIdMap.get(edge.source).push(edge);
          s.edgeIdMap.get(edge.target).push(edge);
        }

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

        s.nodeMap = new Map(s.physics.map(n => [n.id, n]));
        s.stableFrames = 0;
        s.frameCount = 0;

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
    // Resume animation if paused
    if (!s.animFrame) { s.stableFrames = 0; s.animFrame = requestAnimationFrame(gameLoop); }
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
    // Resume animation if paused
    if (!s.animFrame) { s.stableFrames = 0; s.animFrame = requestAnimationFrame(gameLoop); }
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    s.scale = Math.max(0.2, Math.min(4, s.scale * delta));
  };

  const touchRef = useRef({ dist: 0, lastX: 0, lastY: 0, singleId: null });
  const handleTouchStart = (e) => {
    const s = stateRef.current;
    // Resume animation if paused
    if (!s.animFrame) { s.stableFrames = 0; s.animFrame = requestAnimationFrame(gameLoop); }
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

      // Rebuild lookup maps
      s.edgeIdMap = new Map();
      for (const edge of s.edges) {
        if (!s.edgeIdMap.has(edge.source)) s.edgeIdMap.set(edge.source, []);
        if (!s.edgeIdMap.has(edge.target)) s.edgeIdMap.set(edge.target, []);
        s.edgeIdMap.get(edge.source).push(edge);
        s.edgeIdMap.get(edge.target).push(edge);
      }

      const connected = new Set();
      s.edges.forEach(e => { connected.add(e.source); connected.add(e.target); });

      const canvas = canvasRef.current;
      const w = canvas?.width || 800, h = canvas?.height || 600;

      s.physics = s.nodes.map(n => {
        const hasEdges = connected.has(n.id);
        const existing = s.nodeMap ? s.nodeMap.get(n.id) : null;
        return {
          id: n.id, label: n.label || n.id,
          x: existing ? existing.x : w / 2 + (hasEdges ? (Math.random() - 0.5) * w * 0.3 : (Math.random() - 0.5) * w * 0.6),
          y: existing ? existing.y : h / 2 + (hasEdges ? (Math.random() - 0.5) * h * 0.3 : (Math.random() - 0.5) * h * 0.6),
          vx: existing ? existing.vx : 0, vy: existing ? existing.vy : 0,
          r: Math.max(5, Math.min(14, (n.size || 1) * 3)),
          hasEdges,
        };
      });

      s.nodeMap = new Map(s.physics.map(n => [n.id, n]));
      s.stableFrames = 0;
      s.frameCount = 0;

      // Resume animation if paused
      if (!s.animFrame) { s.animFrame = requestAnimationFrame(gameLoop); }

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
