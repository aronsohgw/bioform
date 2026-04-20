/**
 * Shared drawing functions for rendering CV extraction data on a canvas.
 * Used by both ImageTrace (multi-option grid) and PatternPreview (single).
 */

export const HIER_COLORS = [
  '#6c63ff',  // hierarchy 0 — primary (bright purple)
  '#4ecdc4',  // hierarchy 1 — secondary (teal)
  '#ff6b6b',  // hierarchy 2 — tertiary (coral)
]
const DEFAULT_COLOR = '#6c63ff'

export const CATEGORY_LABELS = {
  cellular: 'Cellular',
  branching: 'Branching',
  lattice: 'Lattice / Grid',
  porous: 'Porous',
  spiral: 'Spiral',
  shell: 'Shell / Surface',
}

export const CATEGORY_DESCRIPTIONS = {
  cellular: 'Cell shapes, voronoi boundaries',
  branching: 'Vein networks, tree-like paths',
  lattice: 'Grid lines, woven structures',
  porous: 'Holes, perforations, gaps',
  spiral: 'Curved arms, radial patterns',
  shell: 'Surface curvature, height map',
}

/**
 * Draw a smooth curve through an array of [x, y] screen-space points.
 * Uses quadratic bezier curves with midpoints as anchors — produces
 * organic, flowing lines instead of angular polygon segments.
 * @param {CanvasRenderingContext2D} ctx
 * @param {Array} pts - [[x,y], [x,y], ...] in screen coordinates
 * @param {boolean} closed - whether to close the path
 */
function drawSmoothCurve(ctx, pts, closed = false) {
  if (pts.length < 2) return
  if (pts.length === 2) {
    ctx.moveTo(pts[0][0], pts[0][1])
    ctx.lineTo(pts[1][0], pts[1][1])
    return
  }

  if (closed) {
    // For closed shapes: start at midpoint between last and first
    const mx = (pts[pts.length - 1][0] + pts[0][0]) / 2
    const my = (pts[pts.length - 1][1] + pts[0][1]) / 2
    ctx.moveTo(mx, my)
    for (let i = 0; i < pts.length; i++) {
      const next = pts[(i + 1) % pts.length]
      const midX = (pts[i][0] + next[0]) / 2
      const midY = (pts[i][1] + next[1]) / 2
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], midX, midY)
    }
  } else {
    // Open path: start at first point, end at last
    ctx.moveTo(pts[0][0], pts[0][1])
    for (let i = 0; i < pts.length - 1; i++) {
      const midX = (pts[i][0] + pts[i + 1][0]) / 2
      const midY = (pts[i][1] + pts[i + 1][1]) / 2
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], midX, midY)
    }
    // Draw to the final point
    const last = pts[pts.length - 1]
    ctx.lineTo(last[0], last[1])
  }
}

/**
 * Draw extraction data for a given category onto a canvas context.
 * @param {CanvasRenderingContext2D} ctx
 * @param {string} category
 * @param {object} extraction - serialized extraction data
 * @param {number} size - canvas size (square)
 * @param {number} imgW - source image width
 * @param {number} imgH - source image height
 */
export function drawTrace(ctx, category, extraction, size, imgW, imgH) {
  const maxDim = Math.max(imgW, imgH)
  const s = size / maxDim
  const ox = (size - imgW * s) / 2
  const oy = (size - imgH * s) / 2

  ctx.lineWidth = 1.5
  ctx.lineCap = 'round'

  switch (category) {
    case 'cellular': drawCellular(ctx, extraction, s, ox, oy); break
    case 'branching': drawPaths(ctx, extraction, s, ox, oy); break
    case 'lattice': drawLattice(ctx, extraction, s, ox, oy); break
    case 'porous': drawPorous(ctx, extraction, s, ox, oy); break
    case 'spiral': drawSpiral(ctx, extraction, s, ox, oy); break
    case 'shell': drawShell(ctx, extraction, s, ox, oy); break
  }
}

/**
 * Draw faded source image as background on canvas.
 */
export function drawImageBackground(ctx, img, size, opacity = 0.2) {
  ctx.globalAlpha = opacity
  const scale = Math.min(size / img.width, size / img.height)
  const w = img.width * scale
  const h = img.height * scale
  const ox = (size - w) / 2
  const oy = (size - h) / 2
  ctx.drawImage(img, ox, oy, w, h)
  ctx.globalAlpha = 1.0
}

