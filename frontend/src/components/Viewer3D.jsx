import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { apiUrl } from '../api'
import './Viewer3D.css'

const VIEW_MODES = {
  default: {
    background: 0x0a0a0f,
    meshColor: 0x6c63ff,
    wireColor: 0x8880ff,
    curveColor: 0x4ecdc4,
    pointColor: 0xff6b6b,
    roughness: 0.5,
    metalness: 0.1,
    ambient: { color: 0xffffff, intensity: 0.4 },
    main: { color: 0xffffff, intensity: 0.8, position: [20, 30, 20] },
    fill: { color: 0x6c63ff, intensity: 0.3, position: [-10, 10, -10] },
    gridColors: [0x2a2a3a, 0x1a1a25],
    wireOpacity: 0.15,
    showEdges: false,
  },
  arctic: {
    background: 0xf5f5f5,
    meshColor: 0xffffff,
    wireColor: 0xcccccc,
    curveColor: 0x666666,
    pointColor: 0x999999,
    roughness: 0.95,
    metalness: 0.0,
    ambient: { color: 0xffffff, intensity: 0.7 },
    main: { color: 0xffffff, intensity: 0.5, position: [20, 30, 20] },
    fill: { color: 0xe8e8f0, intensity: 0.4, position: [-10, 10, -10] },
    gridColors: [0xdddddd, 0xeeeeee],
    wireOpacity: 0.0,
    showEdges: true,
  },
}

// Friendly display names for Rhino layer names
const LAYER_LABELS = {
  Site_Boundary: 'Site Boundary',
  Floor_Plates: 'Floor Plates',
  Walls: 'Walls',
  Facade_Pattern: 'Facade Pattern',
  Structural_Columns: 'Columns',
  Structural_Beams: 'Beams',
  Room_Walls: 'Room Walls',
  Room_Floors: 'Room Floors',
  Corridors: 'Corridors',
}

