import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import SearchScreen from './pages/SearchScreen.jsx'
import ResultsScreen from './pages/ResultsScreen.jsx'
import './App.css'

export default function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [error, setError] = useState(null)

  const handleSearch = async (q) => {
    setQuery(q)
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const res = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, top_k: 5, include_rationale: true }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setResults(null)
    setQuery('')
    setError(null)
  }

  return (
    <div className="app">
      <AnimatePresence mode="wait">
        {!results && !loading ? (
          <motion.div
            key="search"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <SearchScreen onSearch={handleSearch} error={error} />
          </motion.div>
        ) : loading ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="loading-screen"
          >
            <LoadingView query={query} />
          </motion.div>
        ) : (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <ResultsScreen results={results} query={query} onReset={handleReset} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function LoadingView({ query }) {
  const steps = [
    'Classifying product category...',
    'Running semantic search...',
    'BM25 keyword retrieval...',
    'Expanding via knowledge graph...',
    'Generating rationale...',
  ]
  const [step, setStep] = useState(0)

  useState(() => {
    const interval = setInterval(() => {
      setStep(s => Math.min(s + 1, steps.length - 1))
    }, 600)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '100vh', gap: '2rem', padding: '2rem'
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-2)', fontSize: '0.75rem', letterSpacing: '0.1em' }}>
        ANALYSING
      </div>
      <div style={{
        fontFamily: 'var(--font-display)', fontSize: 'clamp(1rem, 3vw, 1.5rem)',
        color: 'var(--text)', textAlign: 'center', maxWidth: '600px', fontWeight: 600
      }}>
        "{query}"
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '320px' }}>
        {steps.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: i <= step ? 1 : 0.2, x: 0 }}
            transition={{ delay: i * 0.1 }}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.75rem',
              fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
              color: i === step ? 'var(--accent)' : i < step ? 'var(--text-2)' : 'var(--text-3)'
            }}
          >
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: i === step ? 'var(--accent)' : i < step ? 'var(--green)' : 'var(--text-3)',
              flexShrink: 0
            }} />
            {s}
          </motion.div>
        ))}
      </div>
    </div>
  )
}
