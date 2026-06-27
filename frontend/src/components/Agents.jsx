import React, { useEffect, useState } from 'react';
import { runConnector, runEvolver, transcribeAll, getAgentStatus, getEvolutionStats } from '../api';
import '../styles/agents.css';

function AgentCard({ type, icon, name, desc, status, lastRun, onRun, result }) {
  const statusText = status === 'running' ? '▶ Ejecutando' : status === 'idle' ? '💤 Inactivo' : '⚠️ Error';
  return (
    <div className={`agent-card ${type}`}>
      <div className="agent-header">
        <span className="agent-icon">{icon}</span>
        <div className="agent-info">
          <h3>{name}</h3>
          <p>{desc}</p>
        </div>
        <span className={`agent-status-badge ${status}`}>{statusText}</span>
      </div>
      <div className="agent-body">
        <div className="agent-metrics">
          <div className="metric">
            <span className="metric-value">{status}</span>
            <span className="metric-label">Estado</span>
          </div>
          <div className="metric">
            <span className="metric-value">{lastRun || '—'}</span>
            <span className="metric-label">Última ejecución</span>
          </div>
        </div>
        <button className={`btn ${status === 'running' ? 'btn-secondary' : 'btn-primary'}`} onClick={onRun} disabled={status === 'running'}>
          {status === 'running' ? '⏳ Procesando...' : `▶ Ejecutar ${name}`}
        </button>
        <div className={`agent-result${result ? ' show' : ''}`}>{result}</div>
      </div>
    </div>
  );
}

export default function Agents({ agents, setAgents, onDone }) {
  const [results, setResults] = useState({ connector: '', evolver: '', transcriber: '' });

  const loadStatus = async () => {
    try { setAgents(await getAgentStatus()); } catch (_) {}
  };

  useEffect(() => { loadStatus(); }, [setAgents]);

  const formatTime = (ts) => ts ? new Date(ts).toLocaleTimeString() : '—';

  return (
    <div className="view">
      <div className="view-header">
        <h2>🤖 Agentes</h2>
        <p className="view-desc">Agentes autónomos que evolucionan tu cerebro</p>
      </div>
      <div className="agents-layout">
        <AgentCard
          type="connector"
          icon="🔗"
          name="El Conector"
          desc="Encuentra conexiones entre notas y crea clusters"
          status={agents.connector || 'idle'}
          lastRun={formatTime(agents.last_connector_run)}
          result={results.connector}
          onRun={async () => {
            setResults(prev => ({ ...prev, connector: '' }));
            try {
              const data = await runConnector();
              setResults(prev => ({
                ...prev,
                connector: `✅ ${data.connections_found || 0} conexiones | ${data.notes_analyzed || 0} notas analizadas`,
              }));
              await loadStatus();
              if (onDone) onDone();
            } catch {
              setResults(prev => ({ ...prev, connector: '❌ Error' }));
            }
          }}
        />

        <AgentCard
          type="evolver"
          icon="🧬"
          name="El Evolucionador"
          desc="Analiza tags y genera insights"
          status={agents.evolver || 'idle'}
          lastRun={formatTime(agents.last_evolver_run)}
          result={results.evolver}
          onRun={async () => {
            setResults(prev => ({ ...prev, evolver: '' }));
            try {
              const data = await runEvolver();
              setResults(prev => ({
                ...prev,
                evolver: `✅ ${data.tags_found || 0} tags | ${data.popular_tags || 0} tags populares`,
              }));
              await loadStatus();
            } catch {
              setResults(prev => ({ ...prev, evolver: '❌ Error' }));
            }
          }}
        />

        <AgentCard
          type="transcriber"
          icon="🎤"
          name="El Transcriptor"
          desc="Transcribe audios con Whisper (formato estudio)"
          status={agents.transcriber || 'idle'}
          lastRun={formatTime(agents.last_transcriber_run)}
          result={results.transcriber}
          onRun={async () => {
            setResults(prev => ({ ...prev, transcriber: '' }));
            try {
              const data = await transcribeAll();
              setResults(prev => ({
                ...prev,
                transcriber: data.transcribed?.length
                  ? `✅ ${data.transcribed.length} audio(s) transcrito(s)`
                  : '📭 No hay audios pendientes',
              }));
              if (onDone) onDone();
            } catch (e) {
              setResults(prev => ({ ...prev, transcriber: `❌ Error: ${e.message || ''}` }));
            }
          }}
        />

        <EvolutionCard />
      </div>
    </div>
  );
}

function EvolutionCard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setStats(await getEvolutionStats()); } catch { setStats(null); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="agent-card evolver">
      <div className="agent-header">
        <span className="agent-icon">🌱</span>
        <div className="agent-info">
          <h3>Aprendizaje Autónomo</h3>
          <p>El Baul aprende solo de cada conversación</p>
        </div>
        <span className={`agent-status-badge ${stats ? 'idle' : 'idle'}`}>{stats ? 'Activo' : '...'}</span>
      </div>
      <div className="agent-body">
        <div className="agent-metrics">
          <div className="metric">
            <span className="metric-value">{stats?.conversation_count ?? '?'}</span>
            <span className="metric-label">Conversaciones</span>
          </div>
          <div className="metric">
            <span className="metric-value">{stats?.draft_notes_count ?? '?'}</span>
            <span className="metric-label">Draft Notes</span>
          </div>
          <div className="metric">
            <span className="metric-value">{stats?.connections_count ?? '?'}</span>
            <span className="metric-label">Conexiones</span>
          </div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
          {loading ? '⏳' : '🔄 Refrescar'}
        </button>
        {stats?.last_consolidation && (
          <div className="agent-result show" style={{ marginTop: 8, color: 'var(--text-secondary)' }}>
            Última consolidación: {new Date(stats.last_consolidation).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}