export default function Viewer3D({ fileId, variationName, layerVisibility, onLayerChange }) {
  const containerRef = useRef(null)
  const sceneRef = useRef(null)
  const rendererRef = useRef(null)
  const lightsRef = useRef({})
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState('default')
  const [layerPanelOpen, setLayerPanelOpen] = useState(false)

  // Use lifted state from parent (persists across variation switches)
  const layers = layerVisibility || {}
  const setLayers = onLayerChange || (() => {})

  useEffect(() => {
    if (!containerRef.current) return

    // Setup scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0a0f)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(
      50,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    )
    camera.position.set(15, 12, 15)
    camera.lookAt(5, 0, 5)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    rendererRef.current = renderer
    containerRef.current.appendChild(renderer.domElement)

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.target.set(5, 2, 5)
    controls.update()

    // Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambient)

    const directional = new THREE.DirectionalLight(0xffffff, 0.8)
    directional.position.set(20, 30, 20)
    scene.add(directional)

    const fill = new THREE.DirectionalLight(0x6c63ff, 0.3)
    fill.position.set(-10, 10, -10)
    scene.add(fill)

    // Ground grid
    const grid = new THREE.GridHelper(30, 30, 0x2a2a3a, 0x1a1a25)
    grid.userData.isGrid = true
    scene.add(grid)

    // Axes helper
    const axes = new THREE.AxesHelper(3)
    scene.add(axes)

    lightsRef.current = { ambient, directional, fill, grid, axes }

    // Animation loop
    let animId
    const animate = () => {
      animId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize handler
    const handleResize = () => {
      if (!containerRef.current) return
      const w = containerRef.current.clientWidth
      const h = containerRef.current.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', handleResize)
      renderer.dispose()
      if (containerRef.current?.contains(renderer.domElement)) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [])

  // Update scene when view mode changes
  useEffect(() => {
    if (!sceneRef.current) return
    const scene = sceneRef.current
    const mode = VIEW_MODES[viewMode]
    const lights = lightsRef.current

    scene.background = new THREE.Color(mode.background)

    if (lights.ambient) {
      lights.ambient.color.set(mode.ambient.color)
      lights.ambient.intensity = mode.ambient.intensity
    }
    if (lights.directional) {
      lights.directional.color.set(mode.main.color)
      lights.directional.intensity = mode.main.intensity
    }
    if (lights.fill) {
      lights.fill.color.set(mode.fill.color)
      lights.fill.intensity = mode.fill.intensity
    }
    if (lights.grid) {
      scene.remove(lights.grid)
      const newGrid = new THREE.GridHelper(30, 30, mode.gridColors[0], mode.gridColors[1])
      newGrid.userData.isGrid = true
      scene.add(newGrid)
      lights.grid = newGrid
    }

    // Update all model materials
    scene.traverse((child) => {
      if (!child.userData.isModel) return
      if (child.isMesh && child.material) {
        if (child.material.wireframe) {
          child.material.color.set(mode.wireColor)
          child.material.opacity = mode.wireOpacity
          child.visible = mode.wireOpacity > 0
        } else if (child.material.isMeshStandardMaterial) {
          child.material.color.set(mode.meshColor)
          child.material.roughness = mode.roughness
          child.material.metalness = mode.metalness
        }
      }
      if (child.isLine && child.material) {
        child.material.color.set(mode.curveColor)
      }
    })

    // Handle edge outlines for arctic mode
    const existingEdges = []
    scene.traverse((child) => {
      if (child.userData.isEdgeOutline) existingEdges.push(child)
    })
    existingEdges.forEach((e) => scene.remove(e))

    if (mode.showEdges) {
      scene.traverse((child) => {
        if (child.userData.isModel && child.isMesh && !child.material.wireframe && child.geometry) {
          const edges = new THREE.EdgesGeometry(child.geometry, 30)
          const line = new THREE.LineSegments(
            edges,
            new THREE.LineBasicMaterial({ color: 0xbbbbbb, linewidth: 1 })
          )
          line.userData.isEdgeOutline = true
          line.userData.isModel = true
          line.userData.layerName = child.userData.layerName
          line.visible = child.visible
          line.position.copy(child.position)
          line.rotation.copy(child.rotation)
          line.scale.copy(child.scale)
          scene.add(line)
        }
      })
    }
  }, [viewMode])

  // Apply layer visibility when toggles change
  useEffect(() => {
    if (!sceneRef.current) return
    const scene = sceneRef.current
    scene.traverse((child) => {
      if (!child.userData.layerName) return
      const layerName = child.userData.layerName
      if (layerName in layers) {
        child.visible = layers[layerName]
      }
    })
  }, [layers])

  const toggleLayer = (layerName) => {
    setLayers((prev) => ({ ...prev, [layerName]: !prev[layerName] }))
  }

  const setAllLayers = (visible) => {
    setLayers((prev) => {
      const updated = {}
      for (const key of Object.keys(prev)) updated[key] = visible
      return updated
    })
  }

  // Load 3dm file when fileId changes
  useEffect(() => {
    if (!fileId || !sceneRef.current) return

    const scene = sceneRef.current

    // Remove previous model objects and edge outlines (keep lights, grid, axes)
    const toRemove = []
    scene.traverse((child) => {
      if (child.userData.isModel || child.userData.isEdgeOutline) toRemove.push(child)
    })
    toRemove.forEach((obj) => scene.remove(obj))

    setLoading(true)

    fetch(apiUrl(`/api/download/${fileId}`))
      .then((res) => res.arrayBuffer())
      .then(async (buffer) => {
        const discovered = await loadRhino3dm(buffer, scene, viewMode)
        // Merge with existing layer visibility — keep user's toggle choices
        setLayers((prev) => {
          const merged = {}
          for (const name of Object.keys(discovered)) {
            // Keep previous visibility if the layer existed before, otherwise default to visible
            merged[name] = name in prev ? prev[name] : true
          }
          return merged
        })
        setLoading(false)
      })
      .catch((err) => {
        console.error('Failed to load 3dm:', err)
        setLoading(false)
      })
  }, [fileId])

  return (
    <div className="viewer-container">
      <div className="viewer-toolbar">
        <span className="viewer-title">{variationName || '3D Preview'}</span>
        <div className="viewer-controls">
          <button
            className={`view-mode-btn ${viewMode === 'default' ? 'active' : ''}`}
            onClick={() => setViewMode('default')}
            title="Default view"
          >
            Default
          </button>
          <button
            className={`view-mode-btn ${viewMode === 'arctic' ? 'active' : ''}`}
            onClick={() => setViewMode('arctic')}
            title="Arctic view — white matte rendering"
          >
            Arctic
          </button>
          <span className="viewer-hint">Click + drag to orbit, scroll to zoom</span>
        </div>
      </div>
      <div className="viewer-canvas" ref={containerRef}>
        {loading && (
          <div className="viewer-loading">
            <div className="spinner" />
            <p>Loading model...</p>
          </div>
        )}
        {Object.keys(layers).length > 0 && (
          <div className={`layer-panel ${layerPanelOpen ? 'open' : ''}`}>
            <button
              className="layer-panel-toggle"
              onClick={() => setLayerPanelOpen(!layerPanelOpen)}
              title="Toggle layer visibility"
            >
              {layerPanelOpen ? '\u00D7' : 'Layers'}
            </button>
            {layerPanelOpen && (
              <div className="layer-panel-body">
                <div className="layer-panel-header">
                  <span>Layers</span>
                  <div className="layer-panel-actions">
                    <button onClick={() => setAllLayers(true)} title="Show all">All</button>
                    <button onClick={() => setAllLayers(false)} title="Hide all">None</button>
                  </div>
                </div>
                {Object.keys(layers).map((name) => (
                  <label key={name} className="layer-toggle">
                    <input
                      type="checkbox"
                      checked={layers[name]}
                      onChange={() => toggleLayer(name)}
                    />
                    <span>{LAYER_LABELS[name] || name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

async function loadRhino3dm(buffer, scene, modeName = 'default') {
  const mode = VIEW_MODES[modeName] || VIEW_MODES.default
  const discoveredLayers = {}
  try {
    const rhino3dm = await import('https://cdn.jsdelivr.net/npm/rhino3dm@8.4.0/rhino3dm.module.min.js')
    const Module = await rhino3dm.default()
    const file = Module.File3dm.fromByteArray(new Uint8Array(buffer))

    if (!file) return discoveredLayers

    // Build layer index → name map
    const layerMap = {}
    const fileLayers = file.layers()
    for (let i = 0; i < fileLayers.count; i++) {
      const layer = fileLayers.get(i)
      layerMap[i] = layer.name || `Layer ${i}`
    }

    const objects = file.objects()
    for (let i = 0; i < objects.count; i++) {
      const obj = objects.get(i)
      const geo = obj.geometry()
      if (!geo) continue

      // Get layer name from object attributes
      const attrs = obj.attributes()
      const layerIdx = attrs ? attrs.layerIndex : 0
      const layerName = layerMap[layerIdx] || 'Default'
      discoveredLayers[layerName] = true

      const typeName = geo.constructor.name

      if (typeName === 'Mesh' || geo.objectType === 32) {
        addMeshToScene(geo, scene, mode, layerName)
      } else if (typeName === 'PolylineCurve' || typeName === 'NurbsCurve' ||
                 typeName === 'ArcCurve' || geo.objectType === 4) {
        addCurveToScene(geo, scene, mode, layerName)
      } else if (typeName === 'Point' || geo.objectType === 1) {
        addPointToScene(geo, scene, mode, layerName)
      }
    }

    file.delete()
  } catch (err) {
    console.warn('rhino3dm.js loading failed, using wireframe fallback:', err)
    addFallbackGeometry(scene)
  }
  return discoveredLayers
}

function addMeshToScene(rhinoMesh, scene, mode, layerName) {
  try {
    const vertices = rhinoMesh.vertices()
    const faces = rhinoMesh.faces()

    const geometry = new THREE.BufferGeometry()
    const positions = []
    const indices = []

    for (let i = 0; i < vertices.count; i++) {
      const v = vertices.get(i)
      positions.push(v[0], v[2], v[1]) // Rhino Y-up to Three.js Y-up (swap Y/Z)
    }

    for (let i = 0; i < faces.count; i++) {
      const face = faces.get(i)
      if (face.length === 3) {
        indices.push(face[0], face[1], face[2])
      } else if (face.length === 4) {
        indices.push(face[0], face[1], face[2])
        indices.push(face[0], face[2], face[3])
      }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geometry.setIndex(indices)
    geometry.computeVertexNormals()

    const material = new THREE.MeshStandardMaterial({
      color: mode.meshColor,
      roughness: mode.roughness,
      metalness: mode.metalness,
      side: THREE.DoubleSide,
    })

    const mesh = new THREE.Mesh(geometry, material)
    mesh.userData.isModel = true
    mesh.userData.layerName = layerName
    scene.add(mesh)

    // Wireframe overlay
    if (mode.wireOpacity > 0) {
      const wireMat = new THREE.MeshBasicMaterial({
        color: mode.wireColor,
        wireframe: true,
        transparent: true,
        opacity: mode.wireOpacity,
      })
      const wireframe = new THREE.Mesh(geometry.clone(), wireMat)
      wireframe.userData.isModel = true
      wireframe.userData.layerName = layerName
      scene.add(wireframe)
    }

    // Edge outlines for arctic mode
    if (mode.showEdges) {
      const edges = new THREE.EdgesGeometry(geometry, 30)
      const edgeMat = new THREE.LineBasicMaterial({ color: 0xbbbbbb, linewidth: 1 })
      const edgeLines = new THREE.LineSegments(edges, edgeMat)
      edgeLines.userData.isModel = true
      edgeLines.userData.isEdgeOutline = true
      edgeLines.userData.layerName = layerName
      scene.add(edgeLines)
    }
  } catch (e) {
    console.warn('Failed to add mesh:', e)
  }
}

function addCurveToScene(rhinoCurve, scene, mode, layerName) {
  try {
    const points = []
    // Sample curve at intervals
    const domain = rhinoCurve.domain
    const steps = 200
    for (let i = 0; i <= steps; i++) {
      const t = domain[0] + (domain[1] - domain[0]) * (i / steps)
      const pt = rhinoCurve.pointAt(t)
      if (pt) points.push(new THREE.Vector3(pt[0], pt[2], pt[1]))
    }

    if (points.length < 2) return

    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    const material = new THREE.LineBasicMaterial({
      color: mode.curveColor,
      linewidth: 1,
    })

    const line = new THREE.Line(geometry, material)
    line.userData.isModel = true
    line.userData.layerName = layerName
    scene.add(line)
  } catch (e) {
    console.warn('Failed to add curve:', e)
  }
}

function addPointToScene(rhinoPoint, scene, mode, layerName) {
  try {
    const loc = rhinoPoint.location
    const geometry = new THREE.SphereGeometry(0.08, 8, 8)
    const material = new THREE.MeshBasicMaterial({ color: mode.pointColor })
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(loc[0], loc[2], loc[1])
    mesh.userData.isModel = true
    mesh.userData.layerName = layerName
    scene.add(mesh)
  } catch (e) {
    console.warn('Failed to add point:', e)
  }
}

function addFallbackGeometry(scene) {
  // Simple wireframe box as placeholder
  const geometry = new THREE.BoxGeometry(8, 4, 8)
  const edges = new THREE.EdgesGeometry(geometry)
  const material = new THREE.LineBasicMaterial({ color: 0x6c63ff })
  const wireframe = new THREE.LineSegments(edges, material)
  wireframe.position.set(5, 2, 5)
  wireframe.userData.isModel = true
  scene.add(wireframe)

  // Label
  const label = new THREE.Mesh(
    new THREE.PlaneGeometry(4, 1),
    new THREE.MeshBasicMaterial({ color: 0x1a1a25, transparent: true, opacity: 0.8 })
  )
  label.position.set(5, 5, 5)
  label.userData.isModel = true
  scene.add(label)
}
