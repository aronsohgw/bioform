import React, { useEffect, useRef } from 'react'
import './PatternPreview.css'

// Colors per hierarchy level — brighter = primary, dimmer = tertiary
const HIER_COLORS = [
  '#6c63ff',  // hierarchy 0 — primary (bright purple)
  '#4ecdc4',  // hierarchy 1 — secondary (teal)
  '#ff6b6b',  // hierarchy 2 — tertiary (coral)
]
const DEFAULT_COLOR = '#6c63ff'

export default function PatternPreview({
  imagePreview,
  analysisData,
  onConfirm,
  onBack,
}) {
  const canvasRef = useRef(null)

  const category = analysisData?.category || 'unknown'
  const extraction = analysisData?.extraction_data || {}
  const [imgW, imgH] = analysisData?.image_dimensions || [1, 1]

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const size = canvas.width // square canvas
    ctx.clearRect(0, 0, size, size)

    // Dark background
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, size, size)

    // Load source image faded in the background
    if (imagePreview) {
      const img = new Image()
      img.onload = () => {
        ctx.globalAlpha = 0.2
        // Fit image centered in square
        const scale = Math.min(size / img.width, size / img.height)
        const w = img.width * scale
        const h = img.height * scale
        const ox = (size - w) / 2
        const oy = (size - h) / 2
        ctx.drawImage(img, ox, oy, w, h)
        ctx.globalAlpha = 1.0
        drawFeatures(ctx, size)
      }
      img.src = imagePreview
    } else {
      drawFeatures(ctx, size)
    }
  }, [analysisData, imagePreview])

  function drawFeatures(ctx, size) {
    // Scale factor: map image pixel coords → canvas coords
    const maxDim = Math.max(imgW, imgH)
    const s = size / maxDim
    const ox = (size - imgW * s) / 2
    const oy = (size - imgH * s) / 2

    ctx.lineWidth = 1.5
    ctx.lineCap = 'round'

    if (category === 'cellular') {
      drawCellular(ctx, extraction, s, ox, oy)
    } else if (category === 'branching') {
      drawPaths(ctx, extraction, s, ox, oy)
    } else if (category === 'lattice') {
      drawLattice(ctx, extraction, s, ox, oy)
    } else if (category === 'porous') {
      drawPorous(ctx, extraction, s, ox, oy)
    } else if (category === 'spiral') {
      drawSpiral(ctx, extraction, s, ox, oy)
    } else if (category === 'shell') {
      drawShell(ctx, extraction, s, ox, oy)
    }
  }

  function drawCellular(ctx, ext, s, ox, oy) {
    // Draw cell boundaries
    const boundaries = ext.cell_boundaries || []
    for (const cell of boundaries) {
      const pts = cell.points || []
      const color = HIER_COLORS[cell.hierarchy ?? 0] || DEFAULT_COLOR
      if (pts.length < 3) continue
      ctx.strokeStyle = color
      ctx.beginPath()
      ctx.moveTo(ox + pts[0][0] * s, oy + pts[0][1] * s)
      for (let i = 1; i < pts.length; i++) {
        ctx.lineTo(ox + pts[i][0] * s, oy + pts[i][1] * s)
      }
      ctx.closePath()
      ctx.stroke()
    }

    // Draw seed points
    const seeds = ext.seed_points_hierarchical || []
    if (seeds.length > 0) {
      for (const sp of seeds) {
        const cx = sp.center ? sp.center[0] : sp[0]
        const cy = sp.center ? sp.center[1] : sp[1]
        const color = HIER_COLORS[sp.hierarchy ?? 0] || DEFAULT_COLOR
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(ox + cx * s, oy + cy * s, 2.5, 0, Math.PI * 2)
        ctx.fill()
      }
    } else {
      // Flat seed points fallback
      const flat = ext.seed_points || []
      ctx.fillStyle = DEFAULT_COLOR
      for (const pt of flat) {
        ctx.beginPath()
        ctx.arc(ox + pt[0] * s, oy + pt[1] * s, 2.5, 0, Math.PI * 2)
        ctx.fill()
      }
    }
  }

  function drawPaths(ctx, ext, s, ox, oy) {
    const paths = ext.paths || []
    if (paths.length === 0) {
      // Fallback: draw branch_points as dots
      const bps = ext.branch_points || []
      ctx.fillStyle = DEFAULT_COLOR
      for (const bp of bps) {
        ctx.beginPath()
        ctx.arc(ox + bp[1] * s, oy + bp[0] * s, 2, 0, Math.PI * 2)
        ctx.fill()
      }
      return
    }

    for (const path of paths) {
      const pts = path.points || path
      const hier = path.hierarchy ?? 1
      const color = HIER_COLORS[hier] || DEFAULT_COLOR
      // Thicker lines for primary paths
      ctx.lineWidth = hier === 0 ? 2.5 : hier === 1 ? 1.5 : 0.8
      ctx.strokeStyle = color

      if (pts.length < 2) continue
      ctx.beginPath()
      // paths use (row, col) format — row=y, col=x
      ctx.moveTo(ox + pts[0][1] * s, oy + pts[0][0] * s)
      // Subsample for performance if very long
      const step = Math.max(1, Math.floor(pts.length / 200))
      for (let i = step; i < pts.length; i += step) {
        ctx.lineTo(ox + pts[i][1] * s, oy + pts[i][0] * s)
      }
      // Always include last point
      const last = pts[pts.length - 1]
      ctx.lineTo(ox + last[1] * s, oy + last[0] * s)
      ctx.stroke()
    }
    ctx.lineWidth = 1.5
  }

  function drawLattice(ctx, ext, s, ox, oy) {
    const hierLines = ext.lines_hierarchical || []
    if (hierLines.length > 0) {
      for (const hl of hierLines) {
        const [x1, y1, x2, y2] = hl.coords
        const color = HIER_COLORS[hl.hierarchy ?? 0] || DEFAULT_COLOR
        ctx.lineWidth = hl.hierarchy === 0 ? 2 : hl.hierarchy === 1 ? 1.2 : 0.6
        ctx.strokeStyle = color
        ctx.beginPath()
        ctx.moveTo(ox + x1 * s, oy + y1 * s)
        ctx.lineTo(ox + x2 * s, oy + y2 * s)
        ctx.stroke()
      }
    } else {
      // Flat lines fallback
      const lines = ext.lines || []
      ctx.strokeStyle = DEFAULT_COLOR
      ctx.lineWidth = 1
      for (const line of lines) {
        const coords = Array.isArray(line[0]) ? line[0] : line
        ctx.beginPath()
        ctx.moveTo(ox + coords[0] * s, oy + coords[1] * s)
        ctx.lineTo(ox + coords[2] * s, oy + coords[3] * s)
        ctx.stroke()
      }
    }
    ctx.lineWidth = 1.5
  }

  function drawPorous(ctx, ext, s, ox, oy) {
    const holes = ext.holes || []
    for (const hole of holes) {
      const [cx, cy] = hole.center
      const r = hole.radius || 3
      const hier = hole.hierarchy ?? 0
      const color = HIER_COLORS[hier] || DEFAULT_COLOR

      // Draw boundary contour if available
      if (hole.boundary && hole.boundary.length >= 3) {
        ctx.strokeStyle = color
        ctx.lineWidth = hier === 0 ? 2 : 1
        ctx.beginPath()
        ctx.moveTo(ox + hole.boundary[0][0] * s, oy + hole.boundary[0][1] * s)
        for (let i = 1; i < hole.boundary.length; i++) {
          ctx.lineTo(ox + hole.boundary[i][0] * s, oy + hole.boundary[i][1] * s)
        }
        ctx.closePath()
        ctx.stroke()
      } else {
        // Circle fallback
        ctx.strokeStyle = color
        ctx.lineWidth = hier === 0 ? 2 : 1
        ctx.beginPath()
        ctx.arc(ox + cx * s, oy + cy * s, r * s, 0, Math.PI * 2)
        ctx.stroke()
      }

      // Center dot
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(ox + cx * s, oy + cy * s, 1.5, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.lineWidth = 1.5
  }

  function drawSpiral(ctx, ext, s, ox, oy) {
    // Try traced paths first
    const paths = ext.paths || []
    if (paths.length > 0) {
      drawPaths(ctx, ext, s, ox, oy)
      return
    }

    // Fallback: radial profile
    const profile = ext.radial_profile || []
    const center = ext.center || [0, 0]
    if (profile.length === 0) return

    ctx.strokeStyle = DEFAULT_COLOR
    ctx.beginPath()
    for (let i = 0; i < profile.length; i++) {
      const [angleDeg, r] = profile[i]
      const angle = (angleDeg * Math.PI) / 180
      const px = center[0] + r * Math.cos(angle)
      const py = center[1] + r * Math.sin(angle)
      if (i === 0) ctx.moveTo(ox + px * s, oy + py * s)
      else ctx.lineTo(ox + px * s, oy + py * s)
    }
    ctx.stroke()

    // Center point
    ctx.fillStyle = HIER_COLORS[0]
    ctx.beginPath()
    ctx.arc(ox + center[0] * s, oy + center[1] * s, 4, 0, Math.PI * 2)
    ctx.fill()
  }

  function drawShell(ctx, ext, s, ox, oy) {
    // Draw control point grid as a height-mapped dot grid
    const grid = ext.control_points || []
    if (grid.length === 0) return

    for (const row of grid) {
      for (const pt of row) {
        const [x, y, z] = pt
        // Map z (0-1) to brightness
        const brightness = Math.floor(80 + z * 175)
        ctx.fillStyle = `rgb(${brightness}, ${brightness - 20}, ${brightness + 40})`
        const radius = 1 + z * 3
        ctx.beginPath()
        ctx.arc(ox + x * s, oy + y * s, radius, 0, Math.PI * 2)
        ctx.fill()
      }
    }
  }

  return (
    <div className="pattern-preview">
      <div className="pattern-preview-header">
        <h2>Pattern Preview</h2>
        <p className="pattern-preview-category">
          Detected: <strong>{category}</strong>
          {analysisData?.confidence > 0 && (
            <span className="confidence"> ({Math.round(analysisData.confidence * 100)}% confidence)</span>
          )}
        </p>
        {analysisData?.rationale && (
          <p className="pattern-preview-rationale">{analysisData.rationale}</p>
        )}
      </div>

      <div className="pattern-preview-canvas-container">
        <canvas ref={canvasRef} width={600} height={600} className="pattern-preview-canvas" />
        <div className="pattern-preview-legend">
          <span><span className="legend-dot" style={{ background: HIER_COLORS[0] }} /> Primary</span>
          <span><span className="legend-dot" style={{ background: HIER_COLORS[1] }} /> Secondary</span>
          <span><span className="legend-dot" style={{ background: HIER_COLORS[2] }} /> Tertiary</span>
        </div>
      </div>

      <div className="pattern-preview-actions">
        <button className="btn-secondary" onClick={onBack}>Back</button>
        <button className="btn-primary" onClick={onConfirm}>Looks Good — Generate 3D</button>
      </div>
    </div>
  )
}
