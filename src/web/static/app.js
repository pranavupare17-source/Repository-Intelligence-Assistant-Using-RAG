/**
 * Repository Intelligence Assistant - Frontend Orchestrator
 * Pure ES6 with HTML5 Canvas Force-Directed Graph Engine & REST API Integration
 */

// Application State
const state = {
  activeTab: 'graph',
  graphData: { nodes: [], edges: [], stats: {} },
  selectedNodeId: null,
  blastRadiusData: null,
  activePathIds: null,
  filterTypes: {
    file: true,
    class: true,
    method: true,
    function: true,
    module: true,
  },
  chunks: [],
  selectedFile: null,
  transform: { x: 0, y: 0, scale: 1 },
  isDragging: false,
  dragNode: null,
  lastMouse: { x: 0, y: 0 },
  hoverNode: null,
};

// Node Colors & Radii Configuration: Matte Industrial Metal Palette
const NODE_CONFIG = {
  file: { color: '#27272a', stroke: '#64748b', radius: 14 },
  class: { color: '#303036', stroke: '#8b8b94', radius: 12 },
  method: { color: '#242428', stroke: '#a1a1aa', radius: 10 },
  function: { color: '#1e1e22', stroke: '#71717a', radius: 10 },
  module: { color: '#18181b', stroke: '#52525b', radius: 8 },
};

const EDGE_CONFIG = {
  calls: { color: '#3f3f46', width: 1.2, dash: [] },
  imports: { color: '#2e2e34', width: 1.0, dash: [4, 4] },
  contains: { color: '#242428', width: 1.0, dash: [] },
  inherits: { color: '#52525b', width: 1.5, dash: [2, 2] },
};

// ==========================================================================
// Initialization & Lifecycle
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  initTabs();
  initCanvas();
  initSearch();
  initFilters();
  initPathFinder();

  // Load telemetry and initial datasets
  await loadSystemStatus();
  await loadGraphData();
  await loadChunks();
});

// ==========================================================================
// Tab Management
// ==========================================================================
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === `panel-${tabName}`);
  });

  if (tabName === 'graph') {
    resizeCanvas();
  }
}

// ==========================================================================
// Telemetry & Status API
// ==========================================================================
async function loadSystemStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('stat-chunks-count').textContent = data.ast_chunks.total_chunks;
    document.getElementById('stat-vectors-count').textContent = data.vector_store.total_vectors;
    document.getElementById('stat-dim').textContent = `${data.vector_store.dimension}d`;
    document.getElementById('stat-nodes-count').textContent = data.knowledge_graph.total_nodes;
    document.getElementById('stat-edges-count').textContent = data.knowledge_graph.total_edges;
  } catch (err) {
    console.error('Failed to load status:', err);
  }
}

// ==========================================================================
// HTML5 Canvas Force-Directed Graph Engine
// ==========================================================================
let canvas, ctx;
let simNodes = [];
let simEdges = [];
let animFrameId = null;

function initCanvas() {
  canvas = document.getElementById('graph-canvas');
  ctx = canvas.getContext('2d');

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  // Mouse / Touch Interactivity
  canvas.addEventListener('mousedown', onMouseDown);
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
  canvas.addEventListener('wheel', onWheel, { passive: false });

  // Toolbar Actions
  document.getElementById('btn-zoom-in').addEventListener('click', () => zoom(1.2));
  document.getElementById('btn-zoom-out').addEventListener('click', () => zoom(0.8));
  document.getElementById('btn-reset-view').addEventListener('click', resetView);

  // Search inside graph
  document.getElementById('graph-search-btn').addEventListener('click', () => {
    const q = document.getElementById('graph-search-input').value.trim();
    if (q) focusNodeByName(q);
  });
  document.getElementById('graph-search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const q = e.target.value.trim();
      if (q) focusNodeByName(q);
    }
  });
}

function resizeCanvas() {
  const container = document.getElementById('canvas-wrapper');
  if (!container || !canvas) return;
  canvas.width = container.clientWidth;
  canvas.height = container.clientHeight;
}

async function loadGraphData() {
  try {
    const res = await fetch('/api/graph');
    if (!res.ok) return;
    const data = await res.json();
    state.graphData = data;

    setupSimulation(data.nodes, data.edges);
    startSimulation();
  } catch (err) {
    console.error('Failed to load graph:', err);
  }
}

