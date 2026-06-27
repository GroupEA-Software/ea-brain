import React, { useState, useEffect, useCallback } from 'react';
import { listNotes, getNote, createNote, updateNote, deleteNote, moveNote, getWikilinks, getBacklinks, rebuildIndex, listFolders, createFolder, exportNote, exportVault } from '../api';
import NoteEditor from './NoteEditor';
import '../styles/notes.css';

function buildTree(notes, folders) {
  const tree = {};
  for (const f of (folders || [])) {
    const parts = f.split('/');
    let current = tree;
    for (let i = 0; i < parts.length; i++) {
      if (!current[parts[i]]) current[parts[i]] = { _files: [] };
      current = current[parts[i]];
    }
  }
  for (const n of notes) {
    const parts = n.filename.split('/');
    let current = tree;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!current[parts[i]]) current[parts[i]] = { _files: [] };
      current = current[parts[i]];
    }
    if (!current._files) current._files = [];
    current._files.push(n);
  }

  // Sort folders and files alphabetically (case-insensitive) like VSCode
  function sortTree(node) {
    if (node._files) {
      node._files.sort((a, b) => a.title.toLowerCase().localeCompare(b.title.toLowerCase()));
    }
    for (const [key, val] of Object.entries(node)) {
      if (key !== '_files') {
        sortTree(val);
      }
    }
  }
  sortTree(tree);

  return tree;
}

function countFiles(subtree) {
  let c = (subtree._files || []).length;
  for (const [k, v] of Object.entries(subtree)) {
    if (k !== '_files') c += countFiles(v);
  }
  return c;
}

function FolderTree({ tree, path, activeNote, onOpen, onNewHere, onMoveNote, dragOver, setDragOver, collapsed, toggleCollapse }) {
  const entries = Object.entries(tree).filter(([k]) => k !== '_files');
  const files = tree._files || [];

  const handleDragStart = (e, filename) => {
    e.dataTransfer.setData('text/plain', filename);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, folderPath) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOver(folderPath);
  };

  const handleDragLeave = () => {
    setDragOver(null);
  };

  const handleDrop = (e, folderPath) => {
    e.preventDefault();
    setDragOver(null);
    const filename = e.dataTransfer.getData('text/plain');
    if (filename) {
      onMoveNote(filename, folderPath || '');
    }
  };

  return (
    <div className="folder-tree">
      {entries.map(([name, subtree]) => {
        const fullPath = path ? `${path}/${name}` : name;
        const isOver = dragOver === fullPath;
        const isCollapsed = collapsed.has(fullPath);
        const fileCount = countFiles(subtree);
        return (
          <div key={name} className="tree-folder">
            <div
              className={`tree-folder-label${isOver ? ' drag-over' : ''}`}
              onDragOver={(e) => handleDragOver(e, fullPath)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, fullPath)}
              onClick={() => toggleCollapse(fullPath)}
            >
              <span className={`tree-folder-arrow${isCollapsed ? ' collapsed' : ''}`}>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
              </span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              <span className="tree-folder-name">{name}</span>
            </div>
            {!isCollapsed && (
              <div className="tree-folder-children">
                <FolderTree tree={subtree} path={fullPath} activeNote={activeNote} onOpen={onOpen} onNewHere={onNewHere} onMoveNote={onMoveNote} dragOver={dragOver} setDragOver={setDragOver} collapsed={collapsed} toggleCollapse={toggleCollapse} />
              </div>
            )}
          </div>
        );
      })}
      {files.map(n => (
        <div
          key={n.filename}
          className={`tree-file${activeNote?.filename === n.filename ? ' active' : ''}`}
          onClick={() => onOpen(n.filename)}
          draggable
          onDragStart={(e) => handleDragStart(e, n.filename)}
          title={n.filename}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.7 }}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span className="tree-file-title">{n.title}</span>
        </div>
      ))}
    </div>
  );
}

