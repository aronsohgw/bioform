import React, { useCallback, useRef, useState } from 'react'
import ImageSearch from './ImageSearch'
import { apiUrl } from '../api'
import './ImageUpload.css'

export default function ImageUpload({ onUpload }) {
  const [dragActive, setDragActive] = useState(false)
  const [mode, setMode] = useState('upload') // 'upload' | 'search'
  const inputRef = useRef(null)

  const handleFile = useCallback((file) => {
    if (file && file.type.startsWith('image/')) {
      onUpload(file)
    }
  }, [onUpload])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }, [handleFile])

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragActive(true)
  }

  const handleDragLeave = () => setDragActive(false)
  const handleClick = () => inputRef.current?.click()

  const handleChange = (e) => {
    const file = e.target.files[0]
    handleFile(file)
  }

  const handleImageSelected = useCallback(async (imageUrl) => {
    // Fetch the image through our proxy to avoid CORS, then create a File
    const resp = await fetch(apiUrl(`/api/proxy-image?url=${encodeURIComponent(imageUrl)}`))
    if (!resp.ok) {
      let detail = 'Failed to fetch image'
      try {
        const err = await resp.json()
        detail = err.detail || detail
      } catch { /* ignore parse errors */ }
      throw new Error(detail)
    }
    const blob = await resp.blob()
    if (blob.size < 100) throw new Error('Image too small or empty')
    const contentType = blob.type || 'image/jpeg'
    const ext = contentType.includes('png') ? '.png' : contentType.includes('webp') ? '.webp' : '.jpg'
    const file = new File([blob], `unsplash-image${ext}`, { type: contentType })
    onUpload(file)
  }, [onUpload])

  return (
    <div className="upload-container">
      <div className="upload-hero">
        <h2>Upload a nature image</h2>
        <p>BioForm will analyze biomimicry patterns and generate parametric Rhino + Grasshopper files for architectural design.</p>
      </div>

      <div className="upload-tabs">
        <button
          className={`tab ${mode === 'upload' ? 'active' : ''}`}
          onClick={() => setMode('upload')}
        >
          Upload File
        </button>
        <button
          className={`tab ${mode === 'search' ? 'active' : ''}`}
          onClick={() => setMode('search')}
        >
          Search Unsplash
        </button>
      </div>

      {mode === 'upload' && (
        <>
          <div
            className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={handleClick}
          >
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="upload-text">Drop image here or click to browse</p>
            <p className="upload-hint">PNG, JPG, WebP</p>
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleChange}
              hidden
            />
          </div>

          <div className="upload-examples">
            <p>Best results with: leaf veins, coral, honeycomb, spider webs, shells, bone cross-sections</p>
          </div>
        </>
      )}

      {mode === 'search' && (
        <ImageSearch onSelect={handleImageSelected} />
      )}
    </div>
  )
}