let simAlpha = 0.25;
const ALPHA_DECAY = 0.95;
const ALPHA_MIN = 0.003;

function wakeSimulation(targetAlpha = 0.2) {
  if (simAlpha < targetAlpha) {
    simAlpha = targetAlpha;
  }
}

function setupSimulation(nodes, edges) {
  const width = canvas.width || 800;
  const height = canvas.height || 600;

  // Initialize node positions in a calm, spread layout
  const nodeMap = new Map();
  simNodes = nodes.map((n, i) => {
    const angle = (i / nodes.length) * 2 * Math.PI;
    const r = 160 + (i % 4) * 40;
    const sNode = {
      ...n,
      x: width / 2 + r * Math.cos(angle),
      y: height / 2 + r * Math.sin(angle),
      vx: 0,
      vy: 0,
      radius: (NODE_CONFIG[n.node_type] || NODE_CONFIG.module).radius,
      color: (NODE_CONFIG[n.node_type] || NODE_CONFIG.module).color,
      stroke: (NODE_CONFIG[n.node_type] || NODE_CONFIG.module).stroke,
      pinned: false,
    };
    nodeMap.set(n.id, sNode);
    return sNode;
  });

  simEdges = edges.map(e => ({
    ...e,
    sourceNode: nodeMap.get(e.source),
    targetNode: nodeMap.get(e.target),
  })).filter(e => e.sourceNode && e.targetNode);

  // Pre-stabilize layout so it starts already clustered and doesn't explode
  let warmAlpha = 0.7;
  for (let s = 0; s < 60; s++) {
    updatePhysics(warmAlpha);
    warmAlpha *= 0.94;
  }

  simAlpha = 0.2;
  resetView();
}

function resetView() {
  state.transform = { x: 0, y: 0, scale: 1 };
}

function zoom(factor) {
  const newScale = Math.max(0.3, Math.min(3.5, state.transform.scale * factor));
  state.transform.scale = newScale;
}

function startSimulation() {
  if (animFrameId) cancelAnimationFrame(animFrameId);

  function tick() {
    if (simAlpha > ALPHA_MIN || state.dragNode) {
      updatePhysics(simAlpha);
      if (!state.dragNode) {
        simAlpha *= ALPHA_DECAY;
      }
    }
    renderGraph();
    animFrameId = requestAnimationFrame(tick);
  }
  animFrameId = requestAnimationFrame(tick);
}

