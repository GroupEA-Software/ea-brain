import React, { useState, useEffect } from 'react';

function renderMD(text) {
  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/\[\[([^\]]+)\]\]/g, '<a class="wikilink">$1</a>');
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
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="note-img" loading="lazy" />');
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

export default function NoteEditor({ note, links, onSave, onDelete, onNavigate, exportNote, onBack }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [preview, setPreview] = useState(false);

  useEffect(() => {
    if (note) { setTitle(note.title); setContent(note.content); setPreview(false); }
  }, [note]);

  if (!note) {
    return (
      <div className="note-editor">
        <div className="note-editor-empty">
          <span className="empty-icon">📝</span>
          <p>Selecciona o crea una nota</p>
        </div>
      </div>
    );
  }

  return (
    <div className="note-editor">
      <div className="note-editor-tabs">
        {onBack && (
          <button className="note-editor-back btn btn-secondary" onClick={onBack} aria-label="Volver">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
        )}
        <input
          className="note-title-input"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Titulo de la nota"
        />
        <button className="btn btn-secondary btn-sm" onClick={() => setPreview(!preview)}>
          {preview ? '✏️ Editar' : '👁️ Vista previa'}
        </button>
      </div>

      {preview ? (
        <div className="note-preview" dangerouslySetInnerHTML={{ __html: renderMD(content) }} />
      ) : (
        <textarea
          className="note-body-input"
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="Escribe tu nota en Markdown..."
        />
      )}

      <div className="note-links">
        <div className="note-outlinks">
          {links.outgoing.length > 0 ? (
            <>
              <strong>Conexiones:</strong>{' '}
              {links.outgoing.map((l, i) => (
                <span key={i}>
                  {i > 0 && ' • '}
                  <a className="wikilink" onClick={() => onNavigate(l.filename)}>{l.wikilink}</a>
                </span>
              ))}
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Sin conexiones salientes</span>
          )}
        </div>
        <div className="note-backlinks">
          {links.backlinks.length > 0 ? (
            <>
              <strong>Backlinks:</strong>{' '}
              {links.backlinks.map((l, i) => (
                <span key={i}>
                  {i > 0 && ' • '}
                  <a className="wikilink" onClick={() => onNavigate(l.filename)}>{l.title}</a>
                </span>
              ))}
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Sin backlinks</span>
          )}
        </div>
      </div>

      <div className="note-editor-toolbar">
        <span className="note-filename">{note.filename}</span>
        <div className="toolbar-actions">
          {exportNote && (
            <>
              <a className="btn btn-secondary" href={exportNote(note.filename, 'md')} download style={{ textDecoration: 'none', padding: '4px 10px', fontSize: 12 }}>.md</a>
              <a className="btn btn-secondary" href={exportNote(note.filename, 'html')} target="_blank" rel="noopener" style={{ textDecoration: 'none', padding: '4px 10px', fontSize: 12 }}>HTML</a>
              <a className="btn btn-secondary" href={exportNote(note.filename, 'pdf')} target="_blank" rel="noopener" style={{ textDecoration: 'none', padding: '4px 10px', fontSize: 12 }}>PDF</a>
            </>
          )}
          <button className="btn btn-primary" onClick={() => onSave(note.filename, content, title)}>Guardar</button>
          <button className="btn btn-danger" onClick={() => onDelete(note.filename)}>Eliminar</button>
        </div>
      </div>
    </div>
  );
}
