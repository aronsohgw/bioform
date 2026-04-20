import React, { useState, useRef } from 'react'
import ImageUpload from './components/ImageUpload'
import ImageTrace from './components/ImageTrace'
import ProjectBrief from './components/ProjectBrief'
import AnalysisResults from './components/AnalysisResults'
import VariationCards from './components/VariationCards'
import VariationPopup from './components/VariationPopup'
import Viewer3D from './components/Viewer3D'
import { apiUrl } from './api'
import './App.css'

const STEPS = {
  UPLOAD: 'upload',
  TRACING: 'tracing',
  IMAGE_TRACE: 'image_trace',
  BRIEF: 'brief',
  GENERATING: 'generating',
  RESULTS: 'results',
}

export default function App() {
  const [step, setStep] = useState(STEPS.UPLOAD)
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [result, setResult] = useState(null)
  const [selectedVariation, setSelectedVariation] = useState(null)
  const [editingVariation, setEditingVariation] = useState(null)
  const [layerVisibility, setLayerVisibility] = useState({}) // persists across variation switches
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState({ percent: 0, label: '' })
  const [traceData, setTraceData] = useState(null)      // all 6 traces from /api/trace
  const [analysisData, setAnalysisData] = useState(null) // selected trace (single category)
  const [briefData, setBriefData] = useState(null)
  const abortRef = useRef(null)

  const cancelRequest = () => {
    if (abortRef.current) abortRef.current.abort()
    setStep(STEPS.UPLOAD)
    setProgress({ percent: 0, label: '' })
  }

  const handleUpload = async (file) => {
    setError(null)
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
    // Auto-start tracing immediately after upload
    await runTrace(file)
  }

  // Read an SSE stream
  const readSSE = async (response, { onProgress, onDone, onError }) => {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const chunk of lines) {
        const line = chunk.trim()
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.step === 'error') {
            onError(event.label)
            return
          }
          onProgress(event)
          if (event.step === 'done' && event.result) {
            onDone(event.result)
            return
          }
        } catch {
          // skip malformed JSON chunks
        }
      }
    }
  }

  // Step 1: Trace image — run all 6 extractors
  const runTrace = async (file, modeOverride = '') => {
    setStep(STEPS.TRACING)
    setProgress({ percent: 0, label: 'Starting image trace...' })

    const controller = new AbortController()
    abortRef.current = controller

    const formData = new FormData()
    formData.append('file', file)
    if (modeOverride) formData.append('mode', modeOverride)

    try {
      const response = await fetch(apiUrl('/api/trace'), {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })

      if (!response.ok) {
        let detail = 'Trace failed'
        try { detail = (await response.json()).detail || detail } catch {}
        throw new Error(detail)
      }

      await readSSE(response, {
        onProgress: (e) => setProgress({ percent: e.percent, label: e.label }),
        onDone: (result) => {
          setTraceData(result)
          setStep(STEPS.IMAGE_TRACE)
        },
        onError: (msg) => { throw new Error(msg) },
      })
    } catch (err) {
      setError(err.message)
      setStep(STEPS.UPLOAD)
    }
  }

  // Mode toggle: re-run trace with different mode
  const handleModeChange = async (newMode) => {
    if (!imageFile) return
    await runTrace(imageFile, newMode)
  }

  // Step 2: User selected a trace → save it and go to brief
  const handleTraceSelect = (selectedAnalysis) => {
    setAnalysisData(selectedAnalysis)
    setStep(STEPS.BRIEF)
  }

  // Step 3: Brief submitted → generate 3D with cached analysis
  const handleBriefSubmit = async (brief) => {
    setBriefData(brief)
    await runGenerate(brief)
  }

  const handleSkipBrief = async () => {
    setBriefData(null)
    await runGenerate(null)
  }

  // Step 4: Generate 3D from cached trace — fast, no LLM
  const runGenerate = async (brief) => {
    setError(null)
    setStep(STEPS.GENERATING)
    setProgress({ percent: 0, label: 'Starting 3D generation...' })

    const controller = new AbortController()
    abortRef.current = controller

    const formData = new FormData()
    formData.append('file', imageFile)
    if (brief) formData.append('brief_json', JSON.stringify(brief))
    if (traceData?.trace_id && analysisData?.category) {
      formData.append('trace_id', traceData.trace_id)
      formData.append('trace_category', analysisData.category)
    }

    try {
      const response = await fetch(apiUrl('/api/generate'), {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })

      if (!response.ok) {
        let detail = 'Generation failed'
        try { detail = (await response.json()).detail || detail } catch {}
        throw new Error(detail)
      }

      await readSSE(response, {
        onProgress: (e) => setProgress({ percent: e.percent, label: e.label }),
        onDone: (result) => {
          setResult(result)
          setSelectedVariation(0)
          setStep(STEPS.RESULTS)
        },
        onError: (msg) => { throw new Error(msg) },
      })
    } catch (err) {
      setError(err.message)
      setStep(STEPS.BRIEF)
    }
  }

  const handleVariationRegenerated = (index, newData) => {
    setResult((prev) => {
      const updated = { ...prev }
      updated.variations = [...prev.variations]
      updated.variations[index] = {
        ...updated.variations[index],
        file_id: newData.file_id,
        filename: newData.filename,
        applied_params: newData.custom_params || {},
      }
      return updated
    })
    // If the regenerated variation is currently selected, trigger viewer reload
    if (selectedVariation === index) {
      // Force re-render by briefly deselecting
      setSelectedVariation(null)
      setTimeout(() => setSelectedVariation(index), 50)
    }
  }

  const handleReset = () => {
    setStep(STEPS.UPLOAD)
    setImageFile(null)
    setImagePreview(null)
    setResult(null)
    setSelectedVariation(null)
    setEditingVariation(null)
    setError(null)
    setTraceData(null)
    setAnalysisData(null)
    setBriefData(null)
    setLayerVisibility({})
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="logo">BioForm</h1>
        <p className="tagline">Nature to Architecture</p>
        {step === STEPS.BRIEF && (
          <button className="skip-brief-btn" onClick={() => handleSkipBrief()}>
            Skip Brief &rarr;
          </button>
        )}
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        {step === STEPS.UPLOAD && (
          <ImageUpload onUpload={handleUpload} />
        )}

        {step === STEPS.BRIEF && (
          <ProjectBrief
            imagePreview={imagePreview}
            onSubmit={handleBriefSubmit}
            onBack={() => setStep(STEPS.IMAGE_TRACE)}
          />
        )}

        {step === STEPS.TRACING && (
          <div className="analyzing">
            <div className="analyzing-preview">
              {imagePreview && <img src={imagePreview} alt="Uploaded" />}
            </div>
            <div className="analyzing-status">
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${progress.percent}%` }} />
              </div>
              <p className="progress-percent">{progress.percent}%</p>
              <p className="progress-label">{progress.label}</p>
              <button className="cancel-btn" onClick={cancelRequest}>Cancel</button>
            </div>
          </div>
        )}

        {step === STEPS.IMAGE_TRACE && traceData && (
          <ImageTrace
            imagePreview={imagePreview}
            traceData={traceData}
            onSelect={handleTraceSelect}
            onBack={() => { setStep(STEPS.UPLOAD); setTraceData(null) }}
            onModeChange={handleModeChange}
          />
        )}

        {step === STEPS.GENERATING && (
          <div className="analyzing">
            <div className="analyzing-preview">
              {imagePreview && <img src={imagePreview} alt="Uploaded" />}
            </div>
            <div className="analyzing-status">
              <div className="progress-bar-container">
                <div className="progress-bar-fill" style={{ width: `${progress.percent}%` }} />
              </div>
              <p className="progress-percent">{progress.percent}%</p>
              <p className="progress-label">{progress.label}</p>
              <button className="cancel-btn" onClick={cancelRequest}>Cancel</button>
            </div>
          </div>
        )}

        {step === STEPS.RESULTS && result && (
          <div className="results-layout">
            <div className="results-sidebar">
              <button className="reset-btn" onClick={handleReset}>
                New Image
              </button>

              <div className="source-image">
                {imagePreview && <img src={imagePreview} alt="Source" />}
              </div>

              <AnalysisResults analysis={result.analysis} />

              <VariationCards
                variations={result.variations}
                ghx={result.ghx}
                selected={selectedVariation}
                onSelect={setSelectedVariation}
                onEdit={setEditingVariation}
              />
            </div>

            <div className="results-viewer">
              <Viewer3D
                fileId={result.variations[selectedVariation]?.file_id}
                variationName={result.variations[selectedVariation]?.name}
                layerVisibility={layerVisibility}
                onLayerChange={setLayerVisibility}
              />
            </div>

            {editingVariation !== null && result.variations[editingVariation] && (
              <VariationPopup
                variation={result.variations[editingVariation]}
                variationIndex={editingVariation}
                sessionId={result.session_id}
                onClose={() => setEditingVariation(null)}
                onRegenerated={handleVariationRegenerated}
              />
            )}
          </div>
        )}
      </main>
    </div>
  )
}
