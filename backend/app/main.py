import asyncio
import json as json_mod
import logging
import tempfile
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

import cv2

logger = logging.getLogger("bioform")
import numpy as np
import httpx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from starlette.responses import StreamingResponse

from fastapi import Form
from pydantic import BaseModel

from app.cv_extraction import preprocess, extract_all, detect_mode
from app.ollama_service import classify_image
from app.variation_engine import (
    generate_variations, generate_single_variation, apply_scale,
    VARIATION_CONFIGS, DEFAULT_BRIEF,
)
from app.ghx_builder import build_ghx_for_category
from app.brief import validate_brief, brief_to_gen_params

app = FastAPI(title="BioForm API", version="0.1.0")

_default_origins = "http://localhost:5173,http://localhost:3000"
_allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=os.environ.get("ALLOWED_ORIGIN_REGEX") or None,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

# In-memory store for generated files (session-based)
_generated_files: dict[str, dict] = {}
# Session store for regeneration (keeps analysis/brief/extraction per session)
_sessions: dict[str, dict] = {}
# Trace store — keeps full extraction data server-side so frontend only sends a trace_id
_traces: dict[str, dict] = {}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    contents = await file.read()

    img_array = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    h, w = img.shape[:2]

    suffix = os.path.splitext(file.filename or "img.png")[1] or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        classification = await classify_image(tmp_path)
        category = classification.get("category", "cellular")
        if category not in ("cellular", "branching", "shell", "lattice", "spiral", "porous"):
            category = "cellular"

        _, _, denoised = preprocess(tmp_path)
        extraction_data = extract_all(denoised, category)

        return {
            "category": category,
            "confidence": classification.get("confidence", 0.0),
            "rationale": classification.get("rationale", ""),
            "architectural_suggestions": classification.get("architectural_suggestions", []),
            "extraction_data": _serialize_extraction(extraction_data),
            "image_dimensions": [w, h],
        }
    finally:
        os.unlink(tmp_path)


ALL_CATEGORIES = ["cellular", "branching", "lattice", "porous", "spiral", "shell"]


