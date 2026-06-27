import React, { useEffect, useState, useCallback } from 'react';
import { getPersonality, resetPersonality } from '../api';
import '../styles/personality.css';

function Section({ title, children }) {
  return (
    <div className="pers-section">
      <h3 className="pers-section-title">{title}</h3>
      {children}
    </div>
  );
}

function Badge({ children }) {
  return <span className="pers-badge">{children}</span>;
}

function EmptyState({ label }) {
  return <span className="pers-empty">{label}</span>;
}

export default function Personality() {
  const [personality, setPersonality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPersonality();
      setPersonality(data);
    } catch {
      setPersonality(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleReset = async () => {
    if (!confirmReset) {
      setConfirmReset(true);
      return;
    }
    setResetting(true);
    try {
      const data = await resetPersonality();
      setPersonality(data.personality);
      setMessage('✅ Personalidad restaurada a valores de fábrica');
      setTimeout(() => setMessage(''), 3000);
    } catch {
      setMessage('❌ Error al resetear personalidad');
    }
    setConfirmReset(false);
    setResetting(false);
  };

  if (loading) {
    return (
      <div className="view">
        <div className="view-header">
          <h2>🎭 Personalidad</h2>
          <p className="view-desc">Cargando estado de EAgis...</p>
        </div>
        <div className="pers-loading">Cargando...</div>
      </div>
    );
  }

  if (!personality) {
    return (
      <div className="view">
        <div className="view-header">
          <h2>🎭 Personalidad</h2>
          <p className="view-desc">No se pudo cargar el estado de personalidad</p>
        </div>
      </div>
    );
  }

  const {
    interactions_count = 0,
    first_seen = '',
    last_interaction = '',
    preferred_language = 'es',
    favorite_topics = [],
    user_traits = [],
    catchphrases = [],
    catchphrase_usage = {},
    memory_log = [],
    quiz_history = [],
  } = personality;

  const formatDate = (iso) => {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  const langLabel = preferred_language === 'es' ? 'Español' : 'English';

  const usedCatchphrases = catchphrases
    .map(cp => ({ phrase: cp, count: catchphrase_usage[cp] || 0 }))
    .filter(x => x.count > 0)
    .sort((a, b) => b.count - a.count);

  const unusedCatchphrases = catchphrases
    .filter(cp => !(catchphrase_usage[cp] > 0));

  return (
    <div className="view">
      <div className="view-header">
        <h2>🎭 Personalidad de EAgis</h2>
        <p className="view-desc">
          Estado evolutivo del mayordomo — {interactions_count} interacciones
          {first_seen ? ` desde ${formatDate(first_seen)}` : ''}
        </p>
      </div>

      {message && <div className="pers-message">{message}</div>}

      <div className="pers-grid">
        {/* Overview */}
        <Section title="📊 Resumen">
          <div className="pers-metrics">
            <div className="pers-metric">
              <span className="pers-metric-val">{interactions_count}</span>
              <span className="pers-metric-lbl">Interacciones</span>
            </div>
            <div className="pers-metric">
              <span className="pers-metric-val">{langLabel}</span>
              <span className="pers-metric-lbl">Idioma preferido</span>
            </div>
            <div className="pers-metric">
              <span className="pers-metric-val">{favorite_topics.length}</span>
              <span className="pers-metric-lbl">Temas seguidos</span>
            </div>
            <div className="pers-metric">
              <span className="pers-metric-val">{user_traits.length}</span>
              <span className="pers-metric-lbl">Rasgos detectados</span>
            </div>
          </div>
          <div className="pers-timestamps">
            <span><strong>Primer encuentro:</strong> {formatDate(first_seen)}</span>
            <span><strong>Última interacción:</strong> {formatDate(last_interaction)}</span>
          </div>
        </Section>

        {/* Topics */}
        <Section title="📚 Temas favoritos">
          {favorite_topics.length > 0 ? (
            <div className="pers-tags">
              {favorite_topics.map((topic, i) => (
                <Badge key={i}>{topic}</Badge>
              ))}
            </div>
          ) : (
            <EmptyState label="Todavía no hay temas registrados" />
          )}
        </Section>

        {/* Traits */}
        <Section title="🧬 Rasgos del usuario">
          {user_traits.length > 0 ? (
            <ul className="pers-list">
              {user_traits.map((trait, i) => (
                <li key={i}>{trait}</li>
              ))}
            </ul>
          ) : (
            <EmptyState label="Aún no se han detectado rasgos" />
          )}
        </Section>

        {/* Catchphrases */}
        <Section title="💬 Frases características">
          {usedCatchphrases.length > 0 ? (
            <div className="pers-catchphrases">
              {usedCatchphrases.map((item, i) => (
                <div key={i} className="pers-catch-item">
                  <span className="pers-catch-phrase">"{item.phrase}"</span>
                  <span className="pers-catch-count">×{item.count}</span>
                </div>
              ))}
              {unusedCatchphrases.length > 0 && (
                <details className="pers-details">
                  <summary>Disponibles ({unusedCatchphrases.length} sin usar)</summary>
                  <div className="pers-catch-unused">
                    {unusedCatchphrases.map((cp, i) => (
                      <span key={i} className="pers-catch-dim">"{cp}"</span>
                    ))}
                  </div>
                </details>
              )}
            </div>
          ) : (
            <EmptyState label="Ninguna frase usada todavía. ¡Empezá a chatear!" />
          )}
        </Section>

        {/* Memory Log */}
        {memory_log.length > 0 && (
          <Section title="📝 Registro de memoria">
            <ul className="pers-list pers-list-sm">
              {memory_log.map((entry, i) => (
                <li key={i}>{entry}</li>
              ))}
            </ul>
          </Section>
        )}

        {/* Quiz History */}
        {quiz_history.length > 0 && (
          <Section title="🧠 Historial de cuestionarios">
            <ul className="pers-list pers-list-sm">
              {quiz_history.map((q, i) => (
                <li key={i}>
                  {typeof q === 'string' ? q : JSON.stringify(q)}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Reset */}
        <Section title="⚙️ Administración">
          <p className="pers-warning">
            Resetear la personalidad borra todo el historial de interacciones, temas,
            rasgos y frases. EAgis volverá a su estado de fábrica.
          </p>
          <div className="pers-actions">
            <button
              className={`btn ${confirmReset ? 'btn-danger' : 'btn-secondary'}`}
              onClick={handleReset}
              disabled={resetting}
            >
              {resetting ? '⏳ Reseteando...' : confirmReset ? '⚠️ Confirmar reseteo' : '🗑️ Resetear personalidad'}
            </button>
            {confirmReset && (
              <button
                className="btn btn-ghost"
                onClick={() => setConfirmReset(false)}
              >
                Cancelar
              </button>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}
