import React, { useEffect, useRef, useState } from 'react'
import { drawTrace, drawImageBackground, CATEGORY_LABELS, CATEGORY_DESCRIPTIONS, HIER_COLORS } from '../utils/traceDrawer'
import './ImageTrace.css'

const ALL_CATEGORIES = ['cellular', 'branching', 'lattice', 'porous', 'spiral', 'shell']
const CANVAS_SIZE = 360

export default function ImageTrace({
  imagePreview,
  traceData,
  onSelect,
  onBack,
  onModeChange,
}) {
  const [selected, setSelected] = useState('cellular')
  const canvasRefs = useRef({})
  const imgRef = useRef(null)

  const traces = traceData?.traces || {}
  const [imgW, imgH] = traceData?.image_dimensions || [1, 1]
  const detectedMode = traceData?.detected_mode || 'pattern'
  const activeMode = traceData?.active_mode || detectedMode

  // Load the source image once
  useEffect(() => {
    if (!imagePreview) return
    const img = new Image()
    img.onload = () => {
      imgRef.current = img
      drawAllCanvases()
    }
    img.src = imagePreview
  }, [imagePreview, traceData])

  function drawAllCanvases() {
    for (const cat of ALL_CATEGORIES) {
      const canvas = canvasRefs.current[cat]
      if (!canvas) continue
      const ctx = canvas.getContext('2d')
      ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

      // Dark background
      ctx.fillStyle = '#0a0a0f'
      ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

      // Faded source image
      if (imgRef.current) {
        drawImageBackground(ctx, imgRef.current, CANVAS_SIZE, 0.15)
      }

      // Draw trace
      const extraction = traces[cat]
      if (extraction && Object.keys(extraction).length > 0) {
        drawTrace(ctx, cat, extraction, CANVAS_SIZE, imgW, imgH)
      } else {
        // No data — show message
        ctx.fillStyle = '#444'
        ctx.font = '13px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText('No features detected', CANVAS_SIZE / 2, CANVAS_SIZE / 2)
      }
    }
  }

  const handleConfirm = () => {
    onSelect({
      category: selected,
      extraction_data: traces[selected] || {},
      image_dimensions: [imgW, imgH],
    })
  }

  return (
    <div className="image-trace">
      <div className="image-trace-header">
        <h2>Image Trace</h2>
        <p className="image-trace-sub">
          Select the trace approach that best captures the pattern you want to use.
        </p>
        <div className="mode-toggle">
          <button
            className={`mode-btn ${activeMode === 'object' ? 'active' : ''}`}
            onClick={() => onModeChange && onModeChange('object')}
          >
            Object
          </button>
          <button
            className={`mode-btn ${activeMode === 'pattern' ? 'active' : ''}`}
            onClick={() => onModeChange && onModeChange('pattern')}
          >
            Pattern
          </button>
        </div>
      </div>

      <div className="trace-grid">
        {ALL_CATEGORIES.map((cat) => (
          <div
            key={cat}
            className={`trace-card ${selected === cat ? 'selected' : ''}`}
            onClick={() => setSelected(cat)}
          >
            <canvas
              ref={(el) => { canvasRefs.current[cat] = el }}
              width={CANVAS_SIZE}
              height={CANVAS_SIZE}
              className="trace-canvas"
            />
            <div className="trace-card-info">
              <span className="trace-card-name">{CATEGORY_LABELS[cat] || cat}</span>
              <span className="trace-card-desc">{CATEGORY_DESCRIPTIONS[cat] || ''}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="trace-legend">
        <span><span className="legend-dot" style={{ background: HIER_COLORS[0] }} /> Primary</span>
        <span><span className="legend-dot" style={{ background: HIER_COLORS[1] }} /> Secondary</span>
        <span><span className="legend-dot" style={{ background: HIER_COLORS[2] }} /> Tertiary</span>
      </div>

      <div className="image-trace-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={handleConfirm}>
          Use {CATEGORY_LABELS[selected] || selected} Trace &rarr;
        </button>
      </div>
    </div>
  )
}
