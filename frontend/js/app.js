const API = '';

const state = {
  notes: [], currentNote: null, noteLinks: [], noteBacklinks: [],
  agents: { connector: 'idle', evolver: 'idle' },
  loading: false, inboxFilter: 'all', inboxFiles: [],
  graphNodes: [], graphEdges: [],
};

function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function renderMD(text) {
  let html = esc(text);
  // [[wikilinks]]
  html = html.replace(/\[\[([^\]]+)\]\]/g, (m, name) => {
    const slug = name.toLowerCase().replace(/\s+/g, '-');
    return `<a class="wikilink" data-target="${esc(slug)}" onclick="navigateToNote('${esc(slug)}')">${esc(name)}</a>`;
  });
  // headings
  html = html.replace(/^###### (.+)$/gm, '<h6>$1</h6>');
  html = html.replace(/^##### (.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // bold & italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  // code
  html = html.replace(/`(.+?)`/g, '<code>$1</code>');
  // blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  // lists
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  // horizontal rules
  html = html.replace(/^---$/gm, '<hr>');
  // paragraphs
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  // clean empty paragraphs
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

async function navigateToNote(slug) {
  // Find the filename from slug
  const note = state.notes.find(n => n.filename.replace('.md','').toLowerCase() === slug.toLowerCase());
  if (note) {
    switchView('notes');
    await openNote(note.filename);
  } else {
    // Search API
    try {
      const res = await fetch(`${API}/api/notes?search=${slug}`);
      const notes = await res.json();
      if (notes.length) { switchView('notes'); await openNote(notes[0].filename); }
    } catch(e) {}
  }
}

function switchView(name) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const navBtn = document.querySelector(`.nav-item[data-view="${name}"]`);
  if (navBtn) navBtn.classList.add('active');
  const view = document.getElementById('view' + name.charAt(0).toUpperCase() + name.slice(1));
  if (view) view.classList.add('active');
  if (name === 'graph') setTimeout(renderGraph, 200);
  if (name === 'notes') loadNotes();
  if (name === 'inbox') loadInbox();
  if (name === 'agents') loadAgentStatus();
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

document.getElementById('sidebarToggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('collapsed');
});

// ===== CHAT (unchanged) =====
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');
const chatMessages = document.getElementById('chatMessages');
const chatSources = document.getElementById('chatSources');

function addMessage(role, content, sources) {
  const div = document.createElement('div');
  div.className = 'message ' + (role === 'user' ? 'user' : 'system');
  div.innerHTML = `<div class="message-avatar">${role === 'user' ? '👤' : '🧠'}</div>
    <div class="message-content">${renderMD(content)}</div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTyping() {
  const div = document.createElement('div');
  div.className = 'message system'; div.id = 'typingIndicator';
  div.innerHTML = `<div class="message-avatar">🧠</div><div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() { const el = document.getElementById('typingIndicator'); if (el) el.remove(); }

async function sendMessage() {
  const msg = chatInput.value.trim();
  if (!msg || state.loading) return;
  chatInput.value = ''; chatSources.innerHTML = '';
  addMessage('user', msg); addTyping();
  state.loading = true; chatSend.disabled = true;
  try {
    const res = await fetch(`${API}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'message=' + encodeURIComponent(msg),
    });
    const data = await res.json();
    removeTyping();
    addMessage('system', data.answer);
    if (data.sources && data.sources.length) {
      chatSources.innerHTML = data.sources.map(s =>
        `<span class="source-badge" onclick="navigateToNote('${s.filename.replace('.md','')})" style="cursor:pointer">📄 ${s.filename}</span>`
      ).join('');
    }
  } catch (e) { removeTyping(); addMessage('system', '⚠️ Error al conectar con el cerebro.'); }
  state.loading = false; chatSend.disabled = false;
}
chatSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }});

// ===== NOTES with Markdown Viewer =====
const notesItems = document.getElementById('notesItems');
const notesSearch = document.getElementById('notesSearch');
const noteTitleInput = document.getElementById('noteTitleInput');
const noteBodyInput = document.getElementById('noteBodyInput');
const noteFilename = document.getElementById('noteFilename');
const noteEditorEmpty = document.getElementById('noteEditorEmpty');
const noteEditorContent = document.getElementById('noteEditorContent');
const notePreview = document.getElementById('notePreview');
const noteBacklinksEl = document.getElementById('noteBacklinks');
const noteOutlinksEl = document.getElementById('noteOutlinks');
let noteEditMode = true;

async function loadNotes(query) {
  try {
    const res = await fetch(`${API}/api/notes`);
    state.notes = await res.json();
    renderNotes(query);
  } catch (e) {}
}

function renderNotes(query) {
  let items = state.notes;
  if (query) {
    const q = query.toLowerCase();
    items = items.filter(n => n.title.toLowerCase().includes(q) || n.filename.toLowerCase().includes(q));
  }
  notesItems.innerHTML = items.map(n =>
    `<div class="note-item" data-filename="${n.filename}" onclick="openNote('${n.filename}')">
      <div class="note-item-title">${esc(n.title)}</div>
      <div class="note-item-meta">${new Date(n.modified).toLocaleDateString()} • ${formatSize(n.size)}</div>
    </div>`
  ).join('');
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + 'B';
  return (bytes / 1024).toFixed(1) + 'KB';
}

async function openNote(filename) {
  try {
    const res = await fetch(`${API}/api/notes/${encodeURIComponent(filename)}`);
    const note = await res.json();
    if (note.error) return;
    state.currentNote = note;
    noteEditorEmpty.style.display = 'none';
    noteEditorContent.style.display = 'flex';
    noteTitleInput.value = note.title;
    noteBodyInput.value = note.content;
    noteFilename.textContent = note.filename;
    noteEditMode = true;
    toggleNoteView();
    document.querySelectorAll('.note-item').forEach(el => el.classList.remove('active'));
    const item = document.querySelector(`.note-item[data-filename="${filename}"]`);
    if (item) item.classList.add('active');
    // Load wikilinks
    await loadNoteLinks(filename);
  } catch (e) {}
}

async function loadNoteLinks(filename) {
  try {
    const [linksRes, backlinksRes] = await Promise.all([
      fetch(`${API}/api/wikilinks/${encodeURIComponent(filename)}`),
      fetch(`${API}/api/backlinks/${encodeURIComponent(filename)}`)
    ]);
    const links = await linksRes.json();
    const backlinks = await backlinksRes.json();
    state.noteLinks = links.links || [];
    state.noteBacklinks = backlinks.backlinks || [];
    renderNoteLinks();
  } catch (e) {}
}

function renderNoteLinks() {
  if (noteOutlinksEl) {
    const outgoing = (state.noteLinks || []).filter(l => l.exists);
    noteOutlinksEl.innerHTML = outgoing.length
      ? '<strong>Conexiones salientes:</strong> ' + outgoing.map(l =>
          `<a class="wikilink" onclick="navigateToNote('${l.filename.replace('.md','')}')">${esc(l.wikilink)}</a>`
        ).join(' • ')
      : '<span style="color:var(--text-muted);font-size:12px">Sin conexiones salientes</span>';
  }
  if (noteBacklinksEl) {
    noteBacklinksEl.innerHTML = state.noteBacklinks.length
      ? '<strong>Notas que conectan aqui:</strong> ' + state.noteBacklinks.map(l =>
          `<a class="wikilink" onclick="navigateToNote('${l.filename.replace('.md','')}')">${esc(l.title)}</a>`
        ).join(' • ')
      : '<span style="color:var(--text-muted);font-size:12px">Sin backlinks</span>';
  }
}

function toggleNoteView() {
  const preview = document.getElementById('notePreview');
  const editor = document.getElementById('noteBodyInput');
  const toggleBtn = document.getElementById('togglePreviewBtn');
  if (noteEditMode) {
    // Show preview
    preview.innerHTML = renderMD(state.currentNote ? state.currentNote.content : '');
    preview.style.display = 'block';
    editor.style.display = 'none';
    if (toggleBtn) toggleBtn.textContent = '✏️ Editar';
    noteEditMode = false;
  } else {
    preview.style.display = 'none';
    editor.style.display = 'block';
    if (toggleBtn) toggleBtn.textContent = '👁️ Vista previa';
    noteEditMode = true;
  }
}

document.getElementById('newNoteBtn').addEventListener('click', async () => {
  const title = prompt('Título de la nueva nota:');
  if (!title) return;
  try {
    const res = await fetch(`${API}/api/notes?title=${encodeURIComponent(title)}&content=`, { method: 'POST' });
    const note = await res.json();
    await loadNotes();
    openNote(note.filename);
  } catch (e) {}
});

document.getElementById('saveNoteBtn').addEventListener('click', async () => {
  if (!state.currentNote) return;
  try {
    await fetch(`${API}/api/notes/${encodeURIComponent(state.currentNote.filename)}?content=${encodeURIComponent(noteBodyInput.value)}`, { method: 'PUT' });
    state.currentNote.content = noteBodyInput.value;
    state.currentNote.title = noteTitleInput.value;
    await loadNotes();
  } catch (e) {}
});

document.getElementById('deleteNoteBtn').addEventListener('click', async () => {
  if (!state.currentNote || !confirm('¿Eliminar esta nota?')) return;
  try {
    await fetch(`${API}/api/notes/${encodeURIComponent(state.currentNote.filename)}`, { method: 'DELETE' });
    state.currentNote = null;
    noteEditorEmpty.style.display = 'flex';
    noteEditorContent.style.display = 'none';
    await loadNotes();
  } catch (e) {}
});

document.getElementById('rebuildIndexBtn').addEventListener('click', async () => {
  try { await fetch(`${API}/api/brain/rebuild`, { method: 'POST' }); await loadBrainStats(); } catch (e) {}
});

notesSearch.addEventListener('input', e => renderNotes(e.target.value));

// Toggle preview button
document.getElementById('togglePreviewBtn')?.addEventListener('click', toggleNoteView);

// ===== INBOX (unchanged, but with auto-convert) =====
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const audioFileInput = document.getElementById('audioFileInput');
const queueItems = document.getElementById('queueItems');

document.getElementById('selectFilesBtn').addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('dragover');
  uploadFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => { uploadFiles(fileInput.files); fileInput.value = ''; });

const dropZoneAudio = document.getElementById('dropZoneAudio');
document.getElementById('selectAudioBtn').addEventListener('click', () => audioFileInput.click());
dropZoneAudio.addEventListener('dragover', e => { e.preventDefault(); dropZoneAudio.style.borderColor = 'var(--accent-purple)'; });
dropZoneAudio.addEventListener('dragleave', () => dropZoneAudio.style.borderColor = '');
dropZoneAudio.addEventListener('drop', e => {
  e.preventDefault(); dropZoneAudio.style.borderColor = '';
  uploadFiles(e.dataTransfer.files);
});
audioFileInput.addEventListener('change', () => { uploadFiles(audioFileInput.files); audioFileInput.value = ''; });

document.querySelectorAll('.queue-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.queue-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    state.inboxFilter = tab.dataset.queue;
    renderInbox(state.inboxFiles || []);
  });
});

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  if (['mp3','wav','m4a','ogg','flac','wma','aac','webm'].includes(ext)) return '🎤';
  if (['pdf'].includes(ext)) return '📕';
  if (['docx','doc'].includes(ext)) return '📘';
  if (['pptx','ppt'].includes(ext)) return '📙';
  if (['png','jpg','jpeg','gif','bmp','webp'].includes(ext)) return '🖼️';
  if (['html','htm'].includes(ext)) return '🌐';
  return '📄';
}

async function uploadFiles(files) {
  for (const file of files) {
    const formData = new FormData();
    formData.append('file', file);
    const ext = file.name.split('.').pop().toLowerCase();
    const isPdfOrImg = ['pdf','png','jpg','jpeg','bmp','webp'].includes(ext);
    try {
      await fetch(`${API}/api/inbox/upload?auto=${isPdfOrImg}`, { method: 'POST', body: formData });
    } catch (e) {}
  }
  loadInbox();
  await loadBrainStats();
  await loadNotes();
}

function renderInbox(files) {
  const filtered = state.inboxFilter === 'all' ? files : files.filter(f => f.type === state.inboxFilter);
  if (!filtered.length) {
    queueItems.innerHTML = '<div class="queue-empty">No hay archivos pendientes</div>'; return;
  }
  queueItems.innerHTML = filtered.map(f => {
    const isAudio = f.type === 'audio';
    const icon = getFileIcon(f.filename);
    const typeClass = isAudio ? 'file-type-audio' : 'file-type-document';
    const typeLabel = isAudio ? 'Audio' : 'Documento';
    const actionBtn = isAudio
      ? `<button class="btn btn-secondary" onclick="transcribeFile('${f.filename}')" style="padding:4px 8px;font-size:11px;background:rgba(168,85,247,0.15);border-color:rgba(168,85,247,0.3)">🎤 Transcribir</button>`
      : `<button class="btn btn-secondary" onclick="convertFile('${f.filename}')" style="padding:4px 8px;font-size:11px">📝 Convertir</button>`;
    return `<div class="inbox-file-item">
      <span class="file-icon">${icon}</span>
      <span class="file-name">${esc(f.filename)}</span>
      <span class="file-type-badge ${typeClass}">${typeLabel}</span>
      <span class="file-size">${f.size ? formatSize(f.size) : '—'}</span>
      ${actionBtn}
    </div>`;
  }).join('');
}

async function loadInbox() {
  try {
    const res = await fetch(`${API}/api/inbox`);
    const files = await res.json();
    state.inboxFiles = files;
    if (files.error || !files.length) {
      queueItems.innerHTML = '<div class="queue-empty">No hay archivos pendientes</div>'; return;
    }
    renderInbox(files);
  } catch (e) {}
}

async function convertFile(filename) {
  try {
    const res = await fetch(`${API}/api/convert?filename=${encodeURIComponent(filename)}`, { method: 'POST' });
    loadInbox(); await loadBrainStats(); await loadNotes();
  } catch (e) {}
}

async function transcribeFile(filename) {
  try {
    const res = await fetch(`${API}/api/transcribe?filename=${encodeURIComponent(filename)}`, { method: 'POST' });
    const data = await res.json();
    const result = document.getElementById('transcriberResult');
    if (data.transcribed && data.transcribed.length) {
      const t = data.transcribed[0];
      result.className = 'agent-result show';
      result.textContent = `✅ "${t.title}" — ${t.words} palabras, ${t.language}`;
    }
    loadInbox(); await loadBrainStats(); await loadNotes();
  } catch (e) {}
}

document.getElementById('convertAllBtn').addEventListener('click', async () => {
  try {
    const res = await fetch(`${API}/api/convert-all`, { method: 'POST' });
    const data = await res.json();
    const result = document.getElementById('transcriberResult');
    const parts = [];
    if (data.transcribed && data.transcribed.length) parts.push(`${data.transcribed.length} audio(s) transcrito(s)`);
    if (data.converted && data.converted.length) parts.push(`${data.converted.filter(x=>typeof x==='string').length} archivo(s) convertido(s)`);
    if (parts.length) { result.className = 'agent-result show'; result.textContent = '✅ ' + parts.join(' | '); }
    loadInbox(); await loadBrainStats(); await loadNotes();
  } catch (e) {}
});

// ===== AGENTS (unchanged) =====
const connectorStatus = document.getElementById('connectorStatus');
const evolverStatus = document.getElementById('evolverStatus');

async function loadAgentStatus() {
  try {
    const res = await fetch(`${API}/api/agents/status`);
    state.agents = await res.json();
    updateAgentUI();
  } catch (e) {}
}

function updateAgentUI() {
  const sb = (el, s) => { el.textContent = s === 'running' ? '▶ Ejecutando' : s === 'idle' ? '💤 Inactivo' : '⚠️ Error'; el.className = 'agent-status-badge ' + s; };
  sb(connectorStatus, state.agents.connector);
  sb(evolverStatus, state.agents.evolver);
  const dot = document.querySelector('.indicator-dot');
  dot.className = 'indicator-dot';
  if (state.agents.connector === 'running' || state.agents.evolver === 'running') {
    dot.classList.add('running'); document.querySelector('.indicator-text').textContent = 'Agentes activos';
  } else { dot.classList.add('idle'); document.querySelector('.indicator-text').textContent = 'Agentes idle'; }
  if (state.agents.last_connector_run) document.getElementById('connLastRun').textContent = new Date(state.agents.last_connector_run).toLocaleTimeString();
  if (state.agents.last_evolver_run) document.getElementById('evolvLastRun').textContent = new Date(state.agents.last_evolver_run).toLocaleTimeString();
}

document.getElementById('runConnectorBtn').addEventListener('click', async () => {
  const btn = document.getElementById('runConnectorBtn');
  const result = document.getElementById('connectorResult');
  btn.disabled = true; result.className = 'agent-result show'; result.textContent = '🔗 Ejecutando El Conector...';
  try {
    const res = await fetch(`${API}/api/agents/run-connector`, { method: 'POST' });
    const data = await res.json();
    result.textContent = `✅ Conexiones: ${data.connections_found || 0} | Clusters: ${data.clusters_created || 0} | Notas: ${data.notes_analyzed || 0}`;
    await loadAgentStatus(); await loadBrainStats(); await loadNotes();
  } catch (e) { result.textContent = '❌ Error'; }
  btn.disabled = false;
});

document.getElementById('runEvolverBtn').addEventListener('click', async () => {
  const btn = document.getElementById('runEvolverBtn');
  const result = document.getElementById('evolverResult');
  btn.disabled = true; result.className = 'agent-result show'; result.textContent = '🧬 Ejecutando El Evolucionador...';
  try {
    const res = await fetch(`${API}/api/agents/run-evolver`, { method: 'POST' });
    const data = await res.json();
    result.textContent = `✅ Insights: ${data.insights_created || 0} | Tags: ${data.tags_found || 0} | Populares: ${data.popular_tags || 0}`;
    await loadAgentStatus(); await loadBrainStats();
  } catch (e) { result.textContent = '❌ Error'; }
  btn.disabled = false;
});

document.getElementById('runTranscriberBtn').addEventListener('click', async () => {
  const btn = document.getElementById('runTranscriberBtn');
  const result = document.getElementById('transcriberResult');
  btn.disabled = true; result.className = 'agent-result show'; result.textContent = '🎤 Procesando audios con Whisper...';
  try {
    const res = await fetch(`${API}/api/transcribe`, { method: 'POST' });
    const data = await res.json();
    if (data.transcribed && data.transcribed.length) {
      result.textContent = `✅ ${data.transcribed.length} audio(s) transcrito(s)`;
    } else { result.textContent = '📭 No hay audios pendientes'; }
    await loadBrainStats(); await loadNotes(); loadInbox();
  } catch (e) { result.textContent = '❌ Error: ' + (e.message || ''); }
  btn.disabled = false;
});

// ===== BRAIN STATS =====
async function loadBrainStats() {
  try {
    const res = await fetch(`${API}/api/brain/stats`);
    const stats = await res.json();
    document.getElementById('statNotes').textContent = stats.total_notes || 0;
    document.getElementById('statConnections').textContent = stats.total_connections || 0;
    document.getElementById('statVectors').textContent = stats.total_vectors || 0;
  } catch (e) {}
}

// ===== GRAPH - Obsidian Style =====
const canvas = document.getElementById('graphCanvas');
const ctx = canvas.getContext('2d');
const graphContainer = document.querySelector('.graph-container');
let graphPhysics = [];
let graphNodes = [], graphEdges = [];
let dragNode = null, isDragging = false, dragOffX = 0, dragOffY = 0;
let viewX = 0, viewY = 0, scale = 1;
let hoverNode = null;
let animFrame = null;

function resizeGraph() {
  const rect = graphContainer.getBoundingClientRect();
  canvas.width = rect.width; canvas.height = rect.height;
}

async function loadGraph() {
  try {
    const res = await fetch(`${API}/api/brain/graph`);
    const data = await res.json();
    graphNodes = data.nodes || [];
    graphEdges = data.edges || [];

    // Cluster nodes that have no edges to center
    const connected = new Set();
    graphEdges.forEach(e => { connected.add(e.source); connected.add(e.target); });

  graphLoopStop = false;
  const w = canvas.width || 800, h = canvas.height || 600;
    graphPhysics = graphNodes.map((n, i) => {
      const hasEdges = connected.has(n.id);
      return {
        id: n.id, label: n.label || n.id,
        x: w/2 + (hasEdges ? (Math.random()-0.5)*w*0.3 : (Math.random()-0.5)*w*0.6),
        y: h/2 + (hasEdges ? (Math.random()-0.5)*h*0.3 : (Math.random()-0.5)*h*0.6),
        vx: 0, vy: 0,
        r: Math.max(4, Math.min(12, (n.size || 1) * 3)),
        hasEdges,
      };
    });
    if (animFrame) cancelAnimationFrame(animFrame);
    graphLoop();
  } catch (e) {}
}

function runGraphPhysics() {
  if (!graphPhysics.length) return;
  const rep = 8000, attr = 0.003, damp = 0.85, centerF = 0.008;
  const w = canvas.width || 800, h = canvas.height || 600;

  for (let i = 0; i < graphPhysics.length; i++) {
    let fx = 0, fy = 0;
    const a = graphPhysics[i];
    fx += (w/2 - a.x) * centerF * (a.hasEdges ? 1 : 0.3);
    fy += (h/2 - a.y) * centerF * (a.hasEdges ? 1 : 0.3);

    for (let j = i+1; j < graphPhysics.length; j++) {
      const b = graphPhysics[j];
      const dx = a.x - b.x, dy = a.y - b.y;
      const dist = Math.sqrt(dx*dx + dy*dy) || 1;
      const force = rep / (dist*dist + 50);
      fx += (dx/dist) * force; fy += (dy/dist) * force;
    }

    for (const edge of graphEdges) {
      const s = graphPhysics.findIndex(n => n.id === edge.source);
      const t = graphPhysics.findIndex(n => n.id === edge.target);
      if (s === i && t >= 0) {
        const dx = graphPhysics[t].x - a.x, dy = graphPhysics[t].y - a.y;
        fx += dx * attr; fy += dy * attr;
      }
      if (t === i && s >= 0) {
        const dx = graphPhysics[s].x - a.x, dy = graphPhysics[s].y - a.y;
        fx += dx * attr; fy += dy * attr;
      }
    }

    a.vx = (a.vx + fx) * damp; a.vy = (a.vy + fy) * damp;
    a.x += a.vx; a.y += a.vy;
  }
}

function renderGraph() {
  resizeGraph();
  const w = canvas.width, h = canvas.height;
  if (!w || !h) { animFrame = requestAnimationFrame(renderGraph); return; }

  ctx.clearRect(0, 0, w, h);
  ctx.save();
  ctx.translate(viewX, viewY);
  ctx.scale(scale, scale);

  // Draw edges - thin, elegant lines
  for (const edge of graphEdges) {
    const s = graphPhysics.find(n => n.id === edge.source);
    const t = graphPhysics.find(n => n.id === edge.target);
    if (!s || !t) continue;
    const isHighlight = hoverNode && (hoverNode.id === edge.source || hoverNode.id === edge.target);
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(t.x, t.y);
    ctx.strokeStyle = isHighlight ? 'rgba(0, 212, 255, 0.6)' : `rgba(0, 212, 255, ${0.12 + (edge.weight || 0.2) * 0.15})`;
    ctx.lineWidth = isHighlight ? 2 : (0.5 + (edge.weight || 0.2) * 0.8);
    ctx.stroke();
  }

  // Draw nodes - minimalist dots
  for (const node of graphPhysics) {
    const isHover = hoverNode && hoverNode.id === node.id;
    const isConnected = hoverNode && graphEdges.some(e =>
      (e.source === hoverNode.id && e.target === node.id) || (e.target === hoverNode.id && e.source === node.id)
    );

    ctx.beginPath();
    ctx.arc(node.x, node.y, isHover ? node.r * 1.5 : node.r, 0, Math.PI * 2);
    ctx.fillStyle = isHover ? '#00d4ff' : (isConnected ? '#a855f7' : 'rgba(200, 200, 220, 0.5)');
    ctx.fill();

    if (isHover || isConnected) {
      ctx.shadowColor = '#00d4ff';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // Label
    if (isHover || scale > 0.5) {
      ctx.fillStyle = isHover ? '#fff' : 'rgba(200, 200, 220, 0.7)';
      ctx.font = `${Math.max(9, 11)}px 'Space Grotesk', sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText(node.label.length > 25 ? node.label.slice(0, 25) + '…' : node.label,
        node.x, node.y + node.r + 14);
    }
  }

  ctx.restore();
}

function graphLoop() {
  runGraphPhysics();
  renderGraph();
  animFrame = requestAnimationFrame(graphLoop);
}

document.getElementById('refreshGraphBtn').addEventListener('click', loadGraph);

// Canvas interaction
canvas.addEventListener('mousedown', e => {
  const rect = canvas.getBoundingClientRect();
  const mx = (e.clientX - rect.left - viewX) / scale;
  const my = (e.clientY - rect.top - viewY) / scale;
  for (const node of graphPhysics) {
    const dx = mx - node.x, dy = my - node.y;
    if (dx*dx + dy*dy < (node.r*2)*(node.r*2)) {
      dragNode = node; isDragging = true;
      dragOffX = node.x - mx; dragOffY = node.y - my;
      return;
    }
  }
  isDragging = true; dragOffX = e.clientX - viewX; dragOffY = e.clientY - viewY;
});

canvas.addEventListener('mousemove', e => {
  const rect = canvas.getBoundingClientRect();
  const mx = (e.clientX - rect.left - viewX) / scale;
  const my = (e.clientY - rect.top - viewY) / scale;

  // Hover detection
  let found = null;
  for (const node of graphPhysics) {
    const dx = mx - node.x, dy = my - node.y;
    if (dx*dx + dy*dy < (node.r*3)*(node.r*3)) { found = node; break; }
  }
  hoverNode = found;
  canvas.style.cursor = found ? 'pointer' : 'grab';

  if (isDragging && dragNode) {
    dragNode.x = mx + dragOffX; dragNode.y = my + dragOffY;
  } else if (isDragging && !dragNode) {
    viewX = e.clientX - dragOffX; viewY = e.clientY - dragOffY;
  }
});

canvas.addEventListener('mouseup', () => { isDragging = false; dragNode = null; });
canvas.addEventListener('mouseleave', () => { isDragging = false; dragNode = null; hoverNode = null; });

canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const delta = e.deltaY > 0 ? 0.9 : 1.1;
  scale = Math.max(0.2, Math.min(4, scale * delta));
}, { passive: false });