@app.post("/api/trace")
async def trace_image(file: UploadFile = File(...), mode: str = Form(default="")):
    """Image Trace: run ALL 6 CV extractors with essence extraction.

    Auto-detects object vs pattern mode, or accepts explicit mode override.
    Returns all 6 trace results so the user can pick their preferred approach.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    img_array = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    h, w = img.shape[:2]

    suffix = os.path.splitext(file.filename or "img.png")[1] or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    async def event_stream():
        try:
            yield _sse({"step": "preprocessing", "percent": 5, "label": "Preprocessing image..."})
            color_img, gray, denoised = preprocess(tmp_path)

            # Auto-detect mode or use override
            detected_mode = detect_mode(gray)
            active_mode = mode if mode in ("object", "pattern") else detected_mode

            yield _sse({"step": "extracting", "percent": 10,
                        "label": f"Mode: {active_mode} — Running 6 trace approaches..."})

            loop = asyncio.get_event_loop()

            # Run ALL 6 extractors concurrently with mode + color image
            cv_tasks = {
                cat: loop.run_in_executor(
                    None, extract_all, denoised, cat, active_mode, color_img)
                for cat in ALL_CATEGORIES
            }

            traces = {}
            for i, cat in enumerate(ALL_CATEGORIES):
                try:
                    data = await cv_tasks[cat]
                    traces[cat] = _serialize_extraction(data)
                except Exception as e:
                    logger.warning("Extraction failed for %s: %s", cat, str(e))
                    traces[cat] = {}
                pct = 10 + int((i + 1) / len(ALL_CATEGORIES) * 85)
                yield _sse({"step": "extracting", "percent": pct, "label": f"Traced: {cat} ({i+1}/6)"})

            # Store full trace data server-side
            trace_id = str(uuid.uuid4())
            _traces[trace_id] = {
                "traces": traces,
                "image_dimensions": [w, h],
                "mode": active_mode,
            }

            result = {
                "trace_id": trace_id,
                "traces": traces,
                "image_dimensions": [w, h],
                "detected_mode": detected_mode,
                "active_mode": active_mode,
            }
            yield _sse({"step": "done", "percent": 100, "label": "All traces complete!", "result": result})

        except Exception as e:
            logger.error("Trace failed: %s", str(e))
            yield _sse({"step": "error", "percent": 0, "label": str(e)})
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _resize_for_ollama(image_path: str, max_dim: int = 1024) -> str:
    """Downscale image for Ollama classification if it exceeds max_dim.

    Returns path to resized temp file, or original path if already small enough.
    """
    img = cv2.imread(image_path)
    if img is None:
        return image_path
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return image_path
    scale = max_dim / max(h, w)
    resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    cv2.imwrite(tmp.name, resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return tmp.name


@app.post("/api/generate")
async def generate(file: UploadFile = File(...), brief_json: str = Form(default=""),
                   trace_id: str = Form(default=""), trace_category: str = Form(default="")):
    """Full pipeline with SSE progress: upload → generate → stream results.

    If trace_id + trace_category are provided (from a prior /api/trace call),
    skips LLM+CV and uses the cached extraction data — much faster.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    img_array = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    h, w = img.shape[:2]

    # Parse optional brief
    brief_params = None
    if brief_json:
        try:
            brief_data = json_mod.loads(brief_json)
            validated = validate_brief(brief_data)
            if not validated["valid"]:
                raise HTTPException(status_code=400, detail=f"Invalid brief: {validated['errors']}")
            brief_params = brief_to_gen_params(brief_data, building_index=0)
        except json_mod.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid brief JSON")

    suffix = os.path.splitext(file.filename or "img.png")[1] or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    # Look up cached trace data from /api/trace if trace_id provided
    cached_trace = None
    if trace_id and trace_category:
        cached_trace = _traces.get(trace_id)
        if cached_trace and trace_category not in (cached_trace.get("traces") or {}):
            cached_trace = None  # category not found in this trace

    async def event_stream():
        resized_path = None
        loop = asyncio.get_event_loop()
        try:
            if cached_trace:
                # ── Fast path: use cached trace data ──
                category = trace_category
                extraction_data_serialized = cached_trace["traces"][category]

                yield _sse({"step": "generating", "percent": 30, "label": f"Using {category} trace — generating 3D..."})
            else:
                # ── Full path: run LLM + CV from scratch ──
                yield _sse({"step": "preprocessing", "percent": 5, "label": "Preprocessing image..."})
                _, _, denoised = preprocess(tmp_path)

                yield _sse({"step": "analyzing", "percent": 10, "label": "Analyzing patterns (LLM + CV)..."})
                resized_path = _resize_for_ollama(tmp_path)

                llm_task = asyncio.create_task(classify_image(resized_path))
                cv_task = loop.run_in_executor(None, extract_all, denoised, "cellular")

                classification = await llm_task
                category = classification.get("category", "cellular")
                if category not in ("cellular", "branching", "shell", "lattice", "spiral", "porous"):
                    category = "cellular"

                yield _sse({"step": "extracting", "percent": 50, "label": f"Pattern detected: {category} — extracting features..."})

                preliminary_data = await cv_task
                if category != "cellular":
                    extraction_data = await loop.run_in_executor(None, extract_all, denoised, category)
                else:
                    extraction_data = preliminary_data

                extraction_data_serialized = _serialize_extraction(extraction_data)

            yield _sse({"step": "generating", "percent": 70, "label": "Generating 3D variations..."})

            # ── Generate variations ──
            analysis = {
                "category": category,
                "confidence": 0.0,
                "rationale": "",
                "architectural_suggestions": [],
                "extraction_data": extraction_data_serialized,
                "image_dimensions": [w, h],
            }
            if brief_params:
                analysis["brief"] = brief_params

            # Generate each variation individually with progress + timeout
            session_id = str(uuid.uuid4())
            output_dir = tempfile.mkdtemp(prefix="bioform_")
            file_records = []
            num_vars = min(3, len(VARIATION_CONFIGS))

            for i in range(num_vars):
                var_name = VARIATION_CONFIGS[i]["name"]
                yield _sse({"step": "generating", "percent": 70 + int(i / num_vars * 20),
                            "label": f"Generating {var_name} ({i+1}/{num_vars})..."})

                try:
                    var = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, generate_single_variation, i,
                            extraction_data_serialized, brief_params or DEFAULT_BRIEF,
                            category, None
                        ),
                        timeout=30.0  # 30 second timeout per variation
                    )
                except asyncio.TimeoutError:
                    logger.error("Variation %d (%s) timed out after 30s", i, var_name)
                    yield _sse({"step": "error", "percent": 0,
                                "label": f"Generation timed out on {var_name}. Try a simpler image or different trace."})
                    return

                filename_3dm = f"{category}_{var['name'].lower().replace(' ', '_')}_{i}.3dm"
                filepath_3dm = os.path.join(output_dir, filename_3dm)
                var["model"].Write(filepath_3dm, 8)

                editable_params = {}
                if i < len(VARIATION_CONFIGS):
                    editable_params = VARIATION_CONFIGS[i].get("editable_params", {})

                file_records.append({
                    "name": var["name"],
                    "description": var["description"],
                    "file_id": f"{session_id}_{i}",
                    "filename": filename_3dm,
                    "editable_params": editable_params,
                })

                _generated_files[f"{session_id}_{i}"] = {
                    "path": filepath_3dm,
                    "filename": filename_3dm,
                }

            _sessions[session_id] = {
                "extraction_data": extraction_data_serialized,
                "brief_params": brief_params or DEFAULT_BRIEF,
                "category": category,
                "output_dir": output_dir,
            }

            ghx_xml = build_ghx_for_category(category)
            ghx_filename = f"{category}_parametric.ghx"
            ghx_path = os.path.join(output_dir, ghx_filename)
            with open(ghx_path, "w", encoding="utf-8") as f:
                f.write(ghx_xml)

            ghx_file_id = f"{session_id}_ghx"
            _generated_files[ghx_file_id] = {
                "path": ghx_path,
                "filename": ghx_filename,
            }

            # ── Done (100%) — send final result ──
            # classification only exists on the full path (no trace_id);
            # on the fast path we don't have LLM output.
            if cached_trace:
                analysis_summary = {
                    "category": category,
                    "confidence": 1.0,
                    "rationale": f"User selected {category} trace.",
                    "architectural_suggestions": [],
                }
            else:
                analysis_summary = {
                    "category": category,
                    "confidence": classification.get("confidence", 0.0),
                    "rationale": classification.get("rationale", ""),
                    "architectural_suggestions": classification.get("architectural_suggestions", []),
                }
            result = {
                "session_id": session_id,
                "analysis": analysis_summary,
                "variations": file_records,
                "ghx": {
                    "file_id": ghx_file_id,
                    "filename": ghx_filename,
                },
                "scales": {
                    name: apply_scale(analysis, name)
                    for name in ["module", "small", "large"]
                },
            }
            yield _sse({"step": "done", "percent": 100, "label": "Complete!", "result": result})

        except Exception as e:
            logger.error("Generation failed: %s", str(e))
            yield _sse({"step": "error", "percent": 0, "label": str(e)})
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if resized_path and resized_path != tmp_path and os.path.exists(resized_path):
                os.unlink(resized_path)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(data: dict) -> str:
    """Format a Server-Sent Events message."""
    return f"data: {json_mod.dumps(data)}\n\n"


