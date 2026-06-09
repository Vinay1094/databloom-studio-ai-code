"""
Video Agent - Databloom Studio AI
Orchestrates video generation: images, audio, subtitles, and assembly.
"""

import os
import json
import subprocess
import time
import logging
import textwrap
from typing import Dict, List, Any
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Output directory ──────────────────────────────────────────────────────────
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

# ── Optional dependency guards ────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow not installed. Image generation will be skipped.")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed. Audio generation will be skipped.")

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not installed. Subtitle generation will be skipped.")


# ─────────────────────────────────────────────────────────────────────────────
# Image Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_scene_image(
    scene: Dict[str, Any],
    scene_index: int,
    session_id: str,
    width: int = 1280,
    height: int = 720,
) -> str:
    """
    Generate a styled slide image for a scene using Pillow.
    Returns the path to the saved PNG file.
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for image generation. Install it with: pip install pillow")

    title = scene.get("title", f"Scene {scene_index + 1}")
    narration = scene.get("narration", "")
    visual_style = scene.get("visual_style", "default")

    # Color themes per visual style
    themes = {
        "intro":      {"bg": (15, 23, 42),   "accent": (99, 102, 241),  "text": (255, 255, 255)},
        "explanation":{"bg": (17, 24, 39),   "accent": (16, 185, 129),  "text": (243, 244, 246)},
        "highlight":  {"bg": (30, 27, 75),   "accent": (245, 158, 11),  "text": (255, 255, 255)},
        "conclusion": {"bg": (7, 36, 55),    "accent": (14, 165, 233),  "text": (226, 232, 240)},
        "default":    {"bg": (10, 10, 30),   "accent": (139, 92, 246),  "text": (255, 255, 255)},
    }

    theme = themes.get(visual_style, themes["default"])
    bg_color    = theme["bg"]
    accent_color = theme["accent"]
    text_color  = theme["text"]

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Accent bar (top)
    draw.rectangle([0, 0, width, 8], fill=accent_color)
    # Accent bar (bottom)
    draw.rectangle([0, height - 8, width, height], fill=accent_color)

    # Subtle grid pattern
    for x in range(0, width, 60):
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 10), width=1)
    for y in range(0, height, 60):
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 10), width=1)

    # Load fonts (fallback to default if custom fonts not found)
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        font_body  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        font_badge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_body  = font_title
        font_badge = font_title

    # Scene badge
    badge_text = f"SCENE {scene_index + 1}"
    draw.rounded_rectangle([50, 40, 200, 80], radius=12, fill=accent_color)
    draw.text((60, 50), badge_text, fill=(255, 255, 255), font=font_badge)

    # Title
    title_y = 120
    draw.text((60, title_y), title, fill=text_color, font=font_title)

    # Divider
    draw.rectangle([60, title_y + 70, 400, title_y + 74], fill=accent_color)

    # Narration (word-wrapped)
    wrapped = textwrap.wrap(narration, width=70)
    body_y = title_y + 100
    for line in wrapped[:6]:   # max 6 lines
        draw.text((60, body_y), line, fill=text_color, font=font_body)
        body_y += 42

    # Watermark
    draw.text((width - 260, height - 50), "Databloom Studio AI", fill=accent_color, font=font_badge)

    # Save
    img_dir = os.path.join(EXPORTS_DIR, session_id, "images")
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, f"scene_{scene_index:03d}.png")
    img.save(img_path, "PNG")
    logger.info(f"[Image] Saved: {img_path}")
    return img_path


# ─────────────────────────────────────────────────────────────────────────────
# Audio Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_scene_audio(
    narration: str,
    scene_index: int,
    session_id: str,
    voice: str = "Male",
    language: str = "en",
) -> str:
    """
    Generate TTS audio for a scene using gTTS.
    Returns the path to the saved MP3 file.
    """
    if not GTTS_AVAILABLE:
        raise RuntimeError("gTTS is required for audio generation. Install it with: pip install gtts")

    audio_dir = os.path.join(EXPORTS_DIR, session_id, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, f"scene_{scene_index:03d}.mp3")

    tts = gTTS(text=narration, lang=language, slow=False)
    tts.save(audio_path)
    logger.info(f"[Audio] Saved: {audio_path}")
    return audio_path


# ─────────────────────────────────────────────────────────────────────────────
# Subtitle Generation (Whisper)
# ─────────────────────────────────────────────────────────────────────────────

def generate_subtitles(audio_path: str, scene_index: int, session_id: str) -> str:
    """
    Transcribe audio using OpenAI Whisper and produce an SRT subtitle file.
    Returns the path to the SRT file.
    """
    subtitle_dir = os.path.join(EXPORTS_DIR, session_id, "subtitles")
    os.makedirs(subtitle_dir, exist_ok=True)
    srt_path = os.path.join(subtitle_dir, f"scene_{scene_index:03d}.srt")

    if not WHISPER_AVAILABLE:
        logger.warning("[Subtitles] Whisper not available. Writing empty SRT.")
        with open(srt_path, "w") as f:
            f.write("")
        return srt_path

    model = whisper.load_model("base")
    result = model.transcribe(audio_path)

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result.get("segments", []), start=1):
            start = _format_srt_time(seg["start"])
            end   = _format_srt_time(seg["end"])
            text  = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    logger.info(f"[Subtitles] Saved: {srt_path}")
    return srt_path


def _format_srt_time(seconds: float) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# ─────────────────────────────────────────────────────────────────────────────
# Scene Video Assembly (FFmpeg)
# ─────────────────────────────────────────────────────────────────────────────

def assemble_scene_video(
    image_path: str,
    audio_path: str,
    srt_path: str,
    scene_index: int,
    session_id: str,
    transition: str = "fade",
    burn_subtitles: bool = True,
) -> str:
    """
    Combine image + audio into a scene MP4 using FFmpeg.
    Optionally burns subtitles onto the video.
    Returns path to the scene MP4.
    """
    video_dir = os.path.join(EXPORTS_DIR, session_id, "scenes")
    os.makedirs(video_dir, exist_ok=True)
    output_path = os.path.join(video_dir, f"scene_{scene_index:03d}.mp4")

    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
    ]

    if burn_subtitles and srt_path and os.path.getsize(srt_path) > 0:
        safe_srt = srt_path.replace("\\", "/").replace(":", "\\:")
        cmd += ["-vf", f"subtitles='{safe_srt}':force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'"]

    cmd.append(output_path)

    logger.info(f"[FFmpeg] Assembling scene {scene_index}: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"[FFmpeg] Error on scene {scene_index}:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg failed for scene {scene_index}: {result.stderr[-300:]}")

    logger.info(f"[Scene Video] Saved: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# Final Video Concatenation
# ─────────────────────────────────────────────────────────────────────────────

def concatenate_scenes(scene_paths: List[str], session_id: str, title: str = "output") -> str:
    """
    Concatenate all scene MP4s into a single final video using FFmpeg concat demuxer.
    Returns path to the final MP4.
    """
    concat_list_path = os.path.join(EXPORTS_DIR, session_id, "concat_list.txt")
    final_path = os.path.join(EXPORTS_DIR, session_id, f"{title.replace(' ', '_')}_final.mp4")

    with open(concat_list_path, "w") as f:
        for sp in scene_paths:
            f.write(f"file '{sp}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        final_path,
    ]

    logger.info(f"[FFmpeg] Concatenating {len(scene_paths)} scenes...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"[FFmpeg] Concat error:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg concat failed: {result.stderr[-300:]}")

    logger.info(f"[Final Video] Saved: {final_path}")
    return final_path


# ─────────────────────────────────────────────────────────────────────────────
# Main Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def generate_video(
    script: Dict[str, Any],
    session_id: str = None,
    voice: str = "Male",
    language: str = "en",
    burn_subtitles: bool = True,
    transition: str = "fade",
    progress_callback=None,
) -> Dict[str, Any]:
    """
    Main entry point. Accepts a parsed script dict and produces a final MP4.

    Args:
        script:            Parsed script dict with keys: title, scenes[]
        session_id:        Unique ID for this generation run
        voice:             TTS voice preference (Male/Female — gTTS uses lang)
        language:          TTS language code (default: 'en')
        burn_subtitles:    Whether to burn SRT subtitles onto video
        transition:        Transition style (currently: 'fade')
        progress_callback: Optional callable(step: str, pct: int)

    Returns:
        dict with keys: success, video_path, session_id, scenes_count, errors[]
    """
    if session_id is None:
        session_id = f"session_{int(time.time())}"

    title  = script.get("title", "Databloom Video")
    scenes = script.get("scenes", [])

    if not scenes:
        return {"success": False, "error": "No scenes found in script.", "session_id": session_id}

    errors      = []
    scene_paths = []
    total       = len(scenes)

    def _progress(step: str, pct: int):
        logger
