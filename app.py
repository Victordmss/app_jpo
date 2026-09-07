"""AI Wheel Design Studio - Stellantis.

Faithful reproduction of the mockup screenshot:
- Header with gradient + STELLANTIS text
- Database bar with draggable wheel thumbnails (drag & drop to select)
- Model A / Mix / Model B cards as drop zones
- Interpolation explorer when result is ready
"""

import base64
import json
import re
import time
from pathlib import Path
from typing import Optional

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import trimesh

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
STYLES_PATH = ASSETS_DIR / "styles.css"
RIMS_MANIFEST = DATA_DIR / "rims.json"
INTERPOLATIONS_DIR = ASSETS_DIR / "stl" / "interpolations"

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Wheel Design Studio",
    page_icon="\u2699\ufe0f",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------


def inject_css() -> None:
    """Load and inject custom CSS."""
    if STYLES_PATH.exists():
        css = STYLES_PATH.read_text(encoding="utf-8")
    else:
        css = ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


inject_css()

# Keep-alive: prevent compute auto-stop by sending a heartbeat every 5 min
st.components.v1.html(
    '<script>setInterval(()=>fetch("/_stcore/health"),300000)</script>',
    height=0,
)


# ---------------------------------------------------------------------------
# Data loading (preserved logic)
# ---------------------------------------------------------------------------


