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

# -- Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# -- Output directory
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

# -- Optional dependency guards
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


# =============================================================================
# Image Generation
# =============================================================================

def generate_scene_image(
    scene: Dict[str, Any],
    scene_index: int,
    session_id: str,
    width: int = 1280,
    height: int = 720,
) -> str:
    """Generate a styled slide image for a scene using Pillow."""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required. Install: pip install pillow")

    title = scene.get("title", f"Scene {scene_index + 1}")
    narration = scene.get("narration", "")
    visual_style = scene.get("visual_style", "default")

    themes = {
        "intro":       {"bg": (15, 23, 42),  "accent": (99, 102, 241), "text": (255, 255, 255)},
        "explanation": {"bg": (17, 24, 39),  "accent": (16, 185, 129), "text": (243, 244, 246)},
        "highlight":   {"bg": (30, 27, 75),  "accent": (245, 158, 11), "text": (255, 255, 255)},
        "conclusion":  {"bg": (7, 36, 55),   "accent": (14, 165, 233), "text": (226, 232, 240)},
        "default":     {"bg": (10, 10, 30),  "accent": (139, 92, 246), "text": (255, 255, 255)},
    }
    theme = themes.get(visual_style, themes["default"])
    bg_color     = theme["bg"]
    accent_color = theme["accent"]
    text_color   = theme["text"]

    img  = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Accent bars
    draw.rectangle([0, 0, width, 8], fill=accent_color)
    draw.rectangle([0, height - 8, width, height], fill=accent_color)

    # Load fonts with cross-platform fallback
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font_title = font_body = font_badge = ImageFont.load_default()
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font_title = ImageFont.truetype(fp, 52)
                font_body  = ImageFont.truetype(fp, 28)
                font_badge = ImageFont.truetype(fp, 20)
                break
            except Exception:
                pass

    # Scene badge
    draw.rounded_rectangle([50, 40, 210, 82], radius=12, fill=accent_color)
    draw.text((62, 52), f"SCENE {scene_index + 1}", fill=(255, 255, 255), font=font_badge)

    # Title
    draw.text((60, 110), title, fill=text_color, font=font_title)
    draw.rectangle([60, 180, 420, 184], fill=accent_color)

    # Narration body
    wrapped = textwrap.wrap(narration, width=68)
    body_y = 200
    for line in wrapped[:6]:
        draw.text((60, body_y), line, fill=text_color, font=font_body)
        body_y += 44

    # Watermark
    draw.text((width - 270, height - 48), "Databloom Studio AI", fill=accent_color, font=font_badge)

    img_dir  = os.path.join(EXPORTS_DIR, session_id, "images")
    os.makedirs(img_dir, exist_ok=True)
    img_path = os.path.join(img_dir, f"scene_{scene_index:03d}.png")
    img.save(img_path, "PNG")
    logger.info(f"[Image] Saved: {img_path}")
    return img_path


# =============================================================================
# Audio Generation
# =============================================================================

def generate_scene_audio(
    narration: str,
    scene_index: int,
    session_id: str,
    voice: str = "Male",
    language: str = "en",
) -> str:
    """Generate TTS audio for a scene using gTTS."""
    if not GTTS_AVAILABLE:
        raise RuntimeError("gTTS is required. Install: pip install gtts")

    audio_dir  = os.path.join(EXPORTS_DIR, session_id, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, f"scene_{scene_index:03d}.mp3")

    try:
        tts = gTTS(text=narration, lang=language, slow=False)
        tts.save(audio_path)
    except Exception as e:
        logger.warning(f"[Audio] gTTS failed ({e}). Generating silent audio fallback.")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "aevalsrc=0:duration=5",
            "-c:a", "libmp3lame",
            audio_path,
        ]
        subprocess.run(cmd, capture_output=True)

    logger.info(f"[Audio] Saved: {audio_path}")
    return audio_path


# =============================================================================
# Subtitle Generation
# =============================================================================

def _format_srt_time(seconds: float) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


_whisper_model = None

def generate_subtitles(audio_path: str, scene_index: int, session_id: str) -> str:
    """Transcribe audio using Whisper and produce an SRT file."""
    global _whisper_model

    subtitle_dir = os.path.join(EXPORTS_DIR, session_id, "subtitles")
    os.makedirs(subtitle_dir, exist_ok=True)
    srt_path = os.path.join(subtitle_dir, f"scene_{scene_index:03d}.srt")

    if not WHISPER_AVAILABLE:
        logger.warning("[Subtitles] Whisper not available. Writing empty SRT.")
        with open(srt_path, "w") as f:
            f.write("")
        return srt_path

    if _whisper_model is None:
        logger.info("[Subtitles] Loading Whisper base model...")
        _whisper_model = whisper.load_model("base")

    result = _whisper_model.transcribe(audio_path)

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result.get("segments", []), start=1):
            start = _format_srt_time(seg["start"])
            end   = _format_srt_time(seg["end"])
            text  = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    logger.info(f"[Subtitles] Saved: {srt_path}")
    return srt_path


# =============================================================================
# Scene Video Assembly
# =============================================================================

