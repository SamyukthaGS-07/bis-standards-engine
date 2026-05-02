import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Zap, GitBranch, Shield } from 'lucide-react'

const EXAMPLE_QUERIES = [
  'High strength OPC cement for RCC structural columns',
  'TMT steel bars for residential building foundation',
  'Ready-mix concrete admixture for waterproof basement slab',
  'Fly ash bricks for load-bearing partition walls',
  'Coarse aggregate for M25 grade concrete mix design',
]

const CATEGORY_PILLS = [
  { label: 'Cement', color: '#e8ff47' },
  { label: 'Steel', color: '#60a5fa' },
  { label: 'Concrete', color: '#fb923c' },
  { label: 'Aggregates', color: '#4ade80' },
  { label: 'Bricks', color: '#f472b6' },
  { label: 'Waterproofing', color: '#a78bfa' },
]

export default function SearchScreen({ onSearch, error }) {
  const [query, setQuery] = useState('')
  const textareaRef = useRef(null)

  const submit = () => {
    const q = query.trim()
    if (q.length < 5) return
    onSearch(q)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const fillExample = (example) => {
    setQuery(example)
    textareaRef.current?.focus()
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateRows: 'auto 1fr auto',
      padding: '0',
    }}>

      {/* ── Header bar ── */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '1.25rem 2rem',
        borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 10,
        background: 'rgba(10,10,10,0.9)',
        backdropFilter: 'blur(12px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '32px', height: '32px',
            background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ fontSize: '14px', fontWeight: 800, color: '#000', fontFamily: 'var(--font-display)' }}>BIS</span>
          </div>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1rem', color: 'var(--text)' }}>
            Standards Engine
          </span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-3)', letterSpacing: '0.1em' }}>
          GRAPH-AUGMENTED RAG · BIS SP 21
        </div>
      </header>

      {/* ── Main ── */}
      <main style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', padding: '4rem 2rem', gap: '3rem',
      }}>

        {/* Hero text */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{ textAlign: 'center', maxWidth: '700px' }}
        >
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--accent)',
            letterSpacing: '0.2em', marginBottom: '1.25rem', textTransform: 'uppercase'
          }}>
            MSE Compliance · Instant · Accurate
          </div>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(2.5rem, 6vw, 4.5rem)',
            fontWeight: 800,
            lineHeight: 1.05,
            letterSpacing: '-0.02em',
            marginBottom: '1.25rem',
          }}>
            Describe your{' '}
            <span style={{
              color: 'var(--accent)',
              position: 'relative',
              display: 'inline-block',
            }}>
              product.
            </span>
            <br />
            Get your standards.
          </h1>
          <p style={{
            color: 'var(--text-2)', fontSize: '1rem', maxWidth: '500px', margin: '0 auto',
            fontWeight: 400, lineHeight: 1.7,
          }}>
            Graph-augmented AI searches the entire BIS SP 21 compendium in seconds.
            No compliance consultants. No weeks of research.
          </p>
        </motion.div>

        {/* Search box */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          style={{ width: '100%', maxWidth: '680px' }}
        >
          <div style={{
            border: '1px solid var(--border-bright)',
            background: 'var(--bg-1)',
            position: 'relative',
            transition: 'border-color 0.2s',
          }}
            onFocus={() => {}}
          >
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Describe your building material or product..."
              rows={3}
              style={{
                width: '100%', padding: '1.25rem 1.5rem',
                background: 'transparent', border: 'none', outline: 'none',
                color: 'var(--text)', fontSize: '1rem', resize: 'none',
                lineHeight: 1.6, fontFamily: 'var(--font-body)',
              }}
            />
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '0.75rem 1.25rem',
              borderTop: '1px solid var(--border)',
            }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.65rem',
                color: 'var(--text-3)',
              }}>
                {query.length > 0 ? `${query.length} chars · Enter to search` : 'Shift+Enter for new line'}
              </span>
              <button
                onClick={submit}
                disabled={query.trim().length < 5}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.6rem 1.25rem',
                  background: query.trim().length >= 5 ? 'var(--accent)' : 'var(--bg-3)',
                  color: query.trim().length >= 5 ? '#000' : 'var(--text-3)',
                  fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.85rem',
                  transition: 'all 0.2s',
                  cursor: query.trim().length >= 5 ? 'pointer' : 'not-allowed',
                }}
              >
                Find Standards
                <ArrowRight size={14} />
              </button>
            </div>
          </div>

          {error && (
            <div style={{
              marginTop: '0.75rem', padding: '0.75rem 1rem',
              background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)',
              color: '#f87171', fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
            }}>
              {error}
            </div>
          )}
        </motion.div>

        {/* Category pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center', maxWidth: '600px' }}
        >
          {CATEGORY_PILLS.map((cat) => (
            <span
              key={cat.label}
              style={{
                padding: '0.3rem 0.8rem',
                border: `1px solid ${cat.color}33`,
                color: cat.color,
                fontFamily: 'var(--font-mono)', fontSize: '0.7rem', letterSpacing: '0.05em',
                background: `${cat.color}0d`,
              }}
            >
              {cat.label.toUpperCase()}
            </span>
          ))}
        </motion.div>

        {/* Example queries */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          style={{ width: '100%', maxWidth: '680px' }}
        >
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-3)',
            letterSpacing: '0.1em', marginBottom: '0.75rem',
          }}>
            EXAMPLE QUERIES
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {EXAMPLE_QUERIES.map((ex, i) => (
              <button
                key={i}
                onClick={() => fillExample(ex)}
                style={{
                  textAlign: 'left', padding: '0.6rem 0.9rem',
                  background: 'transparent', border: '1px solid var(--border)',
                  color: 'var(--text-2)', fontSize: '0.85rem',
                  transition: 'all 0.15s',
                  fontFamily: 'var(--font-body)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent)'
                  e.currentTarget.style.color = 'var(--text)'
                  e.currentTarget.style.background = 'var(--accent-dim)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border)'
                  e.currentTarget.style.color = 'var(--text-2)'
                  e.currentTarget.style.background = 'transparent'
                }}
              >
                {ex}
              </button>
            ))}
          </div>
        </motion.div>
      </main>

      {/* ── Feature bar ── */}
      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '1.25rem 2rem',
        display: 'flex', gap: '2rem', flexWrap: 'wrap', justifyContent: 'center',
      }}>
        {[
          { icon: Zap, label: 'Hybrid Retrieval', desc: 'Semantic + BM25 fusion' },
          { icon: GitBranch, label: 'Graph-Augmented', desc: 'Standards knowledge graph' },
          { icon: Shield, label: 'Zero Hallucination', desc: 'Only real BIS standards' },
        ].map(({ icon: Icon, label, desc }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Icon size={14} color="var(--accent)" />
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '0.8rem', color: 'var(--text)' }}>
              {label}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: 'var(--text-3)' }}>
              {desc}
            </span>
          </div>
        ))}
      </footer>
    </div>
  )
}
