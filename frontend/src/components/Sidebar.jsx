import React from 'react';
import '../styles/sidebar.css';

const NAV_ITEMS = [
  { id: 'chat', icon: '💬', label: 'Chat' },
  { id: 'notes', icon: '📝', label: 'Baúl' },
  { id: 'graph', icon: '🕸️', label: 'Grafo' },
  { id: 'inbox', icon: '📥', label: 'Inbox' },
  { id: 'agents', icon: '🤖', label: 'Agentes' },
];

export default function Sidebar({ activeView, collapsed, stats, agents, onNavigate, onToggle }) {
  const agentRunning = agents.connector === 'running' || agents.evolver === 'running';

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">🧠</span>
          {!collapsed && (
            <div>
              <span className="logo-title">EA-Brain</span>
              <span className="logo-subtitle">Digital Brain</span>
            </div>
          )}
        </div>
        <button className="sidebar-toggle" onClick={onToggle} title={collapsed ? 'Expandir' : 'Colapsar'}>
          {collapsed ? '☰' : '✕'}
        </button>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(item => (
          <button
            key={item.id}
            className={`nav-item${activeView === item.id ? ' active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            {!collapsed && <span className="nav-label">{item.label}</span>}
          </button>
        ))}
      </nav>

      {!collapsed && (
        <div className="sidebar-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.total_notes || 0}</span>
            <span className="stat-label">Baúl</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.total_connections || 0}</span>
            <span className="stat-label">Conx</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.total_vectors || 0}</span>
            <span className="stat-label">Vec</span>
          </div>
        </div>
      )}

      {!collapsed && (
        <div className="sidebar-footer">
          <div className="agent-indicator">
            <span className={`indicator-dot ${agentRunning ? 'running' : 'idle'}`} />
            <span className="indicator-text">{agentRunning ? 'Agentes activos' : 'Agentes idle'}</span>
          </div>
        </div>
      )}
    </aside>
  );
}
