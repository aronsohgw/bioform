import React from 'react'
import { apiUrl } from '../api'
import './VariationCards.css'

export default function VariationCards({ variations, ghx, selected, onSelect, onEdit }) {
  if (!variations) return null

  return (
    <div className="variations">
      <p className="variations-label">Variations</p>

      <div className="variation-list">
        {variations.map((v, i) => (
          <div
            key={v.file_id}
            className={`variation-card ${selected === i ? 'selected' : ''}`}
          >
            <button
              className="variation-select"
              onClick={() => onSelect(i)}
            >
              <span className="variation-letter">{String.fromCharCode(65 + i)}</span>
              <div className="variation-info">
                <span className="variation-name">{v.name}</span>
                <span className="variation-desc">{v.description}</span>
              </div>
            </button>
            {v.editable_params && Object.keys(v.editable_params).length > 0 && (
              <button
                className="variation-edit"
                onClick={(e) => { e.stopPropagation(); onEdit(i) }}
                title="Adjust parameters"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
                </svg>
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="download-section">
        <p className="download-label">Download</p>
        <div className="download-buttons">
          {variations.map((v, i) => (
            <a
              key={v.file_id}
              href={apiUrl(`/api/download/${v.file_id}`)}
              className="download-btn"
              download={v.filename}
            >
              {String.fromCharCode(65 + i)} .3dm
            </a>
          ))}
          {ghx && (
            <a
              href={apiUrl(`/api/download/${ghx.file_id}`)}
              className="download-btn download-ghx"
              download={ghx.filename}
            >
              .ghx
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