canvas.addEventListener('dblclick', e => {
  const rect = canvas.getBoundingClientRect();
  const mx = (e.clientX - rect.left - viewX) / scale;
  const my = (e.clientY - rect.top - viewY) / scale;
  for (const node of graphPhysics) {
    const dx = mx - node.x, dy = my - node.y;
    if (dx*dx + dy*dy < (node.r*3)*(node.r*3)) {
      navigateToNote(node.id);
      return;
    }
  }
});

// ===== NEURAL BACKGROUND =====
const bgCanvas = document.getElementById('neuralBg');
const bgCtx = bgCanvas.getContext('2d');
let bgP = [];

function initBg() {
  bgCanvas.width = window.innerWidth; bgCanvas.height = window.innerHeight;
  bgP = Array.from({length: 50}, () => ({
    x: Math.random()*bgCanvas.width, y: Math.random()*bgCanvas.height,
    vx: (Math.random()-0.5)*0.2, vy: (Math.random()-0.5)*0.2, r: Math.random()*1.5+0.5,
  }));
}

function drawBg() {
  bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
  for (const p of bgP) {
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0 || p.x > bgCanvas.width) p.vx *= -1;
    if (p.y < 0 || p.y > bgCanvas.height) p.vy *= -1;
    bgCtx.beginPath(); bgCtx.arc(p.x, p.y, p.r, 0, Math.PI*2);
    bgCtx.fillStyle = 'rgba(0, 212, 255, 0.15)'; bgCtx.fill();
  }
  for (let i = 0; i < bgP.length; i++) {
    for (let j = i+1; j < bgP.length; j++) {
      const dx = bgP[i].x - bgP[j].x, dy = bgP[i].y - bgP[j].y;
      const d = Math.sqrt(dx*dx + dy*dy);
      if (d < 120) {
        bgCtx.beginPath(); bgCtx.moveTo(bgP[i].x, bgP[i].y); bgCtx.lineTo(bgP[j].x, bgP[j].y);
        bgCtx.strokeStyle = `rgba(0, 212, 255, ${0.03*(1-d/120)})`;
        bgCtx.lineWidth = 0.5; bgCtx.stroke();
      }
    }
  }
  requestAnimationFrame(drawBg);
}

// ===== INIT =====
async function init() {
  initBg(); drawBg();
  await loadBrainStats();
  loadAgentStatus();
  loadNotes();
  setInterval(loadBrainStats, 10000);
  setInterval(loadAgentStatus, 15000);
}
document.addEventListener('DOMContentLoaded', init);