function updatePhysics(alpha = 1.0) {
  const kRepulse = 1100;
  const kSpring = 0.025;
  const damping = 0.72;
  const centerGravity = 0.006;
  const maxVelocity = 2.5 * Math.max(alpha, 0.15);

  const cx = canvas.width / 2;
  const cy = canvas.height / 2;

  // 1. Center Gravity (gentle tether)
  for (const n of simNodes) {
    if (n.pinned) continue;
    n.vx += (cx - n.x) * centerGravity * alpha;
    n.vy += (cy - n.y) * centerGravity * alpha;
  }

  // 2. Node-Node Repulsion (softened at close range)
  for (let i = 0; i < simNodes.length; i++) {
    const a = simNodes[i];
    for (let j = i + 1; j < simNodes.length; j++) {
      const b = simNodes[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      let dist = Math.sqrt(dx * dx + dy * dy);
      if (dist === 0) dist = 1;
      if (dist < 220) {
        const softDist = Math.max(dist, 40);
        const force = (kRepulse / (softDist * softDist)) * alpha;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
        if (!b.pinned) { b.vx += fx; b.vy += fy; }
      }
    }
  }

  // 3. Edge Attraction (gentle target distance)
  for (const e of simEdges) {
    const a = e.sourceNode;
    const b = e.targetNode;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    let dist = Math.sqrt(dx * dx + dy * dy);
    if (dist === 0) dist = 1;
    const targetDist = e.edge_type === 'contains' ? 45 : 85;
    const force = (dist - targetDist) * kSpring * alpha;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    if (!a.pinned) { a.vx += fx; a.vy += fy; }
    if (!b.pinned) { b.vx += fx; b.vy += fy; }
  }

  // 4. Position update & velocity damping & max speed clamp
  for (const n of simNodes) {
    if (!n.pinned) {
      n.vx *= damping;
      n.vy *= damping;
      const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      if (speed > maxVelocity) {
        n.vx = (n.vx / speed) * maxVelocity;
        n.vy = (n.vy / speed) * maxVelocity;
      }
      n.x += n.vx;
      n.y += n.vy;
    }
  }
}

function renderGraph() {
  if (!ctx || !canvas) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.save();
  ctx.translate(state.transform.x, state.transform.y);
  ctx.scale(state.transform.scale, state.transform.scale);

  // Draw Subtle Cyber Grid
  drawGrid();

  const selectedNode = simNodes.find(n => n.id === state.selectedNodeId);
  const connectedNodeIds = new Set();
  if (selectedNode) {
    connectedNodeIds.add(selectedNode.id);
    for (const e of simEdges) {
      if (e.sourceNode.id === selectedNode.id) connectedNodeIds.add(e.targetNode.id);
      if (e.targetNode.id === selectedNode.id) connectedNodeIds.add(e.sourceNode.id);
    }
  }

  // Draw Edges
  for (const e of simEdges) {
    const srcVisible = state.filterTypes[e.sourceNode.node_type];
    const tgtVisible = state.filterTypes[e.targetNode.node_type];
    if (!srcVisible || !tgtVisible) continue;

    const isConnected = selectedNode && (e.sourceNode.id === selectedNode.id || e.targetNode.id === selectedNode.id);
    const isPathEdge = state.activePathIds && isPath(e.sourceNode.id, e.targetNode.id);

    ctx.save();
    const cfg = EDGE_CONFIG[e.edge_type] || EDGE_CONFIG.calls;

    if (isPathEdge) {
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 2.5;
    } else if (selectedNode) {
      if (isConnected) {
        ctx.strokeStyle = '#71717a';
        ctx.lineWidth = 1.5;
      } else {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        ctx.lineWidth = 0.5;
      }
    } else {
      ctx.strokeStyle = cfg.color;
      ctx.lineWidth = cfg.width;
      if (cfg.dash.length) ctx.setLineDash(cfg.dash);
    }

    // Draw edge line with directional arrow
    drawArrow(e.sourceNode.x, e.sourceNode.y, e.targetNode.x, e.targetNode.y, e.targetNode.radius);
    ctx.restore();
  }

  // Draw Nodes
  for (const n of simNodes) {
    if (!state.filterTypes[n.node_type]) continue;

    const isSelected = n.id === state.selectedNodeId;
    const isHovered = n === state.hoverNode;
    const isConnected = !selectedNode || connectedNodeIds.has(n.id);
    const isBlast = state.blastRadiusData && state.blastRadiusData.has(n.id);
    const isPathNode = state.activePathIds && state.activePathIds.includes(n.id);

    ctx.save();
    let alpha = isConnected ? 1.0 : 0.15;
    if (isBlast) alpha = 1.0;

    ctx.globalAlpha = alpha;

    // Technical Concentric Rings (Zero Neon Glow / Zero Shadow Blur)
    if (isBlast) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 5, 0, 2 * Math.PI);
      ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)';
      ctx.lineWidth = 1;
      ctx.stroke();
    } else if (isPathNode) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 4, 0, 2 * Math.PI);
      ctx.strokeStyle = '#d4d4d8';
      ctx.lineWidth = 1;
      ctx.stroke();
    } else if (isSelected) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 4, 0, 2 * Math.PI);
      ctx.strokeStyle = '#71717a';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Node Body
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius, 0, 2 * Math.PI);
    ctx.fillStyle = isBlast ? '#7f1d1d' : (isPathNode ? '#27272a' : (isSelected ? '#323238' : n.color));
    ctx.fill();
    ctx.strokeStyle = isBlast ? '#fca5a5' : (isPathNode ? '#e2e8f0' : (isSelected ? '#ffffff' : (n.stroke || '#52525b')));
    ctx.lineWidth = isSelected ? 1.8 : 1.0;
    ctx.stroke();

    // Node Label
    if (alpha > 0.4 || state.transform.scale > 0.8) {
      ctx.font = isSelected ? '600 10.5px Inter, sans-serif' : '10px Inter, sans-serif';
      ctx.fillStyle = isSelected ? '#ffffff' : (isConnected ? '#a1a1aa' : '#404040');
      ctx.textAlign = 'center';
      ctx.fillText(n.name, n.x, n.y + n.radius + 12);
    }

    ctx.restore();
  }

  ctx.restore();
}

