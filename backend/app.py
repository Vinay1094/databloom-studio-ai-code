"""Gradio frontend for Databloom Studio AI video generation.

This app provides an end-to-end UI on top of the backend.video_agent
pipeline. It assumes you have a working generate_video() implementation
in backend/video_agent.py.

Run locally:
    uvicorn backend.app:app --reload   # if you expose FastAPI as well
or simply (for pure Gradio):
    python -m backend.app

Make sure to install dependencies:
    pip install -r requirements.txt

"""

from __future__ import annotations

import json
import os
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr

try:
    # Import your production-grade video agent
    from .video_agent import generate_video  # type: ignore
except Exception:  # pragma: no cover - safe fallback in case of import issues
    # Minimal fallback so the UI still loads; shows helpful error when used.
    def generate_video(
        script: str,
        output_dir: str = "outputs",
        project_name: str = "databloom_demo",
        language: str = "en",
        voice: str = "default",
        image_style: str = "simple",
        frame_rate: int = 30,
        resolution: Tuple[int, int] = (1280, 720),
        background_music_path: Optional[str] = None,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        raise RuntimeError(
            "backend.video_agent.generate_video could not be imported. "
            "Please ensure backend/video_agent.py exists and is importable."
        )

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = BASE_DIR.parent / "outputs"
DEFAULT_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def _safe_int(value: Any, default: int) -> int:
    try:
        v = int(value)
        return v if v > 0 else default
    except Exception:
        return default


def _safe_resolution(choice: str) -> Tuple[int, int]:
    mapping = {
        "720p (1280x720)": (1280, 720),
        "1080p (1920x1080)": (1920, 1080),
        "Square (1080x1080)": (1080, 1080),
        "Vertical (1080x1920)": (1080, 1920),
    }
    return mapping.get(choice, (1280, 720))


# ---------------------------------------------------------------------------
# Script helper (simple heuristic splitter)
# ---------------------------------------------------------------------------


def split_script_into_scenes(script: str, max_chars: int = 260) -> List[str]:
    """Split a long script into scene-like chunks.

    This is a UI-only helper for preview; the backend.video_agent may
    override with its own logic. We keep this logic lightweight.
    """

    cleaned = script.strip()
    if not cleaned:
        return []

    # Prefer sentence boundaries.
    sentences = [s.strip() for s in cleaned.replace("\n", " ").split(".") if s.strip()]
    scenes: List[str] = []
    current = ""

    for sent in sentences:
        candidate = (current + " " + sent).strip() if current else sent
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                scenes.append(current)
            current = sent

    if current:
        scenes.append(current)

    return scenes


# ---------------------------------------------------------------------------
# Gradio callbacks
# ---------------------------------------------------------------------------


def on_preview_scenes(script: str) -> Tuple[str, List[str]]:
    if not script or not script.strip():
        return "Please enter a script first.", []

    scenes = split_script_into_scenes(script)
    pretty = "\n\n".join(f"Scene {i+1}: {s}" for i, s in enumerate(scenes))
    return pretty, scenes


def on_generate_video(
    topic: str,
    script: str,
    language: str,
    voice: str,
    image_style: str,
    resolution_choice: str,
    fps_text: str,
    bg_music_path: str,
    project_name: str,
) -> Tuple[str, Optional[str]]:
    """Main callback that calls backend.video_agent.generate_video.

    Returns (status_message, video_path).
    """

    if not script or not script.strip():
        if not topic or not topic.strip():
            return "Please provide either a topic or a full script.", None
        # If only topic is provided, create a tiny placeholder script.
        script = textwrap.dedent(
            f"""Intro: What is {topic}?

Key ideas about {topic}.

Summary and closing thoughts."""
        ).strip()

    fps = _safe_int(fps_text or  "30", 30)
    resolution = _safe_resolution(resolution_choice)

    # Normalise background music path
    music_path = bg_music_path.strip() or None

    status_prefix = "Starting video generation...\n"

    def progress_callback(step: str, meta: Optional[Dict[str, Any]] = None) -> None:
        # In this minimal version we just print to server logs;
        # could be extended to use Gradio streaming.
        print(f"[video_agent] {step}", json.dumps(meta or {}))

    try:
        result = generate_video(
            script=script,
            output_dir=str(DEFAULT_OUTPUT_ROOT),
            project_name=project_name or "databloom_project",
            language=language,
            voice=voice,
            image_style=image_style,
            frame_rate=fps,
            resolution=resolution,
            background_music_path=music_path,
            progress_callback=progress_callback,
        )
    except Exception as exc:
        return status_prefix + f"Error: {exc}", None

    video_path = result.get("video_path") or result.get("output_path")
    if not video_path or not os.path.exists(video_path):
        return status_prefix + "Pipeline finished but no video file was reported.", None

    rel_path = os.path.relpath(video_path, start=DEFAULT_OUTPUT_ROOT)
    msg = status_prefix + f"Done! Video saved at: {video_path}\n(Relative to outputs/: {rel_path})"
    return msg, video_path


# ---------------------------------------------------------------------------
# Gradio UI definition
# ---------------------------------------------------------------------------


def build_interface() -> gr.Blocks:
    with gr.Blocks(theme=gr.themes.Soft(), css="""
    .db-header {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 700;
        font-size: 1.6rem;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .db-subtitle {
        font-size: 0.95rem;
        color: #4b5563;
        margin-bottom: 16px;
    }
    .db-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: #e0f2fe;
        color: #0369a1;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .db-footer {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 18px;
        text-align: center;
    }
    """) as demo:
        gr.Markdown(
            """
<div class="db-header">Databloom Studio AI – Video Generator</div>
<div class="db-subtitle">Turn your ideas and scripts into narrated, image-backed videos.</div>
<div class="db-pill">⚙️ Backend: <span>video_agent.generate_video</span></div>
""",
            elem_id="db_header",
        )

        with gr.Row():
            with gr.Column(scale=3):
                topic = gr.Textbox(
                    label="Topic (optional if script is provided)",
                    placeholder="e.g. Introduction to Generative AI",
                )
                script = gr.Textbox(
                    label="Script", lines=14,
                    placeholder=(
                        "Paste your full narration script here. "
                        "If empty, a placeholder will be generated from the topic."
                    ),
                )

                with gr.Accordion("Advanced script tools", open=False):
                    preview_btn = gr.Button("Preview scene breakdown", variant="secondary")
                    scene_preview = gr.Markdown(label="Scene breakdown preview")
                    hidden_scenes = gr.State([])  # currently unused, but kept for extensibility

            with gr.Column(scale=2):
                language = gr.Dropdown(
                    label="Narration language",
                    choices=[
                        "en", "hi", "es", "fr", "de",
                    ],
                    value="en",
                )
                voice = gr.Textbox(
                    label="Voice preset or name",
                    value="default",
                    placeholder="Depends on your TTS setup (e.g., 'en_male_1')",
                )

                image_style = gr.Dropdown(
                    label="Image style",
                    choices=[
                        "simple",
                        "gradient",
                        "photo",
                        "sketch",
                    ],
                    value="simple",
                )

                resolution_choice = gr.Dropdown(
                    label="Resolution",
                    choices=[
                        "720p (1280x720)",
                        "1080p (1920x1080)",
                        "Square (1080x1080)",
                        "Vertical (1080x1920)",
                    ],
                    value="720p (1280x720)",
                )

                fps_text = gr.Textbox(
                    label="Frames per second",
                    value="30",
                    max_lines=1,
                )

                bg_music_path = gr.Textbox(
                    label="Background music file (optional)",
                    placeholder="Path on server, e.g. assets/music/soft_ambient.mp3",
                )

                project_name = gr.Textbox(
                    label="Project name (folder)",
                    value="databloom_demo",
                )

                generate_btn = gr.Button("Generate video", variant="primary")

                status = gr.Textbox(
                    label="Status", lines=6,
                    interactive=False,
                )
                video_out = gr.Video(label="Generated video preview")

        # Wiring callbacks
        preview_btn.click(
            fn=on_preview_scenes,
            inputs=[script],
            outputs=[scene_preview, hidden_scenes],
        )

        generate_btn.click(
            fn=on_generate_video,
            inputs=[
                topic,
                script,
                language,
                voice,
                image_style,
                resolution_choice,
                fps_text,
                bg_music_path,
                project_name,
            ],
            outputs=[status, video_out],
        )

        gr.Markdown(
            """<div class="db-footer">Databloom Studio AI · Gradio frontend · backend.video_agent.generate_video</div>"""
        )

    return demo


app = build_interface()


if __name__ == "__main__":
    # For local debugging: python -m backend.app
    app.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))

