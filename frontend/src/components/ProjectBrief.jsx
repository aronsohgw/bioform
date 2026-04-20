import React, { useState } from 'react'
import './ProjectBrief.css'

const PRESET_POLYGONS = {
  rectangle: { label: 'Rectangle', points: [[0, 0], [20, 0], [20, 30], [0, 30]] },
  square: { label: 'Square', points: [[0, 0], [20, 0], [20, 20], [0, 20]] },
  lShape: { label: 'L-Shape', points: [[0, 0], [20, 0], [20, 15], [10, 15], [10, 30], [0, 30]] },
  triangle: { label: 'Triangle', points: [[0, 0], [30, 0], [15, 25]] },
  pentagon: { label: 'Pentagon', points: [[15, 0], [30, 10], [25, 28], [5, 28], [0, 10]] },
}

const FACADE_OPTIONS = ['north', 'south', 'east', 'west']

export default function ProjectBrief({ imagePreview, onSubmit, onBack }) {
  const [siteShape, setSiteShape] = useState('rectangle')
  const [customWidth, setCustomWidth] = useState(20)
  const [customDepth, setCustomDepth] = useState(30)
  const [buildings, setBuildings] = useState([
    {
      name: 'Building A',
      floor_count: 8,
      floor_height: 3.5,
      dimension_mode: 'static',
      footprint_inset: 0,
      facades: ['all'],
      taper_ratio: 0.9,
      setback_amount: 1.0,
      setback_every: 3,
    },
  ])

  const getPolygon = () => {
    if (siteShape === 'custom') {
      return [[0, 0], [customWidth, 0], [customWidth, customDepth], [0, customDepth]]
    }
    return PRESET_POLYGONS[siteShape]?.points || PRESET_POLYGONS.rectangle.points
  }

  const updateBuilding = (index, field, value) => {
    setBuildings(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  const toggleFacade = (bIndex, facade) => {
    setBuildings(prev => {
      const updated = [...prev]
      const bldg = { ...updated[bIndex] }
      let facades = [...bldg.facades]

      if (facade === 'all') {
        facades = facades.includes('all') ? [] : ['all']
      } else {
        facades = facades.filter(f => f !== 'all')
        if (facades.includes(facade)) {
          facades = facades.filter(f => f !== facade)
        } else {
          facades.push(facade)
        }
        if (facades.length === 4) facades = ['all']
      }

      bldg.facades = facades.length === 0 ? ['all'] : facades
      updated[bIndex] = bldg
      return updated
    })
  }


  const handleSubmit = () => {
    const polygon = getPolygon()
    onSubmit({
      site_polygon: polygon,
      buildings: buildings,
    })
  }

  const polygon = getPolygon()
  const totalHeight = buildings[0]?.floor_count * buildings[0]?.floor_height || 0

  return (
    <div className="brief-container">
      <div className="brief-header">
        <button className="brief-back" onClick={onBack}>&larr; Change Image</button>
        <h2>Project Brief</h2>
        <p>Define your building to map the biomimicry pattern onto real architecture.</p>
      </div>

      <div className="brief-layout">
        <div className="brief-left">
          {/* Source image */}
          <div className="brief-image">
            {imagePreview && <img src={imagePreview} alt="Source" />}
          </div>

          {/* Site polygon preview */}
          <div className="brief-site-preview">
            <svg viewBox="-2 -2 36 36" className="site-svg">
              <polygon
                points={polygon.map(p => `${p[0]},${p[1]}`).join(' ')}
                fill="rgba(108, 99, 255, 0.15)"
                stroke="var(--accent)"
                strokeWidth="0.5"
              />
              {polygon.map((p, i) => (
                <circle key={i} cx={p[0]} cy={p[1]} r="0.8" fill="var(--accent)" />
              ))}
            </svg>
            <div className="site-stats">
              <span>{polygon.length} sides</span>
              <span>{totalHeight.toFixed(1)}m tall</span>
              <span>{buildings[0]?.floor_count} floors</span>
            </div>
          </div>
        </div>

        <div className="brief-right">
          {/* Site shape */}
          <section className="brief-section">
            <h3>Site Shape</h3>
            <div className="shape-options">
              {Object.entries(PRESET_POLYGONS).map(([key, { label }]) => (
                <button
                  key={key}
                  className={`shape-btn ${siteShape === key ? 'active' : ''}`}
                  onClick={() => setSiteShape(key)}
                >
                  {label}
                </button>
              ))}
              <button
                className={`shape-btn ${siteShape === 'custom' ? 'active' : ''}`}
                onClick={() => setSiteShape('custom')}
              >
                Custom
              </button>
            </div>

            {siteShape === 'custom' && (
              <div className="custom-dims">
                <label>
                  Width (m)
                  <input type="number" value={customWidth} min={5} max={200}
                    onChange={e => setCustomWidth(Number(e.target.value))} />
                </label>
                <label>
                  Depth (m)
                  <input type="number" value={customDepth} min={5} max={200}
                    onChange={e => setCustomDepth(Number(e.target.value))} />
                </label>
              </div>
            )}
          </section>

          {/* Buildings */}
          {buildings.map((bldg, bi) => (
            <section key={bi} className="brief-section building-section">
              <div className="building-header">
                <h3>{bldg.name}</h3>
              </div>

              <div className="field-grid">
                <label>
                  Floors
                  <input type="number" value={bldg.floor_count} min={1} max={100}
                    onChange={e => updateBuilding(bi, 'floor_count', Number(e.target.value))} />
                </label>
                <label>
                  Floor Height (m)
                  <input type="number" value={bldg.floor_height} min={2} max={10} step={0.5}
                    onChange={e => updateBuilding(bi, 'floor_height', Number(e.target.value))} />
                </label>
                <label>
                  Footprint Inset (m)
                  <input type="number" value={bldg.footprint_inset} min={0} max={20}
                    onChange={e => updateBuilding(bi, 'footprint_inset', Number(e.target.value))} />
                </label>
              </div>

              {/* Dimension mode */}
              <div className="field-group">
                <label className="field-label">Floor Dimensions</label>
                <div className="mode-options">
                  {['static', 'taper', 'setback'].map(mode => (
                    <button
                      key={mode}
                      className={`mode-btn ${bldg.dimension_mode === mode ? 'active' : ''}`}
                      onClick={() => updateBuilding(bi, 'dimension_mode', mode)}
                    >
                      {mode === 'static' && 'Uniform'}
                      {mode === 'taper' && 'Taper'}
                      {mode === 'setback' && 'Setback'}
                    </button>
                  ))}
                </div>

                {bldg.dimension_mode === 'taper' && (
                  <div className="mode-params">
                    <label>
                      Taper Ratio
                      <input type="range" min={0.5} max={0.99} step={0.01}
                        value={bldg.taper_ratio}
                        onChange={e => updateBuilding(bi, 'taper_ratio', Number(e.target.value))} />
                      <span className="range-value">{bldg.taper_ratio}</span>
                    </label>
                    <p className="param-hint">
                      Top floor: {(polygon[1]?.[0] * Math.pow(bldg.taper_ratio, bldg.floor_count - 1)).toFixed(1)}m wide
                    </p>
                  </div>
                )}

                {bldg.dimension_mode === 'setback' && (
                  <div className="mode-params">
                    <label>
                      Setback (m)
                      <input type="number" value={bldg.setback_amount} min={0.5} max={5} step={0.5}
                        onChange={e => updateBuilding(bi, 'setback_amount', Number(e.target.value))} />
                    </label>
                    <label>
                      Every N floors
                      <input type="number" value={bldg.setback_every} min={1} max={10}
                        onChange={e => updateBuilding(bi, 'setback_every', Number(e.target.value))} />
                    </label>
                  </div>
                )}
              </div>

              {/* Facades */}
              <div className="field-group">
                <label className="field-label">Pattern Facades</label>
                <div className="facade-options">
                  <button
                    className={`facade-btn ${bldg.facades.includes('all') ? 'active' : ''}`}
                    onClick={() => toggleFacade(bi, 'all')}
                  >
                    All
                  </button>
                  {FACADE_OPTIONS.map(f => (
                    <button
                      key={f}
                      className={`facade-btn ${bldg.facades.includes(f) || bldg.facades.includes('all') ? 'active' : ''}`}
                      onClick={() => toggleFacade(bi, f)}
                    >
                      {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </section>
          ))}

          <button className="generate-btn" onClick={handleSubmit}>
            Generate 3D Variations
          </button>
        </div>
      </div>
    </div>
  )
}
