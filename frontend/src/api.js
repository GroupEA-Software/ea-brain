const API = '';

async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function listNotes() {
  return request('/api/notes');
}

export function getNote(filename) {
  return request(`/api/notes/${encodeURIComponent(filename)}`);
}

export function createNote(title, content = '', tags = '', folder = '') {
  return request(`/api/notes?title=${encodeURIComponent(title)}&content=${encodeURIComponent(content)}&tags=${encodeURIComponent(tags)}&folder=${encodeURIComponent(folder)}`, { method: 'POST' });
}

export function updateNote(filename, content, title) {
  let qs = `content=${encodeURIComponent(content)}`;
  if (title) qs += `&title=${encodeURIComponent(title)}`;
  return request(`/api/notes/${encodeURIComponent(filename)}?${qs}`, { method: 'PUT' });
}

export function deleteNote(filename) {
  return request(`/api/notes/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

export function moveNote(filename, folder) {
  return request(`/api/notes/${encodeURIComponent(filename)}/move?folder=${encodeURIComponent(folder)}`, { method: 'PUT' });
}

export function listFolders() {
  return request('/api/folders');
}

export function createFolder(path) {
  return request(`/api/folders?path=${encodeURIComponent(path)}`, { method: 'POST' });
}

export function exportNote(filename, format = 'md') {
  return `${API}/api/export/${encodeURIComponent(filename)}?format=${format}`;
}

export function exportVault() {
  return `${API}/api/export-vault`;
}

export function getInbox() {
  return request('/api/inbox');
}

export async function uploadFile(file, auto = false, folder = '') {
  const form = new FormData();
  form.append('file', file);
  let qs = `auto=${auto}`;
  if (folder) qs += `&folder=${encodeURIComponent(folder)}`;
  const res = await fetch(`${API}/api/inbox/upload?${qs}`, { method: 'POST', body: form });
  return res.json();
}

export function convertFile(filename) {
  return request(`/api/convert?filename=${encodeURIComponent(filename)}`, { method: 'POST' });
}

export function convertAll() {
  return request('/api/convert-all', { method: 'POST' });
}

export function transcribeFile(filename, language = '') {
  let qs = `filename=${encodeURIComponent(filename)}`;
  if (language) qs += `&language=${encodeURIComponent(language)}`;
  return request(`/api/transcribe?${qs}`, { method: 'POST' });
}

export function transcribeAll() {
  return request('/api/transcribe', { method: 'POST' });
}

export async function uploadAudio(file, language = '') {
  const form = new FormData();
  form.append('file', file);
  let qs = '';
  if (language) qs = `?language=${encodeURIComponent(language)}`;
  const res = await fetch(`${API}/api/transcribe-upload${qs}`, { method: 'POST', body: form });
  return res.json();
}

export function chat(message, history = []) {
  const hist = history.length > 0 ? `&history=${encodeURIComponent(JSON.stringify(history))}` : '';
  return request('/api/chat', {
    method: 'POST',
    body: `message=${encodeURIComponent(message)}${hist}`,
  });
}

export function search(query, k = 5) {
  return request(`/api/search?query=${encodeURIComponent(query)}&k=${k}`, { method: 'POST' });
}

export function getBrainStats() {
  return request('/api/brain/stats');
}

export function getGraph() {
  return request('/api/brain/graph');
}

export function getWikilinks(filename) {
  return request(`/api/wikilinks/${encodeURIComponent(filename)}`);
}

export function getBacklinks(filename) {
  return request(`/api/backlinks/${encodeURIComponent(filename)}`);
}

export function getAgentStatus() {
  return request('/api/agents/status');
}

export function runConnector() {
  return request('/api/agents/run-connector', { method: 'POST' });
}

export function runEvolver() {
  return request('/api/agents/run-evolver', { method: 'POST' });
}

export function rebuildIndex() {
  return request('/api/brain/rebuild', { method: 'POST' });
}

export function getHealth() {
  return request('/api/health');
}

export function getEvolutionStats() {
  return request('/api/evolution/stats');
}

export function getRepos() {
  return request('/api/repos');
}

export function checkRepoUpdates() {
  return request('/api/repos/check-updates');
}

export function connectRepo(url, branch = 'main', token = '', repoPath = '') {
  return request('/api/repos/connect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, branch, token, repo_path: repoPath }),
  });
}

export function syncRepo(repoId, token = '') {
  return request('/api/repos/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_id: repoId, token }),
  });
}

export function syncAllRepos(token = '') {
  return request('/api/repos/sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_id: 'all', token }),
  });
}

export function disconnectRepo(repoId, removeFiles = false) {
  return request(`/api/repos?repo_id=${encodeURIComponent(repoId)}&remove_files=${removeFiles}`, { method: 'DELETE' });
}

// ── Knowledge Library (01-07 directories) ──

export function listKnowledge() {
  return request('/api/knowledge');
}

export function getKnowledgeNote(filename) {
  return request(`/api/knowledge/${encodeURIComponent(filename)}`);
}

// ── Chat download (PDF via backend) ──

export async function downloadChatPdf(content, filename = '') {
  const res = await fetch(`${API}/api/chat/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, format: 'pdf', filename }),
  });
  if (!res.ok) throw new Error(`PDF download failed: ${res.status}`);

  // Extract filename from Content-Disposition header, or fallback
  const cd = res.headers.get('Content-Disposition') || '';
  const match = cd.match(/filename="?([^";\n]+)"?/);
  const dlName = match ? match[1] : `EAgis-${Date.now()}.${res.headers.get('Content-Type')?.includes('pdf') ? 'pdf' : 'html'}`;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = dlName;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Personality (EAgis state) ──

export function getPersonality() {
  return request('/api/personality');
}

export function resetPersonality() {
  return request('/api/personality/reset', { method: 'POST' });
}
