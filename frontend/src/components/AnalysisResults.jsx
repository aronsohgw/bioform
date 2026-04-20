import React from 'react'
import './AnalysisResults.css'

const CATEGORY_COLORS = {
  cellular: '#ff6b6b',
  branching: '#4ecdc4',
  shell: '#45b7d1',
  lattice: '#96ceb4',
  spiral: '#ffd93d',
  porous: '#c9b1ff',
}

export default function AnalysisResults({ analysis }) {
  if (!analysis) return null

  const { category, confidence, rationale, architectural_suggestions } = analysis
  const color = CATEGORY_COLORS[category] || '#6c63ff'
  const pct = Math.round(confidence * 100)

  return (
    <div className="analysis">
      <div className="analysis-category">
        <span className="category-badge" style={{ borderColor: color, color }}>
          {category}
        </span>
        <span className="confidence">{pct}% confidence</span>
      </div>

      {rationale && (
        <p className="analysis-rationale">{rationale}</p>
      )}

      {architectural_suggestions?.length > 0 && (
        <div className="analysis-suggestions">
          <p className="suggestions-label">Architectural applications:</p>
          <ul>
            {architectural_suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
