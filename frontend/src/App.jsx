import React, { useState, useEffect, useCallback } from 'react';
import Chat from './components/Chat';
import Notes from './components/Notes';
import Graph from './components/Graph';
import Inbox from './components/Inbox';
import Agents from './components/Agents';
import Repos from './components/Repos';
import Knowledge from './components/Knowledge';
import Personality from './components/Personality';
import BottomNav from './components/BottomNav';
import DesktopSidebar from './components/DesktopSidebar';
import NeuralBg from './components/NeuralBg';
import { getBrainStats, getAgentStatus, listNotes, checkRepoUpdates, listKnowledge } from './api';

export default function App() {
  const [activeView, setActiveView] = useState('chat');
  const [stats, setStats] = useState({ total_notes: 0, total_connections: 0, total_vectors: 0 });
  const [agents, setAgents] = useState({ connector: 'idle', evolver: 'idle' });
  const [notes, setNotes] = useState([]);
  const [repoUpdates, setRepoUpdates] = useState(0);
  const [knowledgeTotal, setKnowledgeTotal] = useState(0);

  const loadKnowledgeStats = useCallback(async () => {
    try {
      const data = await listKnowledge();
      setKnowledgeTotal(data.total || 0);
    } catch {}
  }, []);

  const loadStats = useCallback(async () => {
    try { setStats(await getBrainStats()); } catch (_) {}
  }, []);

  const loadAgents = useCallback(async () => {
    try { setAgents(await getAgentStatus()); } catch (_) {}
  }, []);

  const loadNotesList = useCallback(async () => {
    try { setNotes(await listNotes()); } catch (_) {}
  }, []);

  const checkUpdates = useCallback(async () => {
    try {
      const data = await checkRepoUpdates();
      const pending = data.updates?.filter(u => u.pending_update).length || 0;
      setRepoUpdates(pending);
    } catch {}
  }, []);

  useEffect(() => {
    loadStats(); loadAgents(); loadNotesList(); loadKnowledgeStats();
    const si = setInterval(loadStats, 10000);
    const ai = setInterval(loadAgents, 15000);
    const ri = setInterval(checkUpdates, 30000);
    return () => { clearInterval(si); clearInterval(ai); clearInterval(ri); };
  }, [loadStats, loadAgents, loadNotesList, checkUpdates, loadKnowledgeStats]);

  const switchView = (name) => {
    if (name === activeView) return;
    setActiveView(name);
    if (name === 'graph') setTimeout(() => window.dispatchEvent(new Event('graph-show')), 150);
  };

  const renderView = () => {
    switch (activeView) {
      case 'chat': return <Chat key="chat" />;
      case 'notes': return <Notes key="notes" notes={notes} setNotes={setNotes} />;
      case 'graph': return <Graph key="graph" />;
      case 'inbox': return <Inbox key="inbox" onProcessed={() => { loadStats(); loadNotesList(); }} />;
      case 'agents': return <Agents key="agents" agents={agents} setAgents={setAgents} onDone={() => { loadStats(); loadNotesList(); }} />;
      case 'knowledge': return <Knowledge key="knowledge" />;
      case 'repos': return <Repos key="repos" onDone={() => { loadStats(); loadNotesList(); checkUpdates(); }} />;
      case 'personality': return <Personality key="personality" />;
      default: return null;
    }
  };

  return (
    <>
      <NeuralBg />
      <DesktopSidebar
        activeView={activeView}
        stats={stats}
        agents={agents}
        repoUpdates={repoUpdates}
        knowledgeTotal={knowledgeTotal}
        onNavigate={switchView}
      />
      <div className={`main-content${activeView === 'graph' ? ' graph-active' : ''}`}>
        {renderView()}
      </div>
      <BottomNav
        activeView={activeView}
        stats={stats}
        agents={agents}
        repoUpdates={repoUpdates}
        knowledgeTotal={knowledgeTotal}
        onNavigate={switchView}
      />
    </>
  );
}