function drawGrid() {
  const gridSize = 40;
  ctx.save();
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.02)';
  ctx.lineWidth = 1;
  const startX = -state.transform.x / state.transform.scale;
  const startY = -state.transform.y / state.transform.scale;
  const endX = startX + canvas.width / state.transform.scale;
  const endY = startY + canvas.height / state.transform.scale;

  ctx.beginPath();
  for (let x = Math.floor(startX / gridSize) * gridSize; x < endX; x += gridSize) {
    ctx.moveTo(x, startY);
    ctx.lineTo(x, endY);
  }
  for (let y = Math.floor(startY / gridSize) * gridSize; y < endY; y += gridSize) {
    ctx.moveTo(startX, y);
    ctx.lineTo(endX, y);
  }
  ctx.stroke();
  ctx.restore();
}

function drawArrow(x1, y1, x2, y2, targetRadius) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.sqrt(dx * dx + dy * dy);
  if (dist === 0) return;

  // Offset line to end at the edge of the target node
  const stopDist = dist - targetRadius - 3;
  const endX = x1 + (dx / dist) * stopDist;
  const endY = y1 + (dy / dist) * stopDist;

  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(endX, endY);
  ctx.stroke();

  // Draw arrow head
  const arrowSize = 6;
  const angle = Math.atan2(dy, dx);
  ctx.beginPath();
  ctx.moveTo(endX, endY);
  ctx.lineTo(
    endX - arrowSize * Math.cos(angle - Math.PI / 6),
    endY - arrowSize * Math.sin(angle - Math.PI / 6)
  );
  ctx.lineTo(
    endX - arrowSize * Math.cos(angle + Math.PI / 6),
    endY - arrowSize * Math.sin(angle + Math.PI / 6)
  );
  ctx.closePath();
  ctx.fillStyle = ctx.strokeStyle;
  ctx.fill();
}

function isPath(u, v) {
  if (!state.activePathIds) return false;
  const idxU = state.activePathIds.indexOf(u);
  const idxV = state.activePathIds.indexOf(v);
  return idxU !== -1 && idxV !== -1 && idxV === idxU + 1;
}

// Mouse Event Handlers
function screenToWorld(sx, sy) {
  return {
    x: (sx - state.transform.x) / state.transform.scale,
    y: (sy - state.transform.y) / state.transform.scale,
  };
}

function findNodeAt(worldX, worldY) {
  for (let i = simNodes.length - 1; i >= 0; i--) {
    const n = simNodes[i];
    if (!state.filterTypes[n.node_type]) continue;
    const dx = worldX - n.x;
    const dy = worldY - n.y;
    if (dx * dx + dy * dy <= (n.radius + 4) * (n.radius + 4)) {
      return n;
    }
  }
  return null;
}

function onMouseDown(e) {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const world = screenToWorld(mouseX, mouseY);

  const hitNode = findNodeAt(world.x, world.y);
  if (hitNode) {
    state.dragNode = hitNode;
    hitNode.pinned = true;
    selectNode(hitNode.id);
  } else {
    state.isDragging = true;
    state.lastMouse = { x: e.clientX, y: e.clientY };
  }
}

function onMouseMove(e) {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const world = screenToWorld(mouseX, mouseY);

  if (state.dragNode) {
    state.dragNode.x = world.x;
    state.dragNode.y = world.y;
    wakeSimulation(0.12);
  } else if (state.isDragging) {
    const dx = e.clientX - state.lastMouse.x;
    const dy = e.clientY - state.lastMouse.y;
    state.transform.x += dx;
    state.transform.y += dy;
    state.lastMouse = { x: e.clientX, y: e.clientY };
  } else {
    const hover = findNodeAt(world.x, world.y);
    state.hoverNode = hover;
    canvas.style.cursor = hover ? 'pointer' : 'grab';
  }
}

