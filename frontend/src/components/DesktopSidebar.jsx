import React from 'react';
import '../styles/desktop-sidebar.css';

const TABS = [
  { id: 'chat', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>', label: 'Chat' },
  { id: 'notes', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>', label: 'Baúl' },
  { id: 'graph', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><circle cx="5" cy="19" r="2"/><line x1="12" y1="9" x2="17.5" y2="6.5"/><line x1="12" y1="9" x2="6.5" y2="6.5"/><line x1="12" y1="15" x2="17.5" y2="17.5"/><line x1="12" y1="15" x2="6.5" y2="6.5"/></svg>', label: 'Grafo' },
  { id: 'knowledge', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><line x1="8" y1="7" x2="16" y2="7"/><line x1="8" y1="11" x2="14" y2="11"/></svg>', label: 'Biblioteca' },
  { id: 'inbox', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>', label: 'Inbox' },
  { id: 'repos', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>', label: 'Repos' },
  { id: 'agents', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>', label: 'Agentes' },
  { id: 'personality', icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>', label: 'Personalidad' },
];

export default function DesktopSidebar({ activeView, stats, agents, repoUpdates, knowledgeTotal, onNavigate }) {
  const agentRunning = agents.connector === 'running' || agents.evolver === 'running';

  return (
    <aside className="desktop-sidebar">
      <div className="ds-logo">
        <span className="ds-logo-icon">🧠</span>
        <div className="ds-logo-text">
          <span className="ds-logo-title">EA-Brain</span>
          <span className="ds-logo-sub">Digital Brain</span>
        </div>
      </div>

      <nav className="ds-nav">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`ds-nav-item${activeView === tab.id ? ' active' : ''}`}
            onClick={() => onNavigate(tab.id)}
          >
            <span className="ds-nav-icon" dangerouslySetInnerHTML={{ __html: tab.icon }} />
            <span className="ds-nav-label">{tab.label}</span>
            {tab.id === 'repos' && repoUpdates > 0 && (
              <span className="ds-nav-badge">{repoUpdates}</span>
            )}
            {tab.id === 'knowledge' && knowledgeTotal > 0 && (
              <span className="ds-nav-badge">{knowledgeTotal}</span>
            )}
          </button>
        ))}
      </nav>

      <div className="ds-footer">
        <div className="ds-stats">
          <div className="ds-stat">
            <span className="ds-stat-val">{stats.total_notes || 0}</span>
            <span className="ds-stat-lbl">Notas</span>
          </div>
          <div className="ds-stat">
            <span className="ds-stat-val">{knowledgeTotal || 0}</span>
            <span className="ds-stat-lbl">Biblioteca</span>
          </div>
          <div className="ds-stat">
            <span className="ds-stat-val">{stats.total_vectors || 0}</span>
            <span className="ds-stat-lbl">Vec</span>
          </div>
        </div>
        <div className="ds-agent">
          <span className={`ds-agent-dot ${agentRunning ? 'running' : 'idle'}`} />
          <span className="ds-agent-text">{agentRunning ? 'Agentes activos' : 'Inactivo'}</span>
        </div>
      </div>
    </aside>
  );
}