export default function Notes({ notes, setNotes }) {
  const [query, setQuery] = useState('');
  const [currentNote, setCurrentNote] = useState(null);
  const [links, setLinks] = useState({ outgoing: [], backlinks: [] });
  const [folders, setFolders] = useState([]);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [dragOver, setDragOver] = useState(null);
  const [collapsed, setCollapsed] = useState(new Set());
  const [mobileEditor, setMobileEditor] = useState(false);

  const loadNotes = useCallback(async () => {
    try { setNotes(await listNotes()); } catch (_) {}
  }, [setNotes]);

  const loadFolders = useCallback(async () => {
    try { setFolders(await listFolders()); } catch (_) {}
  }, []);

  useEffect(() => { loadNotes(); loadFolders(); }, [loadNotes, loadFolders]);

  const filtered = query
    ? notes.filter(n =>
        n.title.toLowerCase().includes(query.toLowerCase()) ||
        n.filename.toLowerCase().includes(query.toLowerCase())
      )
    : notes;

  const tree = buildTree(notes, folders);

  const toggleCollapse = (path) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const openNote = async (filename) => {
    try {
      const note = await getNote(filename);
      setCurrentNote(note);
      const [l, b] = await Promise.all([
        getWikilinks(filename),
        getBacklinks(filename),
      ]);
      setLinks({
        outgoing: (l.links || []).filter(x => x.exists),
        backlinks: b.backlinks || [],
      });
      setMobileEditor(true);
    } catch (_) {}
  };

  const handleSave = async (filename, content, title) => {
    await updateNote(filename, content, title);
    if (currentNote) setCurrentNote(prev => ({ ...prev, content, title }));
    await loadNotes();
  };

  const handleDelete = async (filename) => {
    if (!window.confirm('Eliminar esta nota?')) return;
    await deleteNote(filename);
    setCurrentNote(null);
    setMobileEditor(false);
    await loadNotes();
  };

  const handleNew = async (folderPath = '') => {
    const title = window.prompt('Titulo de la nueva nota:' + (folderPath ? ` (en ${folderPath})` : ''));
    if (!title) return;
    const result = await createNote(title, '', '', folderPath);
    await loadNotes();
    const notes = await listNotes();
    setNotes(notes);
    const newName = result?.filename || title.replace(/\s+/g, '_') + '.md';
    setTimeout(() => openNote(newName), 100);
  };

  const handleMoveNote = async (filename, targetFolder) => {
    try {
      await moveNote(filename, targetFolder);
      if (currentNote?.filename === filename) {
        setCurrentNote(null);
      }
      await loadNotes();
    } catch (_) {}
  };

  const handleNewFolder = async () => {
    if (!newFolderName.trim()) return;
    await createFolder(newFolderName.trim());
    setNewFolderName('');
    setShowNewFolder(false);
    await loadFolders();
    await loadNotes();
  };

  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + 'B';
    return (bytes / 1024).toFixed(1) + 'KB';
  };

  return (
    <div className="view">
      <div className="view-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            {mobileEditor ? (
              <div className="notes-mobile-back" onClick={() => setMobileEditor(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                <span>Baúl</span>
              </div>
            ) : (
              <>
                <h2>Baúl</h2>
                <p className="view-desc">{notes.length} notas en el cerebro</p>
              </>
            )}
          </div>
          <div className="view-actions">
            {!mobileEditor && (
              <>
                <button className="btn btn-primary btn-sm" onClick={() => handleNew()}>+ Nueva</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowNewFolder(!showNewFolder)}>Nueva Carpeta</button>
                <button className="btn btn-secondary btn-sm" onClick={async () => {
                  try { await rebuildIndex(); } catch (_) {}
                }}>Reindexar</button>
                <a className="btn btn-secondary btn-sm" href={exportVault()} download style={{ textDecoration: 'none' }}>Exportar (.zip)</a>
              </>
            )}
          </div>
        </div>
        {showNewFolder && !mobileEditor && (
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input className="search-input" placeholder="Nombre de la carpeta (ej: mysql/apuntes)" value={newFolderName} onChange={e => setNewFolderName(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleNewFolder()} style={{ flex: 1 }} />
            <button className="btn btn-primary" onClick={handleNewFolder}>Crear</button>
          </div>
        )}
      </div>
      <div className={`notes-layout${mobileEditor ? ' showing-editor' : ''}`}>
        <div className="notes-list">
          <div className="notes-list-header">
            <input
              className="search-input"
              placeholder="Buscar notas..."
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          </div>
          <div className="notes-items">
            {query ? (
              filtered.map(n => (
                <div
                  key={n.filename}
                  className={`note-item${currentNote?.filename === n.filename ? ' active' : ''}`}
                  onClick={() => openNote(n.filename)}
                >
                  <div className="note-item-title">{n.title}</div>
                  <div className="note-item-meta">
                    {new Date(n.modified).toLocaleDateString()} &bull; {formatSize(n.size)}
                    {n.folder && <span className="note-folder-badge">{n.folder}</span>}
                  </div>
                </div>
              ))
            ) : (
              <FolderTree
                tree={tree}
                path=""
                activeNote={currentNote}
                onOpen={openNote}
                onNewHere={handleNew}
                onMoveNote={handleMoveNote}
                dragOver={dragOver}
                setDragOver={setDragOver}
                collapsed={collapsed}
                toggleCollapse={toggleCollapse}
              />
            )}
          </div>
        </div>
        <NoteEditor
          note={currentNote}
          links={links}
          onSave={handleSave}
          onDelete={handleDelete}
          onNavigate={openNote}
          exportNote={exportNote}
          onBack={() => setMobileEditor(false)}
        />
      </div>
    </div>
  );
}