function onMouseUp() {
  if (state.dragNode) {
    state.dragNode.pinned = false;
    state.dragNode = null;
    wakeSimulation(0.15);
  }
  state.isDragging = false;
}

function onWheel(e) {
  e.preventDefault();
  const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
  zoom(zoomFactor);
}

// ==========================================================================
// Node Selection & Inspector Drawer
// ==========================================================================
async function selectNode(nodeId) {
  state.selectedNodeId = nodeId;
  state.blastRadiusData = null; // reset blast glow

  const node = simNodes.find(n => n.id === nodeId);
  if (!node) return;

  document.getElementById('insp-empty').classList.add('hidden');
  document.getElementById('insp-content').classList.remove('hidden');

  document.getElementById('insp-type').textContent = node.node_type;
  document.getElementById('insp-name').textContent = node.name;
  document.getElementById('insp-citation').textContent = node.citation || `[${node.name}]`;
  document.getElementById('insp-docstring').textContent = node.docstring ? node.docstring.trim() : 'No docstring available.';
  document.getElementById('insp-blast-sec').classList.add('hidden');

  // Load detailed callers, callees, code from /api/node
  try {
    const res = await fetch(`/api/node?id=${encodeURIComponent(nodeId)}`);
    if (!res.ok) return;
    const detail = await res.json();

    // Callers List
    const callersContainer = document.getElementById('insp-callers-list');
    callersContainer.innerHTML = '';
    document.getElementById('insp-callers-title').textContent = `Upstream Callers (${detail.callers.length})`;
    if (detail.callers.length === 0) {
      callersContainer.innerHTML = '<span class="text-dim">No callers detected.</span>';
    } else {
      detail.callers.forEach(c => {
        const card = createItemCard(c.node.name, c.node.citation, c.edge.call_expr, () => {
          selectNode(c.node.id);
          focusNode(c.node.id);
        });
        callersContainer.appendChild(card);
      });
    }

    // Callees List
    const calleesContainer = document.getElementById('insp-callees-list');
    calleesContainer.innerHTML = '';
    document.getElementById('insp-callees-title').textContent = `Downstream Callees (${detail.callees.length})`;
    if (detail.callees.length === 0) {
      calleesContainer.innerHTML = '<span class="text-dim">No downstream calls detected.</span>';
    } else {
      detail.callees.forEach(c => {
        const card = createItemCard(c.node.name, c.node.node_type, c.edge.call_expr, () => {
          if (c.node.id) {
            selectNode(c.node.id);
            focusNode(c.node.id);
          }
        });
        calleesContainer.appendChild(card);
      });
    }

    // Source Code Preview
    const codeElem = document.getElementById('insp-code');
    codeElem.textContent = detail.code || '# Source code not available for module entity';

    // Hook Blast Radius Button
    const blastBtn = document.getElementById('btn-calc-blast');
    blastBtn.onclick = () => renderBlastRadius(detail.blast_radius);

    // Hook Semantic Search Button
    const searchBtn = document.getElementById('btn-search-this');
    searchBtn.onclick = () => {
      switchTab('search');
      document.getElementById('search-input').value = `${node.name} ${node.parent_class || ''}`.trim();
      executeSearch();
    };

  } catch (err) {
    console.error('Failed to load node detail:', err);
  }
}

function createItemCard(title, citation, codeSnippet, onClick) {
  const div = document.createElement('div');
  div.className = 'item-card';
  div.innerHTML = `
    <div class="item-card-header">
      <span class="item-card-title">${escapeHtml(title)}</span>
      <span class="item-card-citation">${escapeHtml(citation || '')}</span>
    </div>
    ${codeSnippet ? `<div class="item-card-code">${escapeHtml(codeSnippet)}</div>` : ''}
  `;
  div.addEventListener('click', onClick);
  return div;
}