function drawCellular(ctx, ext, s, ox, oy) {
  const boundaries = ext.cell_boundaries || []
  for (const cell of boundaries) {
    const pts = cell.points || []
    const hier = cell.hierarchy ?? 0
    const color = HIER_COLORS[hier] || DEFAULT_COLOR
    if (pts.length < 3) continue
    // Quality-based opacity
    ctx.globalAlpha = 0.4 + 0.6 * (cell.quality ?? 1.0)
    ctx.strokeStyle = color
    // Line width by hierarchy: primary thick, tertiary thin
    ctx.lineWidth = hier === 0 ? 2 : hier === 1 ? 1.2 : 0.6
    ctx.beginPath()
    const screenPts = pts.map(p => [ox + p[0] * s, oy + p[1] * s])
    drawSmoothCurve(ctx, screenPts, true)
    ctx.stroke()
  }
  ctx.globalAlpha = 1.0
  ctx.lineWidth = 1.5

  const seeds = ext.seed_points_hierarchical || []
  if (seeds.length > 0) {
    for (const sp of seeds) {
      const cx = sp.center ? sp.center[0] : sp[0]
      const cy = sp.center ? sp.center[1] : sp[1]
      const color = HIER_COLORS[sp.hierarchy ?? 0] || DEFAULT_COLOR
      ctx.globalAlpha = 0.4 + 0.6 * (sp.quality ?? 1.0)
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.arc(ox + cx * s, oy + cy * s, 2.5, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalAlpha = 1.0
  } else {
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
    ctx.lineWidth = hier === 0 ? 2.5 : hier === 1 ? 1.5 : 0.8
    ctx.strokeStyle = color
    ctx.globalAlpha = 0.4 + 0.6 * (path.quality ?? 1.0)

    if (pts.length < 2) continue
    // Subsample then draw smooth curve
    const step = Math.max(1, Math.floor(pts.length / 500))
    const sampled = []
    for (let i = 0; i < pts.length; i += step) {
      sampled.push([ox + pts[i][1] * s, oy + pts[i][0] * s])
    }
    const last = pts[pts.length - 1]
    const lastScreen = [ox + last[1] * s, oy + last[0] * s]
    if (sampled.length === 0 || sampled[sampled.length - 1][0] !== lastScreen[0] ||
        sampled[sampled.length - 1][1] !== lastScreen[1]) {
      sampled.push(lastScreen)
    }
    ctx.beginPath()
    drawSmoothCurve(ctx, sampled, false)
    ctx.stroke()
  }
  ctx.globalAlpha = 1.0
  ctx.lineWidth = 1.5
}

function drawLattice(ctx, ext, s, ox, oy) {
  const hierLines = ext.lines_hierarchical || []
  if (hierLines.length > 0) {
    for (const hl of hierLines) {
      const [x1, y1, x2, y2] = hl.coords
      const hier = hl.hierarchy ?? 0
      const color = HIER_COLORS[hier] || DEFAULT_COLOR
      ctx.globalAlpha = 0.4 + 0.6 * (hl.quality ?? 1.0)
      ctx.lineWidth = hier === 0 ? 2 : hier === 1 ? 1.2 : 0.6
      ctx.strokeStyle = color
      ctx.beginPath()
      ctx.moveTo(ox + x1 * s, oy + y1 * s)
      ctx.lineTo(ox + x2 * s, oy + y2 * s)
      ctx.stroke()
    }
  } else {
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
  ctx.globalAlpha = 1.0
  ctx.lineWidth = 1.5
}

function drawPorous(ctx, ext, s, ox, oy) {
  const holes = ext.holes || []
  for (const hole of holes) {
    const [cx, cy] = hole.center
    const r = hole.radius || 3
    const hier = hole.hierarchy ?? 0
    const color = HIER_COLORS[hier] || DEFAULT_COLOR
    ctx.globalAlpha = 0.4 + 0.6 * (hole.quality ?? 1.0)

    if (hole.boundary && hole.boundary.length >= 3) {
      ctx.strokeStyle = color
      ctx.lineWidth = hier === 0 ? 2 : hier === 1 ? 1.2 : 0.6
      ctx.beginPath()
      const bPts = hole.boundary.map(p => [ox + p[0] * s, oy + p[1] * s])
      drawSmoothCurve(ctx, bPts, true)
      ctx.stroke()
    } else {
      ctx.strokeStyle = color
      ctx.lineWidth = hier === 0 ? 2 : hier === 1 ? 1.2 : 0.6
      ctx.beginPath()
      ctx.arc(ox + cx * s, oy + cy * s, r * s, 0, Math.PI * 2)
      ctx.stroke()
    }

    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(ox + cx * s, oy + cy * s, 1.5, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1.0
  ctx.lineWidth = 1.5
}

function drawSpiral(ctx, ext, s, ox, oy) {
  const paths = ext.paths || []
  if (paths.length > 0) {
    drawPaths(ctx, ext, s, ox, oy)
    return
  }

  const profile = ext.radial_profile || []
  const center = ext.center || [0, 0]
  if (profile.length === 0) return

  ctx.strokeStyle = DEFAULT_COLOR
  const spiralPts = profile.map(([angleDeg, r]) => {
    const angle = (angleDeg * Math.PI) / 180
    return [ox + (center[0] + r * Math.cos(angle)) * s,
            oy + (center[1] + r * Math.sin(angle)) * s]
  })
  ctx.beginPath()
  drawSmoothCurve(ctx, spiralPts, false)
  ctx.stroke()

  ctx.fillStyle = HIER_COLORS[0]
  ctx.beginPath()
  ctx.arc(ox + center[0] * s, oy + center[1] * s, 4, 0, Math.PI * 2)
  ctx.fill()
}

function drawShell(ctx, ext, s, ox, oy) {
  const grid = ext.control_points || []
  if (grid.length === 0) return

  for (const row of grid) {
    for (const pt of row) {
      // New format: (x, y, height, curvature, hierarchy) — fallback for old (x, y, z)
      const x = pt[0]
      const y = pt[1]
      const z = pt[2]  // height
      const curvature = pt[3] ?? 0  // curvature magnitude (new)
      const hier = pt[4] ?? 0  // hierarchy level (new)

      // Color by hierarchy
      const color = HIER_COLORS[hier] || DEFAULT_COLOR
      ctx.fillStyle = color
      // Radius based on curvature (high curvature = larger dots)
      const radius = 1 + Math.min(curvature * 8, 4) + z * 2
      ctx.globalAlpha = 0.5 + Math.min(curvature * 2, 0.5)
      ctx.beginPath()
      ctx.arc(ox + x * s, oy + y * s, radius, 0, Math.PI * 2)
      ctx.fill()
    }
  }
  ctx.globalAlpha = 1.0
}
