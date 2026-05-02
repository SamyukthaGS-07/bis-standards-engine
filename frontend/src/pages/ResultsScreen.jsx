import { useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, Download, Clock, GitBranch, Search, ChevronDown, ChevronUp, CheckCircle, AlertCircle } from 'lucide-react'

const CONFIDENCE_CONFIG = {
  high:   { color: '#4ade80', label: 'HIGH',   bg: 'rgba(74,222,128,0.1)',  border: 'rgba(74,222,128,0.3)' },
  medium: { color: '#fb923c', label: 'MEDIUM', bg: 'rgba(251,146,60,0.1)',  border: 'rgba(251,146,60,0.3)' },
  low:    { color: '#f87171', label: 'LOW',    bg: 'rgba(248,113,113,0.1)', border: 'rgba(248,113,113,0.3)' },
}

const SOURCE_CONFIG = {
  vector_retrieval: { color: '#60a5fa', label: 'SEMANTIC', icon: Search },
  graph_expansion:  { color: '#a78bfa', label: 'GRAPH',    icon: GitBranch },
}

export default function ResultsScreen({ results, query, onReset }) {
  const { recommendations = [], summary, latency_seconds, query_analysis } = results

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bis-results-${Date.now()}.json`
    a.click()
  }

  const exportReport = () => {
    const lines = [
      'BIS STANDARDS COMPLIANCE REPORT',
      '================================',
      '',
      `Product: ${query}`,
      `Generated: ${new Date().toLocaleString()}`,
      `Latency: ${latency_seconds}s`,
      '',
      summary ? `Summary: ${summary}` : '',
      '',
      'RECOMMENDED STANDARDS',
      '---------------------',
      '',
      ...recommendations.map((r, i) => [
        `${i + 1}. ${r.standard_id} — ${r.title}`,
        `   Category: ${r.material_category}`,
        `   Confidence: ${r.confidence?.toUpperCase()}`,
        `   Rationale: ${r.rationale}`,
        `   Key Requirement: ${r.key_requirement}`,
        '',
      ].join('\n')),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bis-compliance-report-${Date.now()}.txt`
    a.click()
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateRows: 'auto 1fr' }}>

      {/* ── Header ── */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '1.25rem 2rem',
        borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 10,
        background: 'rgba(10,10,10,0.95)', backdropFilter: 'blur(12px)',
        flexWrap: 'wrap', gap: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={onReset}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.4rem',
              color: 'var(--text-2)', fontSize: '0.8rem',
              fontFamily: 'var(--font-mono)', transition: 'color 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--accent)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-2)'}
          >
            <ArrowLeft size={14} />
            NEW SEARCH
          </button>
          <div style={{ width: '1px', height: '20px', background: 'var(--border)' }} />
          <div style={{
            fontFamily: 'var(--font-display)', fontWeight: 600,
            fontSize: '0.9rem', color: 'var(--text)',
            maxWidth: '400px', overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            "{query}"
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Latency badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.4rem',
            padding: '0.3rem 0.75rem',
            border: `1px solid ${latency_seconds < 5 ? 'rgba(74,222,128,0.4)' : 'rgba(248,113,113,0.4)'}`,
            background: latency_seconds < 5 ? 'rgba(74,222,128,0.08)' : 'rgba(248,113,113,0.08)',
          }}>
            <Clock size={11} color={latency_seconds < 5 ? '#4ade80' : '#f87171'} />
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.65rem',
              color: latency_seconds < 5 ? '#4ade80' : '#f87171',
            }}>
              {latency_seconds}s
            </span>
          </div>

          <button
            onClick={exportReport}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.4rem',
              padding: '0.4rem 0.9rem',
              border: '1px solid var(--border-bright)',
              background: 'var(--bg-2)', color: 'var(--text-2)',
              fontFamily: 'var(--font-mono)', fontSize: '0.65rem', letterSpacing: '0.05em',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-bright)'; e.currentTarget.style.color = 'var(--text-2)' }}
          >
            <Download size={11} />
            EXPORT REPORT
          </button>
        </div>
      </header>

      {/* ── Body ── */}
      <main style={{ padding: '2.5rem 2rem', maxWidth: '900px', margin: '0 auto', width: '100%' }}>

        {/* Query analysis banner */}
        {query_analysis?.detected_categories?.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: '0.75rem 1rem', marginBottom: '1.5rem',
              background: 'var(--accent-dim)', border: '1px solid var(--accent-glow)',
              display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap',
            }}
          >
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--accent)', letterSpacing: '0.1em' }}>
              DETECTED
            </span>
            {query_analysis.detected_categories.map(cat => (
              <span key={cat} style={{
                fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '0.8rem',
                color: 'var(--accent)',
              }}>
                {cat}
              </span>
            ))}
            {query_analysis.is_structural && (
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-2)' }}>
                · Structural application
              </span>
            )}
          </motion.div>
        )}

        {/* Summary */}
        {summary && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            style={{
              padding: '1rem 1.25rem', marginBottom: '2rem',
              background: 'var(--bg-1)', border: '1px solid var(--border)',
              borderLeft: '3px solid var(--accent)',
            }}
          >
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-3)', marginBottom: '0.4rem', letterSpacing: '0.1em' }}>
              COMPLIANCE SUMMARY
            </div>
            <p style={{ color: 'var(--text)', fontSize: '0.9rem', lineHeight: 1.6 }}>{summary}</p>
          </motion.div>
        )}

        {/* Results count */}
        <div style={{
          display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
          marginBottom: '1.25rem',
        }}>
          <div>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.5rem', color: 'var(--text)' }}>
              {recommendations.length}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-3)', marginLeft: '0.5rem', letterSpacing: '0.1em' }}>
              STANDARDS FOUND
            </span>
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-3)' }}>
            Ranked by relevance
          </div>
        </div>

        {/* Standard cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {recommendations.map((rec, i) => (
            <StandardCard key={rec.standard_id} rec={rec} rank={i + 1} />
          ))}
        </div>

        {recommendations.length === 0 && (
          <div style={{
            padding: '3rem', textAlign: 'center',
            border: '1px dashed var(--border)',
            color: 'var(--text-3)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
          }}>
            No standards found. Try rephrasing your product description.
          </div>
        )}
      </main>
    </div>
  )
}


function StandardCard({ rec, rank }) {
  const [expanded, setExpanded] = useState(false)

  const conf = CONFIDENCE_CONFIG[rec.confidence] || CONFIDENCE_CONFIG.medium
  const src  = SOURCE_CONFIG[rec.source] || SOURCE_CONFIG.vector_retrieval
  const SrcIcon = src.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: rank * 0.07, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      style={{
        border: '1px solid var(--border)',
        background: 'var(--bg-1)',
        overflow: 'hidden',
        transition: 'border-color 0.2s',
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-bright)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
    >
      {/* Card header */}
      <div style={{ padding: '1.25rem 1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>

          {/* Left: rank + ID + title */}
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', flex: 1 }}>
            <div style={{
              fontFamily: 'var(--font-mono)', fontWeight: 500,
              fontSize: '1.4rem', color: 'var(--border-bright)',
              lineHeight: 1, paddingTop: '2px', minWidth: '28px',
            }}>
              {String(rank).padStart(2, '0')}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.35rem' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontWeight: 500,
                  fontSize: '1rem', color: 'var(--accent)',
                }}>
                  {rec.standard_id}
                </span>

                {/* Category tag */}
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.6rem',
                  padding: '0.2rem 0.5rem',
                  border: '1px solid var(--border-bright)',
                  color: 'var(--text-3)', letterSpacing: '0.05em',
                }}>
                  {rec.material_category?.toUpperCase()}
                </span>
              </div>

              <div style={{
                fontFamily: 'var(--font-display)', fontWeight: 600,
                fontSize: '0.95rem', color: 'var(--text)', lineHeight: 1.3,
              }}>
                {rec.title || '—'}
              </div>
            </div>
          </div>

          {/* Right: confidence + source badges */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
            <div style={{
              padding: '0.25rem 0.6rem',
              background: conf.bg, border: `1px solid ${conf.border}`,
              fontFamily: 'var(--font-mono)', fontSize: '0.6rem',
              color: conf.color, letterSpacing: '0.08em',
            }}>
              {conf.label}
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '0.3rem',
              padding: '0.2rem 0.5rem',
              border: '1px solid var(--border)',
              fontFamily: 'var(--font-mono)', fontSize: '0.6rem',
              color: src.color,
            }}>
              <SrcIcon size={9} />
              {src.label}
            </div>
          </div>
        </div>

        {/* Rationale */}
        {rec.rationale && (
          <div style={{
            marginTop: '1rem', paddingTop: '1rem',
            borderTop: '1px solid var(--border)',
            color: 'var(--text-2)', fontSize: '0.875rem', lineHeight: 1.7,
          }}>
            {rec.rationale}
          </div>
        )}
      </div>

      {/* Expandable details */}
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            width: '100%', padding: '0.6rem 1.5rem',
            background: 'var(--bg-2)', borderTop: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            color: 'var(--text-3)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem',
            letterSpacing: '0.05em', transition: 'color 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--text)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-3)'}
        >
          <span>DETAILS</span>
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            style={{
              padding: '1rem 1.5rem', borderTop: '1px solid var(--border)',
              background: 'var(--bg-2)',
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem',
            }}
          >
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-3)', marginBottom: '0.35rem', letterSpacing: '0.08em' }}>
                KEY REQUIREMENT
              </div>
              <div style={{ color: 'var(--text-2)', fontSize: '0.8rem' }}>
                {rec.key_requirement || '—'}
              </div>
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-3)', marginBottom: '0.35rem', letterSpacing: '0.08em' }}>
                APPLICATIONS
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                {(Array.isArray(rec.applications) ? rec.applications : []).map(app => (
                  <span key={app} style={{
                    padding: '0.15rem 0.4rem', background: 'var(--bg-3)',
                    border: '1px solid var(--border)',
                    fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-3)',
                  }}>
                    {app}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-3)', marginBottom: '0.35rem', letterSpacing: '0.08em' }}>
                RELEVANCE SCORE
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.8rem',
                color: rec.retrieval_score > 0.7 ? '#4ade80' : rec.retrieval_score > 0.4 ? '#fb923c' : 'var(--text-2)',
              }}>
                {(rec.retrieval_score * 100).toFixed(1)}%
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}
