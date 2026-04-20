import React, { useState } from 'react'
import { apiUrl } from '../api'
import './VariationPopup.css'

export default function VariationPopup({
  variation,
  variationIndex,
  sessionId,
  onClose,
  onRegenerated,
}) {
  const editableParams = variation.editable_params || {}
  const paramKeys = Object.keys(editableParams)

  // Initialize slider values from previously applied params, or defaults
  const [values, setValues] = useState(() => {
    const applied = variation.applied_params || {}
    const initial = {}
    for (const key of paramKeys) {
      initial[key] = key in applied ? applied[key] : editableParams[key].default
    }
    return initial
  })
  const [regenerating, setRegenerating] = useState(false)
  const [error, setError] = useState(null)

  const handleChange = (key, raw) => {
    const meta = editableParams[key]
    const val = meta.step >= 1 ? parseInt(raw, 10) : parseFloat(raw)
    setValues((prev) => ({ ...prev, [key]: val }))
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    setError(null)

    try {
      const res = await fetch(apiUrl('/api/regenerate-variation'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          variation_index: variationIndex,
          custom_params: values,
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Regeneration failed')
      }

      const data = await res.json()
      onRegenerated(variationIndex, data)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setRegenerating(false)
    }
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) onClose()
  }

  const formatValue = (key, val) => {
    const meta = editableParams[key]
    if (meta.step >= 1) return Math.round(val)
    return val.toFixed(2)
  }

  if (paramKeys.length === 0) return null

  return (
    <div className="popup-backdrop" onClick={handleBackdropClick}>
      <div className="popup-panel">
        <div className="popup-header">
          <span className="popup-title">Edit: {variation.name}</span>
          <button className="popup-close" onClick={onClose}>&times;</button>
        </div>

        <div className="popup-params">
          {paramKeys.map((key) => {
            const meta = editableParams[key]
            return (
              <div key={key} className="popup-param">
                <div className="popup-param-header">
                  <span className="popup-param-label">{meta.label}</span>
                  <span className="popup-param-value">{formatValue(key, values[key])}</span>
                </div>
                <input
                  type="range"
                  min={meta.min}
                  max={meta.max}
                  step={meta.step}
                  value={values[key]}
                  onChange={(e) => handleChange(key, e.target.value)}
                />
              </div>
            )
          })}
        </div>

        {error && <div className="search-error" style={{ marginBottom: 12 }}>{error}</div>}

        <div className="popup-actions">
          <button className="popup-cancel" onClick={onClose}>Cancel</button>
          <button
            className="popup-regenerate"
            onClick={handleRegenerate}
            disabled={regenerating}
          >
            {regenerating && <div className="spinner" />}
            {regenerating ? 'Regenerating...' : 'Regenerate'}
          </button>
        </div>
      </div>
    </div>
  )
}
