import React, { useState, useEffect } from 'react';
import { getRepos, connectRepo, syncRepo, disconnectRepo } from '../api';
import '../styles/repos.css';

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function RepoCard({ repo, onSync, onDisconnect, syncing }) {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div className={`repo-card${repo.pending_update ? ' has-update' : ''}`}>
      <div className="repo-card-header">
        <div className="repo-info">
          <div className="repo-name">{repo.url.split('/').slice(-2).join('/').replace('.git', '')}</div>
          <div className="repo-url">{repo.url}</div>
        </div>
        <div className="repo-status">
          {repo.pending_update && <span className="repo-badge-update">Actualización disponible</span>}
          <span className="repo-branch">{repo.branch}</span>
        </div>
      </div>
      <div className="repo-card-body">
        <div className="repo-metrics">
          <div className="repo-metric">
            <span className="repo-metric-val">{repo.files_count ?? '?'}</span>
            <span className="repo-metric-lbl">Archivos</span>
          </div>
          <div className="repo-metric">
            <span className="repo-metric-val">{formatDate(repo.last_sync)}</span>
            <span className="repo-metric-lbl">Último sync</span>
          </div>
        </div>
        <div className="repo-actions">
          <button className="btn btn-primary btn-sm" onClick={() => onSync(repo.id)} disabled={syncing}>
            {syncing ? '⏳ Sincronizando...' : repo.pending_update ? '🔄 Actualizar' : '🔄 Sincronizar'}
          </button>
          {!showConfirm ? (
            <button className="btn btn-danger btn-sm" onClick={() => setShowConfirm(true)}>
              Desconectar
            </button>
          ) : (
            <div className="repo-confirm">
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>¿Desconectar?</span>
              <button className="btn btn-danger btn-sm" onClick={() => { onDisconnect(repo.id); setShowConfirm(false); }}>
                Sí
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowConfirm(false)}>
                No
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Repos({ onDone }) {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ url: '', branch: 'main', token: '', repoPath: '' });
  const [formBusy, setFormBusy] = useState(false);
  const [formError, setFormError] = useState('');
  const [message, setMessage] = useState('');

  const loadRepos = async () => {
    try { setRepos(await getRepos()); } catch {}
  };

  useEffect(() => { loadRepos(); }, []);

  const handleConnect = async () => {
    if (!form.url.trim()) return;
    setFormBusy(true);
    setFormError('');
    setMessage('');
    try {
      const result = await connectRepo(form.url.trim(), form.branch, form.token, form.repoPath);
      setMessage(`✅ Repositorio conectado — ${result.files_imported} archivos importados`);
      setShowForm(false);
      setForm({ url: '', branch: 'main', token: '', repoPath: '' });
      await loadRepos();
      if (onDone) onDone();
    } catch (e) {
      setFormError(e.message || 'Error al conectar');
    }
    setFormBusy(false);
  };

  const handleSync = async (repoId) => {
    setSyncing(repoId);
    setMessage('');
    try {
      const result = await syncRepo(repoId);
      setMessage(result.files_imported > 0
        ? `✅ ${result.files_imported} archivo(s) actualizado(s)`
        : '✅ Sin cambios — ya está al día');
      await loadRepos();
      if (onDone) onDone();
    } catch (e) {
      setMessage(`❌ ${e.message || 'Error al sincronizar'}`);
    }
    setSyncing(null);
  };

  const handleDisconnect = async (repoId) => {
    try {
      await disconnectRepo(repoId, false);
      setMessage('Repositorio desconectado');
      await loadRepos();
    } catch (e) {
      setMessage(`❌ ${e.message || 'Error al desconectar'}`);
    }
  };

  return (
    <div className="view">
      <div className="view-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2>📦 Repos</h2>
            <p className="view-desc">Conectá repositorios GitHub con notas en Markdown</p>
          </div>
          <div className="view-actions">
            <button className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
              {showForm ? '✕ Cancelar' : '+ Conectar repo'}
            </button>
          </div>
        </div>
      </div>

      <div className="repos-content">
        {message && (
          <div className="repo-message" onClick={() => setMessage('')}>{message}</div>
        )}

        {showForm && (
          <div className="repo-form">
            <h3>Conectar repositorio</h3>
            <div className="repo-form-row">
              <label>URL del repo *</label>
              <input
                type="text"
                value={form.url}
                onChange={e => setForm({ ...form, url: e.target.value })}
                placeholder="https://github.com/usuario/repositorio"
                className="repo-input"
              />
            </div>
            <div className="repo-form-row">
              <label>Rama</label>
              <input
                type="text"
                value={form.branch}
                onChange={e => setForm({ ...form, branch: e.target.value })}
                placeholder="main"
                className="repo-input"
              />
            </div>
            <div className="repo-form-row">
              <label>Carpeta dentro del repo (opcional)</label>
              <input
                type="text"
                value={form.repoPath}
                onChange={e => setForm({ ...form, repoPath: e.target.value })}
                placeholder="docs/notas"
                className="repo-input"
              />
            </div>
            <div className="repo-form-row">
              <label>Token (opcional, para repos privados)</label>
              <input
                type="password"
                value={form.token}
                onChange={e => setForm({ ...form, token: e.target.value })}
                placeholder="ghp_..."
                className="repo-input"
              />
            </div>
            {formError && <div className="repo-error">{formError}</div>}
            <button className="btn btn-primary" onClick={handleConnect} disabled={formBusy || !form.url.trim()}>
              {formBusy ? '⏳ Clonando e importando...' : 'Conectar e importar'}
            </button>
          </div>
        )}

        {repos.length === 0 && !showForm ? (
          <div className="repos-empty">
            <div className="repos-empty-icon">📦</div>
            <p>No hay repositorios conectados todavía.</p>
            <p className="repos-empty-sub">Conectá un repo de GitHub con notas en Markdown para expandir tu Baúl automáticamente.</p>
          </div>
        ) : (
          <div className="repos-list">
            {repos.map(repo => (
              <RepoCard
                key={repo.id}
                repo={repo}
                onSync={handleSync}
                onDisconnect={handleDisconnect}
                syncing={syncing === repo.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