@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    """Download a generated .3dm or .ghx file."""
    record = _generated_files.get(file_id)
    if not record or not os.path.exists(record["path"]):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=record["path"],
        filename=record["filename"],
        media_type="application/octet-stream",
    )


class RegenerateRequest(BaseModel):
    session_id: str
    variation_index: int
    custom_params: dict = {}


@app.post("/api/regenerate-variation")
async def regenerate_variation(req: RegenerateRequest):
    """Regenerate a single variation with custom parameters (no image re-upload)."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found — try generating again")

    if req.variation_index < 0 or req.variation_index >= len(VARIATION_CONFIGS):
        raise HTTPException(status_code=400, detail=f"Invalid variation index: {req.variation_index}")

    try:
        result = generate_single_variation(
            variation_index=req.variation_index,
            extraction_data=session["extraction_data"],
            brief_params=session["brief_params"],
            category=session["category"],
            custom_params=req.custom_params,
        )

        # Write new .3dm file
        config = VARIATION_CONFIGS[req.variation_index]
        category = session["category"]
        suffix = uuid.uuid4().hex[:6]
        filename_3dm = f"{category}_{config['name'].lower().replace(' ', '_')}_{suffix}.3dm"
        filepath_3dm = os.path.join(session["output_dir"], filename_3dm)
        result["model"].Write(filepath_3dm, 8)

        file_id = f"{req.session_id}_{req.variation_index}"
        _generated_files[file_id] = {
            "path": filepath_3dm,
            "filename": filename_3dm,
        }

        return {
            "file_id": file_id,
            "filename": filename_3dm,
            "name": config["name"],
            "description": config["description"],
            "custom_params": req.custom_params,
        }
    except Exception as e:
        logger.error("Regeneration failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")


UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

# Nature/biomimicry keywords to append to searches for better results
_NATURE_BOOST = " nature macro texture close-up pattern"


@app.get("/api/search-images")
async def search_images(q: str = Query(..., min_length=1), per_page: int = Query(12, le=30)):
    """Search Unsplash for nature images. Returns thumbnails + download URLs."""
    if not UNSPLASH_ACCESS_KEY:
        raise HTTPException(
            status_code=503,
            detail="Unsplash API key not configured. Set UNSPLASH_ACCESS_KEY environment variable. "
                   "Get a free key at https://unsplash.com/developers",
        )

    search_query = q + _NATURE_BOOST

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.unsplash.com/search/photos",
            params={"query": search_query, "per_page": per_page, "orientation": "squarish"},
            headers={
                "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
                "User-Agent": "BioForm/1.0",
            },
        )
        if resp.status_code == 403:
            remaining = resp.headers.get("X-Ratelimit-Remaining", "?")
            logger.warning("Unsplash rate limit hit. Remaining: %s", remaining)
            raise HTTPException(status_code=429, detail="Unsplash API rate limit reached. Try again later.")
        if resp.status_code != 200:
            logger.warning("Unsplash search failed: HTTP %d", resp.status_code)
            raise HTTPException(status_code=502, detail=f"Unsplash search failed (HTTP {resp.status_code})")

        data = resp.json()
        results = []
        for photo in data.get("results", []):
            results.append({
                "id": photo["id"],
                "thumb": photo["urls"]["thumb"],        # 200px thumbnail
                "small": photo["urls"]["small"],         # 400px
                "regular": photo["urls"]["regular"],     # 1080px — used for analysis
                "alt": photo.get("alt_description", ""),
                "author": photo["user"]["name"],
                "link": photo["links"]["html"],
            })

        return {"results": results, "total": data.get("total", 0)}


@app.get("/api/proxy-image")
async def proxy_image(url: str = Query(...)):
    """Download an image from URL and return it. Used to avoid CORS issues with Unsplash."""
    # Only allow Unsplash URLs for security
    if not url.startswith("https://images.unsplash.com/"):
        raise HTTPException(status_code=400, detail="Only Unsplash image URLs are allowed")

    headers = {
        "User-Agent": "BioForm/1.0 (Nature Pattern Analyzer)",
        "Accept": "image/jpeg,image/png,image/webp,image/*",
    }

    last_error = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return Response(
                        content=resp.content,
                        media_type=resp.headers.get("content-type", "image/jpeg"),
                        headers={"Cache-Control": "public, max-age=86400"},
                    )
                last_error = f"HTTP {resp.status_code}"
                logger.warning("Proxy image attempt %d failed: %s for %s", attempt + 1, last_error, url[:80])
        except httpx.TimeoutException:
            last_error = "timeout"
            logger.warning("Proxy image attempt %d timed out for %s", attempt + 1, url[:80])
        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning("Proxy image attempt %d error: %s for %s", attempt + 1, last_error, url[:80])

    raise HTTPException(status_code=502, detail=f"Failed to fetch image: {last_error}")


# Large image-sized arrays that are only used during backend processing.
# These must NOT be sent to the frontend — they can be megabytes each.
_BULK_KEYS = {"skeleton", "height_map", "curvature_map", "curvature_coarse",
              "curvature_fine", "gradient_magnitude",
              "radial_fine"}


def _serialize_extraction(data: dict) -> dict:
    """Convert numpy arrays and other non-serializable types to lists/primitives.

    Strips out bulk image-sized arrays that the frontend doesn't need for drawing.
    """
    result = {}
    for key, value in data.items():
        if key in _BULK_KEYS:
            continue
        if isinstance(value, np.ndarray):
            result[key] = value.tolist()
        elif isinstance(value, (list, tuple)):
            result[key] = _serialize_list(value)
        elif isinstance(value, (np.integer,)):
            result[key] = int(value)
        elif isinstance(value, (np.floating,)):
            result[key] = float(value)
        else:
            result[key] = value
    return result


def _serialize_list(lst):
    """Recursively serialize list elements."""
    result = []
    for item in lst:
        if isinstance(item, np.ndarray):
            result.append(item.tolist())
        elif isinstance(item, dict):
            result.append({k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in item.items()})
        elif isinstance(item, (list, tuple)):
            result.append(_serialize_list(item))
        elif isinstance(item, (np.integer,)):
            result.append(int(item))
        elif isinstance(item, (np.floating,)):
            result.append(float(item))
        else:
            result.append(item)
    return result
