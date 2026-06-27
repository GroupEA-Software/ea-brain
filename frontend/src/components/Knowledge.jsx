import React, { useState, useEffect } from 'react';
import { listKnowledge, getKnowledgeNote } from '../api';
import '../styles/knowledge.css';

function formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + 'B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + 'KB';
  return (bytes / 1048576).toFixed(1) + 'MB';
}

function renderMD(text) {
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/\[\[([^\]]+)\]\]/g, '<span class="knowledge-wikilink">$1</span>');
  html = html.replace(/^###### (.+)$/gm, '<h6>$1</h6>');
  html = html.replace(/^##### (.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.+?)`/g, '<code>$1</code>');
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  html = html.replace(/^---$/gm, '<hr>');
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

export default function Knowledge() {
  const [categories, setCategories] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedCat, setExpandedCat] = useState(null);
  const [currentNote, setCurrentNote] = useState(null);

  useEffect(() => {
    loadKnowledge();
  }, []);

  const loadKnowledge = async () => {
    setLoading(true);
    try {
      const data = await listKnowledge();
      setCategories(data.categories || []);
      setTotal(data.total || 0);
    } catch {
      setCategories([]);
    }
    setLoading(false);
  };

  const openNote = async (filename) => {
    try {
      const note = await getKnowledgeNote(filename);
      setCurrentNote(note);
    } catch {
      setCurrentNote(null);
    }
  };

  const toggleCategory = (name) => {
    setExpandedCat(expandedCat === name ? null : name);
    setCurrentNote(null);
  };

  // Search across all files
  const allFiles = categories.flatMap(cat =>
    (cat.files || []).map(f => ({ ...f, category: cat.name }))
  );

  const filteredFiles = search
    ? allFiles.filter(f =>
        f.title.toLowerCase().includes(search.toLowerCase()) ||
        f.path.toLowerCase().includes(search.toLowerCase())
      )
    : [];

  if (loading) {
    return (
      <div className="view">
        <div className="view-header"><h2>Biblioteca de Conocimiento</h2></div>
        <div className="knowledge-loading">Cargando biblioteca...</div>
      </div>
    );
  }

  return (
    <div className="view">
      <div className="view-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2>Biblioteca de Conocimiento</h2>
            <p className="view-desc">{total} documentos en {categories.length} categorías — Cerebro-Digital</p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={loadKnowledge}>
            ↻ Recargar
          </button>
        </div>
      </div>

      <div className="knowledge-layout">
        <div className="knowledge-sidebar">
          <div className="knowledge-search">
            <input
              className="search-input"
              placeholder="Buscar en toda la biblioteca..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          {search ? (
            <div className="knowledge-search-results">
              <p className="knowledge-search-count">{filteredFiles.length} resultados</p>
              {filteredFiles.map(f => (
                <div
                  key={f.filename}
                  className={`knowledge-file${currentNote?.filename === f.filename ? ' active' : ''}`}
                  onClick={() => openNote(f.filename)}
                >
                  <span className="knowledge-file-cat">{f.category.split(' - ')[0]}</span>
                  <span className="knowledge-file-title">{f.title}</span>
                </div>
              ))}
              {filteredFiles.length === 0 && (
                <p className="knowledge-empty">Sin resultados para "{search}"</p>
              )}
            </div>
          ) : (
            <div className="knowledge-categories">
              {categories.map(cat => (
                <div key={cat.name} className="knowledge-category">
                  <div
                    className={`knowledge-cat-header${expandedCat === cat.name ? ' expanded' : ''}`}
                    onClick={() => toggleCategory(cat.name)}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="knowledge-cat-arrow">
                      <polyline points="9 18 15 12 9 6"/>
                    </svg>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span className="knowledge-cat-name">{cat.name}</span>
                    <span className="knowledge-cat-count">{cat.total}</span>
                  </div>
                  {expandedCat === cat.name && (
                    <div className="knowledge-cat-files">
                      {cat.files.map(f => (
                        <div
                          key={f.filename}
                          className={`knowledge-file${currentNote?.filename === f.filename ? ' active' : ''}`}
                          onClick={() => openNote(f.filename)}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.6 }}>
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                          </svg>
                          <div className="knowledge-file-info">
                            <span className="knowledge-file-title">{f.title}</span>
                            <span className="knowledge-file-meta">{formatSize(f.size)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="knowledge-reader">
          {currentNote ? (
            <div className="knowledge-note">
              <div className="knowledge-note-header">
                <div className="knowledge-note-title-row">
                  <h2>{currentNote.title}</h2>
                  {currentNote.readonly && (
                    <span className="badge badge-knowledge">📚 Biblioteca</span>
                  )}
                </div>
                <div className="knowledge-note-meta">
                  {currentNote.category && (
                    <span className="knowledge-note-cat">{currentNote.category}</span>
                  )}
                  {currentNote.tags?.length > 0 && currentNote.tags.map(t => (
                    <span key={t} className="tag">#{t}</span>
                  ))}
                </div>
              </div>
              <div
                className="knowledge-note-content markdown-content"
                dangerouslySetInnerHTML={{ __html: renderMD(currentNote.content) }}
              />
            </div>
          ) : (
            <div className="knowledge-empty-state">
              <div className="knowledge-empty-icon">📚</div>
              <h3>Biblioteca de Conocimiento</h3>
              <p>Explorá las categorías a la izquierda o buscá un tema específico.</p>
              <p className="knowledge-empty-sub">
                {total} documentos técnicos organizados por área de conocimiento.
              </p>
              <div className="knowledge-stats">
                {categories.slice(0, 4).map(cat => (
                  <div key={cat.name} className="knowledge-stat-card" onClick={() => setExpandedCat(cat.name)}>
                    <div className="knowledge-stat-count">{cat.total}</div>
                    <div className="knowledge-stat-label">{cat.name.split(' - ').pop()}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