@st.cache_data
def load_rims_manifest() -> list[dict]:
    """Load the rims JSON manifest."""
    if not RIMS_MANIFEST.exists():
        return []
    with open(RIMS_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_stl_mesh(path: str) -> Optional[tuple[np.ndarray, np.ndarray]]:
    """Load an STL file and return (vertices, faces) arrays."""
    filepath = Path(path)
    if not filepath.exists():
        return None
    try:
        mesh = trimesh.load(str(filepath), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            geometries = list(mesh.geometry.values())
            if not geometries:
                return None
            mesh = trimesh.util.concatenate(geometries)
        if not isinstance(mesh, trimesh.Trimesh):
            return None
        return np.array(mesh.vertices, dtype=np.float32), np.array(mesh.faces, dtype=np.int32)
    except Exception:
        return None


@st.cache_data
def _image_data_uri(image_path: str) -> Optional[str]:
    """Read an image file and return it as a base64 data URI."""
    if not image_path:
        return None
    filepath = APP_DIR / image_path
    if not filepath.exists():
        return None
    suffix = filepath.suffix.lstrip(".").lower() or "png"
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    encoded = base64.b64encode(filepath.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{encoded}"


def _rim_payload(rim: Optional[dict]) -> Optional[dict]:
    """Build the JSON payload describing a rim for the drag-and-drop components."""
    if rim is None:
        return None
    return {
        "id": rim["id"],
        "name": rim["name"],
        "display_id": rim.get("display_id", rim["name"]),
        "image": _image_data_uri(rim.get("image", "")),
    }


# ---------------------------------------------------------------------------
# 3D Visualization (preserved logic)
# ---------------------------------------------------------------------------


def create_3d_figure(vertices: np.ndarray, faces: np.ndarray, color: str = "#C0C8D4") -> go.Figure:
    """Create a Plotly 3D mesh figure with metallic wheel rendering."""
    centroid = vertices.mean(axis=0)
    centered = vertices - centroid
    max_ext = np.abs(centered).max()
    scale = 1.0 / max_ext if max_ext > 0 else 1.0
    scaled = centered * scale

    fig = go.Figure(data=[go.Mesh3d(
        x=scaled[:, 0], y=scaled[:, 1], z=scaled[:, 2],
        i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
        color=color, opacity=1.0, flatshading=False,
        lighting=dict(ambient=0.65, diffuse=0.8, specular=0.6, roughness=0.3, fresnel=0.3),
        lightposition=dict(x=200, y=200, z=400),
    )])
    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
            bgcolor="#FFFFFF", aspectmode="data",
            camera=dict(eye=dict(x=1.2, y=1.2, z=0.6), center=dict(x=0, y=0, z=0), up=dict(x=0, y=0, z=1)),
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
    )
    return fig


# ---------------------------------------------------------------------------
# Interpolation resolution (preserved logic)
# ---------------------------------------------------------------------------


def resolve_interpolation_folder(rim_a_id: str, rim_b_id: str) -> Optional[tuple[Path, bool]]:
    """Find the precomputed interpolation folder and whether display direction is reversed."""
    folder_ab = INTERPOLATIONS_DIR / f"{rim_a_id}_to_{rim_b_id}"
    folder_ba = INTERPOLATIONS_DIR / f"{rim_b_id}_to_{rim_a_id}"
    if folder_ab.exists() and folder_ab.is_dir():
        return folder_ab, False
    if folder_ba.exists() and folder_ba.is_dir():
        return folder_ba, True
    return None


def _extract_interpolation_step(path: Path) -> int:
    """Extract the numeric interpolation step from a filename."""
    match = re.search(r"(\d+)$", path.stem)
    return int(match.group(1)) if match else -1


def get_interpolation_files(folder: Path, ext: str = "png") -> list[tuple[int, Path]]:
    """Get numerically sorted interpolation files by extension."""
    files = list(folder.glob(f"interpolation_*.{ext}"))
    return sorted(
        ((
            _extract_interpolation_step(path),
            path,
        ) for path in files),
        key=lambda item: item[0],
    )


# ---------------------------------------------------------------------------
# Drag-and-drop components (st.components.v2) - real HTML5 DnD, no sandbox
# ---------------------------------------------------------------------------

_DB_HTML = """
<div class="db-bar">
    <div class="db-label">
        <svg width="38" height="38" viewBox="0 0 38 38" fill="none">
            <ellipse cx="19" cy="9" rx="12" ry="5" fill="#7B9FD4" stroke="#1D1472" stroke-width="1.5"/>
            <path d="M7 9v7c0 2.8 5.4 5 12 5s12-2.2 12-5V9" stroke="#1D1472" stroke-width="1.5" fill="none"/>
            <path d="M7 16v7c0 2.8 5.4 5 12 5s12-2.2 12-5v-7" stroke="#1D1472" stroke-width="1.5" fill="none"/>
        </svg>
        <div>
            <div class="db-title">Database</div>
            <div class="db-subtitle">Glissez un modèle vers une case Model</div>
        </div>
    </div>
    <div class="db-thumbs" id="db-thumbs"></div>
</div>
"""

_DB_CSS = """
* { box-sizing: border-box; }
.db-bar {
    font-family: 'Source Sans Pro', Arial, sans-serif;
    background: linear-gradient(90deg, #2C3998, #3B4FC0);
    border-radius: 16px;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
}
.db-label {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 190px;
    flex-shrink: 0;
}
.db-title {
    color: #fff;
    font-size: 22px;
    font-weight: 700;
    font-style: italic;
}
.db-subtitle {
    color: #8BA4E0;
    font-size: 12px;
}
.db-thumbs {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    overflow-x: auto;
    flex: 1;
    padding: 4px 2px;
}
.db-thumb {
    position: relative;
    width: 84px;
    min-width: 84px;
    height: 96px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.15);
    border: 2px solid transparent;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 6px 4px;
    cursor: grab;
    transition: filter 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.db-thumb:hover {
    transform: translateY(-2px);
}
.db-thumb:active {
    cursor: grabbing;
}
.db-thumb img {
    width: 42px;
    height: 42px;
    object-fit: contain;
    pointer-events: none;
}
.db-thumb-icon {
    font-size: 26px;
    color: rgba(255, 255, 255, 0.6);
    pointer-events: none;
}
.db-thumb-caption {
    margin-top: 4px;
    color: #E3E8FF;
    text-align: center;
    line-height: 1.15;
    pointer-events: none;
    max-width: 76px;
}
.db-thumb-id {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.db-thumb-name {
    font-size: 8.5px;
    opacity: 0.9;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.db-thumb.is-selected {
    filter: brightness(0.45);
    border-color: rgba(255, 255, 255, 0.85);
}
.db-thumb-check {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #26C281;
    color: #fff;
    font-size: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}
"""

_DB_JS = """
export default function(component) {
    const { data, parentElement } = component;
    const rims = (data && data.rims) || [];
    const selectedIds = new Set(
        [data && data.selected_a, data && data.selected_b].filter(Boolean)
    );

    const thumbsEl = parentElement.querySelector('#db-thumbs');
    thumbsEl.innerHTML = '';

    rims.forEach((rim) => {
        const isSelected = selectedIds.has(rim.id);

        const thumb = document.createElement('div');
        thumb.className = 'db-thumb' + (isSelected ? ' is-selected' : '');
        thumb.draggable = true;
        thumb.title = rim.name;

        if (rim.image) {
            const img = document.createElement('img');
            img.src = rim.image;
            img.alt = rim.name;
            img.draggable = false;
            thumb.appendChild(img);
        } else {
            const icon = document.createElement('div');
            icon.className = 'db-thumb-icon';
            icon.textContent = '⚙';
            thumb.appendChild(icon);
        }

        const caption = document.createElement('div');
        caption.className = 'db-thumb-caption';

        const idLine = document.createElement('div');
        idLine.className = 'db-thumb-id';
        idLine.textContent = rim.display_id || rim.name;
        caption.appendChild(idLine);

        const nameLine = document.createElement('div');
        nameLine.className = 'db-thumb-name';
        nameLine.textContent = rim.name;
        caption.appendChild(nameLine);

        thumb.appendChild(caption);

        if (isSelected) {
            const check = document.createElement('div');
            check.className = 'db-thumb-check';
            check.textContent = '✓';
            thumb.appendChild(check);
        }

        thumb.addEventListener('dragstart', (e) => {
            e.dataTransfer.effectAllowed = 'copy';
            e.dataTransfer.setData('text/plain', rim.id);
        });

        thumbsEl.appendChild(thumb);
    });
}
"""

_CARD_HTML = """
<div class="wc-card" id="wc-root"></div>
"""

_CARD_CSS = """
* { box-sizing: border-box; }
.wc-card {
    font-family: 'Source Sans Pro', Arial, sans-serif;
    background: #F2F2F2;
    border-radius: 32px;
    padding: 28px 20px;
    text-align: center;
    min-height: 260px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    border: 2px dashed transparent;
    transition: border-color 0.15s ease, background 0.15s ease;
    position: relative;
}
.wc-card.is-dragover {
    border-color: #2C3998;
    background: #E7EAF8;
}
.wc-title {
    font-size: 22px;
    font-weight: 700;
    color: #1B2A4A;
    margin: 0 0 8px 0;
}
.wc-drop-icon {
    font-size: 30px;
    color: #555;
}
.wc-hint {
    color: #ADADAD;
    font-size: 11px;
    font-style: italic;
    margin-top: 8px;
}
.wc-hint span {
    color: #EF3D3D;
}
.wc-id {
    font-size: 32px;
    font-weight: 800;
    color: #1B2A4A;
    margin: 0;
    letter-spacing: 0.06em;
}
.wc-name {
    font-size: 14px;
    font-weight: 600;
    color: #5E6A7D;
    margin: -4px 0 0 0;
}
.wc-image-wrap {
    width: 100%;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.wc-image-wrap img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    pointer-events: none;
}
.wc-placeholder-icon {
    font-size: 3rem;
    color: #ADADAD;
}
.wc-remove {
    position: absolute;
    top: 14px;
    right: 14px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    background: #fff;
    color: #555;
    font-size: 13px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
.wc-remove:hover {
    background: #EF3D3D;
    color: #fff;
}
"""

_CARD_JS = """
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    const root = parentElement.querySelector('#wc-root');
    const rim = data && data.rim;
    const otherRimId = data && data.other_rim_id;
    const label = (data && data.slot_label) || '';

    root.innerHTML = '';
    root.classList.toggle('is-filled', !!rim);

    if (rim) {
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'wc-remove';
        removeBtn.textContent = '✕';
        removeBtn.title = 'Retirer';
        removeBtn.onclick = () => setTriggerValue('removed', true);
        root.appendChild(removeBtn);

        const idEl = document.createElement('p');
        idEl.className = 'wc-id';
        idEl.textContent = rim.display_id || rim.name;
        root.appendChild(idEl);

        const nameEl = document.createElement('p');
        nameEl.className = 'wc-name';
        nameEl.textContent = rim.name;
        root.appendChild(nameEl);

        const imgWrap = document.createElement('div');
        imgWrap.className = 'wc-image-wrap';
        if (rim.image) {
            const img = document.createElement('img');
            img.src = rim.image;
            img.alt = rim.name;
            imgWrap.appendChild(img);
        } else {
            const icon = document.createElement('div');
            icon.className = 'wc-placeholder-icon';
            icon.textContent = '⚙';
            imgWrap.appendChild(icon);
        }
        root.appendChild(imgWrap);
    } else {
        const title = document.createElement('p');
        title.className = 'wc-title';
        title.textContent = label;
        root.appendChild(title);

        const icon = document.createElement('div');
        icon.className = 'wc-drop-icon';
        icon.textContent = '+';
        root.appendChild(icon);

        const hint = document.createElement('p');
        hint.className = 'wc-hint';
        hint.innerHTML = 'Glissez <span>votre donnée</span> ici';
        root.appendChild(hint);
    }

    root.ondragover = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        root.classList.add('is-dragover');
    };
    root.ondragleave = () => {
        root.classList.remove('is-dragover');
    };
    root.ondrop = (e) => {
        e.preventDefault();
        root.classList.remove('is-dragover');
        const droppedId = e.dataTransfer.getData('text/plain');
        if (!droppedId || droppedId === otherRimId) {
            return;
        }
        setTriggerValue('dropped', droppedId);
    };
}
"""

wheel_database = st.components.v2.component("wheel_database", html=_DB_HTML, css=_DB_CSS, js=_DB_JS)
wheel_card = st.components.v2.component("wheel_card", html=_CARD_HTML, css=_CARD_CSS, js=_CARD_JS)

_SLIDER_HTML = """
<div class="blend-slider-wrap" id="blend-slider-root">
    <input type="range" class="blend-slider-input" id="blend-slider-input" />
</div>
"""

_SLIDER_CSS = """
* { box-sizing: border-box; }
.blend-slider-wrap {
    width: 100%;
    padding: 8px 6px 2px 6px;
}
.blend-slider-input {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 4px;
    border-radius: 999px;
    outline: none;
    background: linear-gradient(to right, #F04D4D var(--pct, 0%), #D9DDE7 var(--pct, 0%));
}
.blend-slider-input::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: none;
    background: #F04D4D;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
}
.blend-slider-input::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: none;
    background: #F04D4D;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
}
.blend-slider-input.is-reversed {
    direction: rtl;
}
"""

_SLIDER_JS = """
export default function(component) {
    const { data, parentElement, setTriggerValue } = component;
    const input = parentElement.querySelector('#blend-slider-input');
    const min = Number(data && data.min_step);
    const max = Number(data && data.max_step);
    const value = Number(data && data.value);
    const reversed = Boolean(data && data.reversed);

    input.min = Number.isFinite(min) ? min : 0;
    input.max = Number.isFinite(max) ? max : 0;
    input.step = 1;
    input.classList.toggle('is-reversed', reversed);

    /* Only set value from server when user is NOT actively dragging */
    if (!input._dragging) {
        input.value = Number.isFinite(value) ? value : input.min;
    }

    const paint = () => {
        const denom = Math.max(1, Number(input.max) - Number(input.min));
        let pct = ((Number(input.value) - Number(input.min)) / denom) * 100;
        if (reversed) pct = 100 - pct;
        input.style.setProperty('--pct', `${pct}%`);
    };
    paint();

    /* Debounce: fire rerun only after user pauses 150 ms */
    clearTimeout(input._debounceTimer);

    input.onpointerdown = () => { input._dragging = true; };
    input.onpointerup = () => {
        input._dragging = false;
        /* Send final value immediately on release */
        clearTimeout(input._debounceTimer);
        setTriggerValue('value', Number(input.value));
    };

    input.oninput = () => {
        paint();
        clearTimeout(input._debounceTimer);
        input._debounceTimer = setTimeout(() => {
            setTriggerValue('value', Number(input.value));
        }, 150);
    };
}
"""

blend_slider = st.components.v2.component(
    "blend_slider",
    html=_SLIDER_HTML,
    css=_SLIDER_CSS,
    js=_SLIDER_JS,
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "selected_a" not in st.session_state:
    st.session_state.selected_a = None
if "selected_b" not in st.session_state:
    st.session_state.selected_b = None
if "interpolation_ready" not in st.session_state:
    st.session_state.interpolation_ready = False
if "interpolation_files" not in st.session_state:
    st.session_state.interpolation_files = []
if "interpolation_stl_files" not in st.session_state:
    st.session_state.interpolation_stl_files = {}
if "current_step" not in st.session_state:
    st.session_state.current_step = 0
if "interpolation_reverse" not in st.session_state:
    st.session_state.interpolation_reverse = False
if "interpolation_steps" not in st.session_state:
    st.session_state.interpolation_steps = []


def clear_interpolation():
    """Reset interpolation state."""
    st.session_state.interpolation_ready = False
    st.session_state.interpolation_files = []
    st.session_state.interpolation_stl_files = {}
    st.session_state.interpolation_steps = []
    st.session_state.interpolation_reverse = False
    st.session_state.current_step = 0


# ---------------------------------------------------------------------------
# UI: Header (matches screenshot)
# ---------------------------------------------------------------------------


def render_header():
    """Header: car logo above-right + gradient bar with title + Stellantis logo."""
    car_logo = _image_data_uri("assets/logo.jpg")
    stellantis_logo = _image_data_uri("assets/stellantis_logo.png")
    st.markdown(f"""
    <div style="margin-top:-16px; margin-bottom:12px;">
        <div style="display:flex; justify-content:flex-end;">
            <img src="{car_logo}" alt="" style="width:150px; height:100px; object-fit:contain;" />
        </div>
        <div style="background:linear-gradient(90deg,#1D1472,#2C3998); border-radius:14px; padding:14px 36px; display:flex; align-items:center; justify-content:space-between;">
            <h1 style="color:white; font-size:36px; font-weight:700; font-style:italic; margin:0;">AI Wheel Design Studio</h1>
            <img src="{stellantis_logo}" alt="STELLANTIS" style="height:48px; width:auto; object-fit:contain;" />
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UI: Database bar (matches screenshot)
# ---------------------------------------------------------------------------


def render_database_bar(rims: list[dict]):
    """Database bar with draggable wheel thumbnails (drag one onto a Model card)."""
    data = {
        "rims": [_rim_payload(rim) for rim in rims[:8]],
        "selected_a": st.session_state.selected_a,
        "selected_b": st.session_state.selected_b,
    }
    wheel_database(data=data, key="wheel_database_bar")
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# UI: Work zone - Model A / Mix / Model B (matches screenshot)
# ---------------------------------------------------------------------------


def render_work_zone(rims: list[dict]):
    """Three-column layout: Model A | Mix | Model B."""
    rims_by_id = {r["id"]: r for r in rims}
    col_a, col_mix, col_b = st.columns([1, 1, 1], gap="large")

    with col_a:
        _mount_wheel_card("a", "Model A", rims_by_id)

    with col_mix:
        _render_center(rims)

    with col_b:
        _mount_wheel_card("b", "Model B", rims_by_id)


def _mount_wheel_card(slot: str, label: str, rims_by_id: dict) -> None:
    """Mount a Model A/B drop-zone card and apply pending drag-and-drop events."""
    session_key = "selected_a" if slot == "a" else "selected_b"
    other_key = "selected_b" if slot == "a" else "selected_a"

    data = {
        "slot_label": label,
        "rim": _rim_payload(rims_by_id.get(st.session_state[session_key])),
        "other_rim_id": st.session_state[other_key],
    }
    result = wheel_card(
        data=data,
        key=f"wheel_card_{slot}",
        on_dropped_change=lambda: None,
        on_removed_change=lambda: None,
    )

    if (
        result.dropped
        and result.dropped != st.session_state[other_key]
        and result.dropped != st.session_state[session_key]
    ):
        st.session_state[session_key] = result.dropped
        clear_interpolation()
        st.rerun()
    elif result.removed:
        st.session_state[session_key] = None
        clear_interpolation()
        st.rerun()


def _render_center(rims: list[dict]):
    """Center zone: Mix button or interpolation result."""
    if st.session_state.interpolation_ready:
        _render_result()
    else:
        # Mix button
        st.markdown('<div style="height:80px;"></div>', unsafe_allow_html=True)
        both_selected = st.session_state.selected_a and st.session_state.selected_b
        if st.button("Mix", key="mix_btn", disabled=not both_selected, use_container_width=True):
            _run_mix()


def _run_mix():
    """Run the mix/interpolation process."""
    sel_a = st.session_state.selected_a
    sel_b = st.session_state.selected_b

    progress_bar = st.progress(0)
    for pct in [25, 50, 75, 100]:
        progress_bar.progress(pct / 100)
        time.sleep(0.5)

    result = resolve_interpolation_folder(sel_a, sel_b)
    progress_bar.empty()

    if result is None:
        st.warning("Aucune interpolation disponible pour cette paire.")
        return

    folder, reverse_display = result
    png_files = [(step, path) for step, path in get_interpolation_files(folder, "png") if step >= 0]
    stl_files = {step: str(path) for step, path in get_interpolation_files(folder, "stl") if step >= 0}
    if not png_files:
        st.warning("Aucune image d'interpolation disponible pour cette paire.")
        return

    step_numbers = [step for step, _ in png_files]
    st.session_state.interpolation_ready = True
    st.session_state.interpolation_files = {
        step: str(path) for step, path in png_files
    }
    st.session_state.interpolation_stl_files = stl_files
    st.session_state.interpolation_steps = step_numbers
    st.session_state.interpolation_reverse = reverse_display
    st.session_state.current_step = max(step_numbers) if reverse_display else min(step_numbers)
    st.rerun()


@st.dialog("Modèle 3D", width="large")
def _show_3d_viewer(stl_path: str):
    """Popup dialog showing the interactive 3D STL viewer."""
    mesh_data = load_stl_mesh(stl_path)
    if mesh_data:
        vertices, faces = mesh_data
        fig = create_3d_figure(vertices, faces)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Impossible de charger le modèle 3D.")


def _render_result():
    """Show interpolation result with PNG images and optional 3D viewer."""
    files = st.session_state.interpolation_files
    stl_files = st.session_state.get("interpolation_stl_files", {})
    step_numbers = st.session_state.interpolation_steps
    if not files or not step_numbers:
        return

    slider_options = list(reversed(step_numbers)) if st.session_state.interpolation_reverse else step_numbers
    default_step = st.session_state.current_step
    if default_step not in slider_options:
        default_step = slider_options[0]

    step = st.select_slider(
        "Blend",
        options=slider_options,
        value=default_step,
        key="blend_slider",
        label_visibility="collapsed",
    )
    st.session_state.current_step = step

    png_path = files.get(step)
    if png_path and Path(png_path).exists():
        st.image(png_path, use_container_width=True)
    else:
        st.info("Image d'interpolation introuvable.")

    stl_path = stl_files.get(step)
    if stl_path and Path(stl_path).exists():
        if st.button("Voir le modèle", key=f"view_3d_{step}", use_container_width=True):
            _show_3d_viewer(stl_path)

    if st.button("Restart", key="restart_btn", use_container_width=True):
        st.session_state.selected_a = None
        st.session_state.selected_b = None
        clear_interpolation()
        st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    render_header()
    rims = load_rims_manifest()
    render_database_bar(rims)
    render_work_zone(rims)


if __name__ == "__main__":
    main()
