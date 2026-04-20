import React, { useState, useRef } from 'react'
import { apiUrl } from '../api'
import './ImageSearch.css'

const SUGGESTIONS = [
  'honeycomb', 'coral reef', 'leaf veins', 'spider web',
  'tree branches', 'nautilus shell', 'fern spiral', 'sea sponge',
  'dragonfly wing', 'sunflower seeds', 'fish scales', 'bone structure',
]

export default function ImageSearch({ onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selecting, setSelecting] = useState(null) // id of image being selected
  const debounceRef = useRef(null)

  const search = async (q) => {
    if (!q.trim()) {
      setResults([])
      return
    }

    setLoading(true)
    setError(null)

    try {
      const resp = await fetch(apiUrl(`/api/search-images?q=${encodeURIComponent(q)}`))
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        if (resp.status === 429) {
          throw new Error('Unsplash rate limit reached — wait a minute and try again')
        }
        throw new Error(err.detail || `Search failed (${resp.status})`)
      }
      const data = await resp.json()
      setResults(data.results || [])
    } catch (err) {
      setError(err.message)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e) => {
    const value = e.target.value
    setQuery(value)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => search(value), 400)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    clearTimeout(debounceRef.current)
    search(query)
  }

  const handleSuggestion = (term) => {
    setQuery(term)
    search(term)
  }

  const handleSelect = async (image) => {
    setSelecting(image.id)
    try {
      await onSelect(image.regular)
    } catch (err) {
      setError(err.message || 'Failed to load image')
      setSelecting(null)
    }
  }

  return (
    <div className="image-search">
      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-input-wrap">
          <svg className="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="Search nature patterns (e.g. honeycomb, coral, leaf veins)"
            value={query}
            onChange={handleInputChange}
            autoFocus
          />
          {query && (
            <button type="button" className="search-clear" onClick={() => { setQuery(''); setResults([]) }}>
              &times;
            </button>
          )}
        </div>
      </form>

      {!query && (
        <div className="search-suggestions">
          <p className="suggestions-label">Try searching for:</p>
          <div className="suggestion-chips">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="chip" onClick={() => handleSuggestion(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <div className="search-error">{error}</div>}

      {loading && (
        <div className="search-loading">
          <div className="spinner" />
          <p>Searching Unsplash...</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          {results.map((img) => (
            <button
              key={img.id}
              className={`result-card ${selecting === img.id ? 'selecting' : ''}`}
              onClick={() => handleSelect(img)}
              disabled={selecting !== null}
            >
              <img src={img.thumb} alt={img.alt || 'Nature image'} loading="lazy" />
              {selecting === img.id && (
                <div className="result-loading">
                  <div className="spinner" />
                </div>
              )}
              <span className="result-credit">by {img.author}</span>
            </button>
          ))}
        </div>
      )}

      {results.length > 0 && (
        <p className="unsplash-credit">
          Photos from <a href="https://unsplash.com" target="_blank" rel="noopener noreferrer">Unsplash</a>
        </p>
      )}
    </div>
  )
}