function renderBlastRadius(blast) {
  state.blastRadiusData = new Set();
  const treeContainer = document.getElementById('insp-blast-tree');
  treeContainer.innerHTML = '';

  const blastSec = document.getElementById('insp-blast-sec');
  blastSec.classList.remove('hidden');

  document.getElementById('insp-blast-title').textContent = `💥 Impact Blast Radius (${blast.total_affected} affected)`;

  if (blast.total_affected === 0) {
    treeContainer.innerHTML = '<p class="text-dim">No upstream components depend on this entity.</p>';
    return;
  }

  for (const [depth, items] of Object.entries(blast.impact_levels)) {
    const levelDiv = document.createElement('div');
    levelDiv.className = 'blast-level';
    levelDiv.innerHTML = `<div class="blast-level-title">Depth ${depth} (${items.length} affected)</div>`;

    const itemsDiv = document.createElement('div');
    itemsDiv.className = 'blast-level-items';

    items.forEach(item => {
      state.blastRadiusData.add(item.node.id);
      const itemElem = document.createElement('div');
      itemElem.className = 'blast-node-item';
      itemElem.innerHTML = `<strong>${escapeHtml(item.node.name)}</strong> <span class="text-dim">${escapeHtml(item.node.citation || '')}</span>`;
      itemsDiv.appendChild(itemElem);
    });

    levelDiv.appendChild(itemsDiv);
    treeContainer.appendChild(levelDiv);
  }
}

function focusNode(nodeId) {
  const node = simNodes.find(n => n.id === nodeId);
  if (!node) return;
  state.transform.x = canvas.width / 2 - node.x * state.transform.scale;
  state.transform.y = canvas.height / 2 - node.y * state.transform.scale;
}

function focusNodeByName(query) {
  const target = simNodes.find(n => n.name.toLowerCase().includes(query.toLowerCase()));
  if (target) {
    selectNode(target.id);
    focusNode(target.id);
  } else {
    alert(`Symbol "${query}" not found in graph.`);
  }
}

// ==========================================================================
// Filter Checkboxes & Path Finder
// ==========================================================================
function initFilters() {
  ['file', 'class', 'method', 'function', 'module'].forEach(type => {
    const check = document.getElementById(`filter-${type}`);
    if (check) {
      check.addEventListener('change', (e) => {
        state.filterTypes[type] = e.target.checked;
        wakeSimulation(0.2);
      });
    }
  });
}

function initPathFinder() {
  const toggleBtn = document.getElementById('btn-toggle-path');
  const bar = document.getElementById('path-finder-bar');
  const closeBtn = document.getElementById('btn-close-path');
  const findBtn = document.getElementById('btn-find-path');

  toggleBtn.addEventListener('click', () => {
    bar.classList.toggle('hidden');
  });
  closeBtn.addEventListener('click', () => {
    bar.classList.add('hidden');
    state.activePathIds = null;
  });

  findBtn.addEventListener('click', async () => {
    const src = document.getElementById('path-src-input').value.trim();
    const tgt = document.getElementById('path-tgt-input').value.trim();
    if (!src || !tgt) return;

    try {
      const res = await fetch(`/api/path?src=${encodeURIComponent(src)}&tgt=${encodeURIComponent(tgt)}`);
      const data = await res.json();
      if (data.path && data.path.length) {
        state.activePathIds = data.path.map(p => p.node.id);
        focusNode(state.activePathIds[0]);
      } else {
        alert(`No directed call-chain found between "${src}" and "${tgt}".`);
      }
    } catch (err) {
      console.error('Failed to find path:', err);
    }
  });
}

// ==========================================================================
// TAB 2: SEMANTIC VECTOR SEARCH
// ==========================================================================
function initSearch() {
  const form = document.getElementById('search-form');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    executeSearch();
  });

  // Benchmark chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.getElementById('search-input').value = chip.dataset.query;
      executeSearch();
    });
  });
}