def assemble_scene_video(
    image_path: str,
    audio_path: str,
    srt_path: str,
    scene_index: int,
    session_id: str,
    transition: str = "fade",
    burn_subtitles: bool = True,
) -> str:
    """Combine image + audio into a scene MP4 using FFmpeg."""
    video_dir   = os.path.join(EXPORTS_DIR, session_id, "scenes")
    os.makedirs(video_dir, exist_ok=True)
    output_path = os.path.join(video_dir, f"scene_{scene_index:03d}.mp4")

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

    has_subs = burn_subtitles and srt_path and os.path.exists(srt_path) and os.path.getsize(srt_path) > 0
    if has_subs:
        # Cross-platform safe path escaping for FFmpeg subtitles filter
        safe_srt = srt_path.replace("\\", "/")
        if ":" in safe_srt:
            # Windows drive letter e.g. C:/... -> C\\:/...
            safe_srt = safe_srt.replace(":", "\\:")
        cmd += [
            "-vf",
            f"subtitles='{safe_srt}':force_style='FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Bold=1'",
        ]

    cmd.append(output_path)

    logger.info(f"[FFmpeg] Assembling scene {scene_index}...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"[FFmpeg] Error scene {scene_index}:\n{result.stderr[-400:]}")
        raise RuntimeError(f"FFmpeg failed scene {scene_index}: {result.stderr[-300:]}")

    logger.info(f"[Scene] Saved: {output_path}")
    return output_path


# =============================================================================
# Final Concatenation
# =============================================================================

def concatenate_scenes(scene_paths: List[str], session_id: str, title: str = "output") -> str:
    """Join all scene MP4s into one final video."""
    concat_list = os.path.join(EXPORTS_DIR, session_id, "concat_list.txt")
    safe_title  = title.replace(" ", "_").replace("/", "_")
    final_path  = os.path.join(EXPORTS_DIR, session_id, f"{safe_title}_final.mp4")

    with open(concat_list, "w") as f:
        for sp in scene_paths:
            f.write(f"file '{sp}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        final_path,
    ]

    logger.info(f"[FFmpeg] Concatenating {len(scene_paths)} scenes...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"[FFmpeg] Concat error:\n{result.stderr[-400:]}")
        raise RuntimeError(f"FFmpeg concat failed: {result.stderr[-300:]}")

    logger.info(f"[Final] Video saved: {final_path}")
    return final_path


# =============================================================================
# MAIN PIPELINE ENTRY POINT
# =============================================================================

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
        session_id:        Unique run ID (auto-generated if None)
        voice:             TTS voice (Male/Female - gTTS uses lang)
        language:          BCP-47 language code (default: 'en')
        burn_subtitles:    Burn SRT subtitles onto video frames
        transition:        Transition style ('fade' supported)
        progress_callback: Optional callable(step: str, pct: int)

    Returns:
        dict: {success, video_path, session_id, scenes_count, errors}
    """
    if session_id is None:
        session_id = f"session_{int(time.time())}"

    title  = script.get("title", "Databloom Video")
    scenes = script.get("scenes", [])

    if not scenes:
        return {
            "success": False,
            "error": "No scenes found in script.",
            "session_id": session_id,
            "errors": [],
        }

    errors      = []
    scene_paths = []
    total       = len(scenes)

    def _progress(step: str, pct: int):
        logger.info(f"[Progress] {pct}% - {step}")
        if progress_callback:
            try:
                progress_callback(step, pct)
            except Exception:
                pass

    logger.info(f"[Pipeline] Starting: '{title}' | {total} scenes | session: {session_id}")

    for i, scene in enumerate(scenes):
        scene_label = scene.get("title", f"Scene {i+1}")
        base_pct    = int((i / total) * 90)

        try:
            # Step 1: Generate slide image
            _progress(f"Generating image: {scene_label}", base_pct + 0)
            img_path = generate_scene_image(scene, i, session_id)

            # Step 2: Generate TTS audio
            narration = scene.get("narration", scene_label)
            _progress(f"Generating audio: {scene_label}", base_pct + 10)
            audio_path = generate_scene_audio(narration, i, session_id, voice, language)

            # Step 3: Generate subtitles
            _progress(f"Generating subtitles: {scene_label}", base_pct + 20)
            srt_path = generate_subtitles(audio_path, i, session_id)

            # Step 4: Assemble scene video
            _progress(f"Assembling scene: {scene_label}", base_pct + 25)
            scene_mp4 = assemble_scene_video(
                img_path, audio_path, srt_path, i, session_id, transition, burn_subtitles
            )
            scene_paths.append(scene_mp4)
            logger.info(f"[Pipeline] Scene {i+1}/{total} complete.")

        except Exception as e:
            logger.error(f"[Pipeline] Scene {i} ('{scene_label}') failed: {e}")
            errors.append({"scene": i, "title": scene_label, "error": str(e)})

    if not scene_paths:
        return {
            "success": False,
            "error": "All scenes failed to generate.",
            "session_id": session_id,
            "errors": errors,
        }

    # Step 5: Concatenate all scenes into final video
    _progress("Concatenating final video...", 92)
    try:
        final_video = concatenate_scenes(scene_paths, session_id, title)
    except Exception as e:
        logger.error(f"[Pipeline] Concat failed: {e}")
        return {
            "success": False,
            "error": f"Final concatenation failed: {e}",
            "session_id": session_id,
            "errors": errors,
        }

    _progress("Done!", 100)
    logger.info(f"[Pipeline] Complete! Final video: {final_video}")

    return {
        "success": True,
        "video_path": final_video,
        "session_id": session_id,
        "scenes_count": len(scene_paths),
        "errors": errors,
    }
