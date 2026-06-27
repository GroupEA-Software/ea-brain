import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getInbox, uploadFile, convertFile, transcribeFile, convertAll, transcribeAll } from '../api';
import '../styles/inbox.css';

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  if (['mp3', 'wav', 'm4a', 'ogg', 'flac', 'wma', 'aac', 'webm'].includes(ext)) return '🎤';
  if (['pdf'].includes(ext)) return '📕';
  if (['docx', 'doc'].includes(ext)) return '📘';
  if (['pptx', 'ppt'].includes(ext)) return '📙';
  if (['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'].includes(ext)) return '🖼️';
  if (['html', 'htm'].includes(ext)) return '🌐';
  return '📄';
}

function formatSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return bytes + 'B';
  return (bytes / 1024).toFixed(1) + 'KB';
}

export default function Inbox({ onProcessed }) {
  const [files, setFiles] = useState([]);
  const [filter, setFilter] = useState('all');
  const [dragging, setDragging] = useState(false);
  const [uploadFolder, setUploadFolder] = useState('');
  const fileInputRef = useRef(null);

  const loadInbox = useCallback(async () => {
    try {
      const data = await getInbox();
      setFiles(data.error || !data.length ? [] : data);
    } catch (_) { setFiles([]); }
  }, []);

  useEffect(() => { loadInbox(); }, [loadInbox]);

  const handleUpload = async (fileList) => {
    for (const file of fileList) {
      const ext = file.name.split('.').pop().toLowerCase();
      const auto = ['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'webp'].includes(ext);
      try { await uploadFile(file, auto, uploadFolder); } catch (_) {}
    }
    await loadInbox();
    if (onProcessed) onProcessed();
  };

  const filtered = filter === 'all' ? files : files.filter(f => f.type === filter);

  return (
    <div className="view">
      <div className="view-header">
        <h2>📥 Inbox</h2>
        <p className="view-desc">Sube archivos para convertir o transcribir</p>
      </div>
      <div className="inbox-layout">
        <div className="inbox-left">
          <div
            className={`drop-zone${dragging ? ' dragover' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleUpload(e.dataTransfer.files); }}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="drop-zone-content">
              <span className="drop-icon">📄</span>
              <p>Arrastra archivos aquí o haz clic para seleccionar</p>
              <p className="drop-hint">PDF, DOCX, PPTX, imágenes, audio...</p>
              <div className="drop-folder-row">
                <input
                  className="drop-folder-input"
                  type="text"
                  value={uploadFolder}
                  onChange={e => setUploadFolder(e.target.value)}
                  placeholder="Carpeta destino (ej: fisica, img/programacion)"
                />
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                style={{ display: 'none' }}
                onChange={e => { handleUpload(e.target.files); e.target.value = ''; }}
              />
              <button className="btn btn-secondary" onClick={e => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                📁 Seleccionar archivos
              </button>
            </div>
          </div>

          <div
            className="drop-zone-audio"
            onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--accent-purple)'; }}
            onDragLeave={e => { e.currentTarget.style.borderColor = ''; }}
            onDrop={e => { e.preventDefault(); e.currentTarget.style.borderColor = ''; handleUpload(e.dataTransfer.files); }}
          >
            <div className="drop-zone-content">
              <span className="drop-icon">🎤</span>
              <p>Arrastra audios aquí para transcripción Whisper</p>
              <p className="drop-hint">MP3, WAV, M4A, OGG, FLAC...</p>
              <button className="btn btn-secondary" onClick={e => {
                e.stopPropagation();
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.mp3,.wav,.m4a,.ogg,.flac,.wma,.aac,.webm';
                input.multiple = true;
                input.onchange = () => { handleUpload(input.files); };
                input.click();
              }}>🎤 Seleccionar audio</button>
            </div>
          </div>

          <div className="view-actions">
            <button className="btn btn-primary" onClick={async () => {
              try {
                await convertAll();
                await transcribeAll();
                await loadInbox();
                if (onProcessed) onProcessed();
              } catch (_) {}
            }}>⚡ Convertir Todos</button>
          </div>
        </div>

        <div className="inbox-queue">
          <div className="queue-tabs">
            {['all', 'document', 'audio'].map(t => (
              <button
                key={t}
                className={`queue-tab${filter === t ? ' active' : ''}`}
                onClick={() => setFilter(t)}
              >
                {t === 'all' ? 'Todos' : t === 'document' ? 'Documentos' : 'Audios'}
              </button>
            ))}
          </div>

          <div className="queue-header">
            <h3>Archivos</h3>
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{filtered.length} archivos</span>
          </div>

          <div className="queue-items">
            {!filtered.length ? (
              <div className="queue-empty">No hay archivos pendientes</div>
            ) : (
              filtered.map(f => {
                const isAudio = f.type === 'audio';
                return (
                  <div key={f.filename} className="inbox-file-item">
                    <span className="file-icon">{getFileIcon(f.filename)}</span>
                    <span className="file-name">{f.filename}</span>
                    <span className={`file-type-badge ${isAudio ? 'file-type-audio' : 'file-type-document'}`}>
                      {isAudio ? 'Audio' : 'Documento'}
                    </span>
                    <span className="file-size">{formatSize(f.size)}</span>
                    {isAudio ? (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: 11, background: 'rgba(168,85,247,0.15)', borderColor: 'rgba(168,85,247,0.3)' }}
                        onClick={async () => { await transcribeFile(f.filename); await loadInbox(); if (onProcessed) onProcessed(); }}
                      >🎤 Transcribir</button>
                    ) : (
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: 11 }}
                        onClick={async () => { await convertFile(f.filename); await loadInbox(); if (onProcessed) onProcessed(); }}
                      >📝 Convertir</button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