async function executeSearch() {
  const query = document.getElementById('search-input').value.trim();
  if (!query) return;

  const resultsList = document.getElementById('results-list');
  resultsList.innerHTML = '<div class="empty-state">Executing dense FAISS cosine retrieval...</div>';

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, k: 5 }),
    });
    if (!res.ok) throw new Error('Search failed');
    const data = await res.json();

    document.getElementById('results-count-title').textContent = `Top ${data.results.length} Ranked Semantic Hits`;
    document.getElementById('results-query-tag').textContent = `"${data.query}"`;

    renderSearchResults(data.results);
  } catch (err) {
    resultsList.innerHTML = `<div class="empty-state text-danger">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function renderSearchResults(results) {
  const resultsList = document.getElementById('results-list');
  resultsList.innerHTML = '';

  if (results.length === 0) {
    resultsList.innerHTML = '<div class="empty-state">No matching code chunks found.</div>';
    return;
  }

  results.forEach(hit => {
    const card = document.createElement('div');
    card.className = 'search-result-card';

    const scoreClass = hit.score >= 0.5 ? 'high' : 'medium';

    card.innerHTML = `
      <div class="card-top-bar">
        <div class="card-badges">
          <span class="rank-badge">Rank #${hit.rank}</span>
          <span class="score-badge ${scoreClass}">Cosine: ${hit.score.toFixed(4)}</span>
        </div>
        <span class="citation-badge">${escapeHtml(hit.citation)}</span>
      </div>

      <div class="card-title-row">
        <span class="card-symbol-name">${escapeHtml(hit.name)}</span>
        ${hit.parent_class ? `<span class="card-parent">in class ${escapeHtml(hit.parent_class)}</span>` : ''}
      </div>

      <div class="card-context-header">${escapeHtml(hit.context_header)}</div>

      <div class="card-code-block">
        <pre><code>${escapeHtml(hit.code)}</code></pre>
      </div>

      <div class="card-footer">
        <button class="btn btn-outline btn-sm btn-show-graph">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
          Show in Knowledge Graph
        </button>
      </div>
    `;

    card.querySelector('.btn-show-graph').addEventListener('click', () => {
      switchTab('graph');
      focusNodeByName(hit.name);
    });

    resultsList.appendChild(card);
  });
}

// ==========================================================================
// TAB 3: AST CHUNKER EXPLORER
// ==========================================================================
async function loadChunks() {
  try {
    const res = await fetch('/api/chunks');
    if (!res.ok) return;
    const data = await res.json();
    state.chunks = data.chunks;

    // Group by file
    const fileMap = new Map();
    state.chunks.forEach(c => {
      if (!fileMap.has(c.file_path)) fileMap.set(c.file_path, []);
      fileMap.get(c.file_path).push(c);
    });

    renderFileTree(fileMap);
  } catch (err) {
    console.error('Failed to load chunks:', err);
  }
}

function renderFileTree(fileMap) {
  const treeList = document.getElementById('file-tree-list');
  treeList.innerHTML = '';
  document.getElementById('files-badge').textContent = `${fileMap.size} files`;

  let firstFile = null;
  fileMap.forEach((chunks, filePath) => {
    if (!firstFile) firstFile = filePath;
    const li = document.createElement('li');
    li.className = 'file-item';
    li.innerHTML = `
      <span>📄 ${escapeHtml(filePath)}</span>
      <span class="badge">${chunks.length} chunks</span>
    `;
    li.addEventListener('click', () => {
      document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
      li.classList.add('active');
      renderFileChunks(filePath, chunks);
    });
    treeList.appendChild(li);
  });

  if (firstFile) {
    treeList.firstChild.classList.add('active');
    renderFileChunks(firstFile, fileMap.get(firstFile));
  }
}

function renderFileChunks(filePath, chunks) {
  document.getElementById('selected-file-title').textContent = filePath;
  document.getElementById('selected-file-summary').textContent = `${chunks.length} semantic AST chunks extracted strictly at class and function boundaries.`;

  const container = document.getElementById('chunks-cards-list');
  container.innerHTML = '';

  chunks.forEach(c => {
    const card = document.createElement('div');
    card.className = 'chunk-card';
    card.innerHTML = `
      <div class="chunk-card-top">
        <span class="chunk-name">${escapeHtml(c.name)}</span>
        <span class="type-pill">${escapeHtml(c.chunk_type)}</span>
      </div>
      <div class="citation-badge">${escapeHtml(c.citation)}</div>
      ${c.parent_class ? `<div class="card-parent">Parent Class: <strong>${escapeHtml(c.parent_class)}</strong></div>` : ''}
      ${c.docstring ? `<div class="docstring-box">${escapeHtml(c.docstring)}</div>` : ''}
      <div class="card-context-header">${escapeHtml(c.context_header)}</div>
      <div class="card-code-block"><pre><code>${escapeHtml(c.code)}</code></pre></div>
    `;
    container.appendChild(card);
  });
}

// Utility
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
