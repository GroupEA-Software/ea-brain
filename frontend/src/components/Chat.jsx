import React, { useState, useRef, useEffect } from 'react';
import { chat, createNote, downloadChatPdf } from '../api';
import '../styles/chat.css';

const HISTORY_KEY = 'baul_chat_history';

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; } catch { return []; }
}

function saveHistory(messages) {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-50))); } catch {}
}

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
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  return html;
}

function stripMD(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '$1').replace(/\*(.+?)\*/g, '$1').replace(/\[\[([^\]]+)\]\]/g, '$1').replace(/^[#>\-]\s*/gm, '').replace(/<[^>]+>/g, '');
}

export default function Chat() {
  const [messages, setMessages] = useState(loadHistory);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => { saveHistory(messages); }, [messages]);

  const sendMessage = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    const userMsg = { role: 'user', content: msg, id: Date.now() };
    setMessages(prev => {
      const next = [...prev, userMsg];
      saveHistory(next);
      return next;
    });
    setLoading(true);
    try {
      const hist = messages.map(m => ({ role: m.role, content: m.content }));
      const data = await chat(msg, hist);
      const sysMsg = {
        role: 'system',
        content: data.answer,
        sources: data.sources || [],
        suggestSave: data.suggest_save,
        webSearchUsed: data.web_search_used,
        webKnowledgeGained: data.web_knowledge_gained,
        topic: data.topic || 'respuesta',
        fullContent: data.full_content || null,
        id: Date.now() + 1,
      };
      setMessages(prev => {
        const next = [...prev, sysMsg];
        saveHistory(next);
        return next;
      });
    } catch {
      const errMsg = { role: 'system', content: '⚠️ Error al conectar con el cerebro.', id: Date.now() + 1 };
      setMessages(prev => {
        const next = [...prev, errMsg];
        saveHistory(next);
        return next;
      });
    }
    setLoading(false);
  };

  const clearHistory = () => {
    if (window.confirm('Borrar todo el historial de chat?')) {
      setMessages([]);
      localStorage.removeItem(HISTORY_KEY);
    }
  };

  const makeFilename = (topic, ext) => {
    const clean = topic.replace(/[^a-zA-Z0-9áéíóúñüÁÉÍÓÚÑÜ\s-]/g, '').trim().slice(0, 60).replace(/\s+/g, '-').toLowerCase();
    return `EAgis-${clean || 'documento'}.${ext}`;
  };

  const downloadAsMd = (content, topic) => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = makeFilename(topic, 'md');
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAsPdf = async (content, topic) => {
    try {
      await downloadChatPdf(content, makeFilename(topic, 'pdf'));
    } catch (e) {
      alert('Error al generar PDF: ' + e.message);
    }
  };

  const saveAsNote = async (msgObj) => {
    const plain = stripMD(msgObj.content);
    const title = prompt('Titulo para la nota:', plain.slice(0, 50).trim() + '...');
    if (!title) return;
    setSaving(msgObj.content);
    try {
      await createNote(title, msgObj.content);
      setMessages(prev => prev.map(m => m.id === msgObj.id ? { ...m, saved: true } : m));
    } catch (e) {
      alert('Error al guardar: ' + e.message);
    }
    setSaving(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div className="view">
      <div className="view-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2>💬 Chat</h2>
            <p className="view-desc">EAgis, tu mayordomo digital, al servicio de tu cerebro</p>
          </div>
          <div className="view-actions">
            {messages.length > 0 && (
              <button className="btn btn-secondary btn-sm" onClick={clearHistory}>🗑️ Limpiar</button>
            )}
          </div>
        </div>
      </div>
      <div className="chat-container">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <div className="chat-welcome-icon">🧠</div>
              <p>Preguntale a EAgis lo que quieras. Revisara tus notas primero, y si no encuentra nada, buscara en internet.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={m.id || i} className={`message ${m.role === 'user' ? 'user' : 'system'}`}>
              <div className="message-avatar">{m.role === 'user' ? '👤' : '🧠'}</div>
              <div className="message-bubble">
                <div className="message-content" dangerouslySetInnerHTML={{ __html: renderMD(m.content) }} />
                {m.role === 'system' && (
                  <div className="message-footer">
                    <div className="message-footer-row">
                      {m.webSearchUsed && <span className="badge badge-web">🌐 Web</span>}
                      {m.webKnowledgeGained && <span className="badge badge-learn">🧠 Nuevo</span>}
                      {m.saved && <span className="badge badge-saved">✅ Guardado</span>}
                      <button className="badge badge-dlmd" onClick={() => downloadAsMd(m.fullContent || m.content, m.topic)} title="Descargar como Markdown">
                        ⬇️ .md
                      </button>
                      <button className="badge badge-dlpdf" onClick={() => downloadAsPdf(m.fullContent || m.content, m.topic)} title="Descargar como PDF">
                        ⬇️ .pdf
                      </button>
                      {m.suggestSave && !m.saved && (
                        <button className="badge badge-save" onClick={() => saveAsNote(m)} disabled={saving}>
                          {saving === m.content ? '⏳' : '📝 Guardar como nota'}
                        </button>
                      )}
                    </div>
                    {m.sources?.filter(s => (s.score || 1) >= 0.3).length > 0 && (
                      <div className="message-citations">
                        {m.sources.filter(s => (s.score || 1) >= 0.3).map((s, j) => (
                          <span key={j} className="citation-item">
                            <span className="citation-num">{j + 1}</span>
                            <span className="citation-name">{s.filename}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="message system">
              <div className="message-avatar">🧠</div>
              <div className="message-bubble">
                <div className="message-content">
                  <div className="typing-indicator"><span /><span /><span /></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Pregunta algo a EAgis..."
              rows={1}
            />
            <button className="chat-send" onClick={sendMessage} disabled={loading}>➤</button>
          </div>
        </div>
      </div>
    </div>
  );
}
