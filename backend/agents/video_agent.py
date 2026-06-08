"""
Video Agent - Databloom Studio AI
Orchestrates video generation: images, audio, subtitles, and assembly.
"""

import os
import json
import subprocess
import time
from typing import Dict, List, Any

# Output directory
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)


def generate_video(
    script_data: Dict[str, Any],
    voice: str = "Male",
    video_format: str = "Portrait (9:16)",
) -> str:
    """
    Main video generation pipeline.
    Orchestrates all steps from scenes to final MP4.
    
    Args:
        script_data: Script dictionary with scenes
        voice: Voice type for TTS
        video_format: Portrait or Landscape
    
    Returns:
        Path to the generated video file
    """
    scenes = script_data.get("scenes", [])
    if not scenes:
        raise ValueError("No scenes found in script data")
    
    session_id = str(int(time.time()))
    session_dir = os.path.join(EXPORTS_DIR, f"session_{session_id}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Step 1: Generate images for each scene
    image_paths = generate_images(scenes, session_dir)
    
    # Step 2: Generate audio for each scene
    audio_paths = generate_audio(scenes, session_dir, voice)
    
    # Step 3: Generate subtitles
    subtitle_path = generate_subtitles(scenes, session_dir)
    
    # Step 4: Assemble video with FFmpeg
    output_file = os.path.join(session_dir, "final_output.mp4")
    assemble_video(
        image_paths, audio_paths, subtitle_path, output_file, video_format
    )
    
    return output_file


def generate_images(scenes: List[Dict], session_dir: str) -> List[str]:
    """
    Generate images for each scene using Stable Diffusion / Flux.
    
    Currently a stub - integrates with SD WebUI API in production.
    """
    image_paths = []
    for i, scene in enumerate(scenes):
        filename = os.path.join(session_dir, f"scene_{i+1}.jpg")
        visual_prompt = scene.get("visual_prompt", "Abstract background")
        
        # TODO: Call Stable Diffusion API
        # sd_api_call(visual_prompt, filename)
        
        # For now, create a placeholder
        image_paths.append(create_placeholder_image(filename, visual_prompt))
    
    return image_paths


def create_placeholder_image(filename: str, prompt: str) -> str:
    """
    Creates a placeholder image with text overlay using FFmpeg.
    Used when SD is not available.
    """
    # Escape special characters for FFmpeg
    safe_prompt = prompt.replace("'", "").replace("\"", "").replace(":", "")
    safe_prompt = safe_prompt[:50]
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=blue:s=1080x1920",
        "-vf",
        f"drawtext=text='{safe_prompt[:30]}...':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-t", "3",
        filename
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return filename
    except (subprocess.CalledProcessError, FileNotFoundError):
        # FFmpeg not available, return empty path
        return ""


def generate_audio(
    scenes: List[Dict], session_dir: str, voice: str = "Male"
) -> List[str]:
    """
    Generate TTS audio for each scene using Coqui TTS / Piper.
    
    Currently a stub - integrates with TTS engine in production.
    """
    audio_paths = []
    for i, scene in enumerate(scenes):
        filename = os.path.join(session_dir, f"scene_{i+1}.wav")
        text = scene.get("text", "No text available")
        duration = scene.get("duration", 5)
        
        # TODO: Call Coqui TTS or Piper
        # tts_api_call(text, filename, voice)
        
        # For now, create a placeholder audio
        audio_paths.append(create_placeholder_audio(filename, duration))
    
    return audio_paths


def create_placeholder_audio(filename: str, duration: int) -> str:
    """
    Creates a placeholder audio file with FFmpeg.
    Used when TTS engine is not available.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration}",
        filename
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return filename
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def generate_subtitles(scenes: List[Dict], session_dir: str) -> str:
    """
    Generate SRT subtitle file from scenes.
    Can be enhanced with Whisper for transcribed subtitles.
    """
    srt_path = os.path.join(session_dir, "subtitles.srt")
    
    start_time = 0
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, scene in enumerate(scenes):
            text = scene.get("text", "")
            duration = scene.get("duration", 5)
            end_time = start_time + duration
            
            f.write(f"{i+1}\n")
            f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
            f.write(f"{text}\n\n")
            start_time = end_time
    
    return srt_path


def format_time(seconds: float) -> str:
    """
    Format time in SRT format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def assemble_video(
    image_paths: List[str],
    audio_paths: List[str],
    subtitle_path: str,
    output_file: str,
    video_format: str = "Portrait (9:16)",
) -> None:
    """
    Assemble final video using FFmpeg.
    Combines images, audio tracks, and subtitles into one MP4.
    """
    # Set dimensions based on format
    if "9:16" in video_format or "Portrait" in video_format:
        width, height = 1080, 1920
    else:
        width, height = 1920, 1080
    
    # Create a filter script for FFmpeg
    filter_complex_parts = []
    
    for i, (img, audio) in enumerate(zip(image_paths, audio_paths)):
        if not img:
            continue
        duration_str = "3"  # default
        # Try to get duration from audio file
        filter_complex_parts.append(
            f"[{i}:v][{i}:a]concat=n=1:v=1:a=1[out{i}][outa{i}]"
        )
    
    # Simple concatenation approach
    # For each scene, we'll use FFmpeg to create a clip, then concatenate
    
    clips_dir = os.path.join(os.path.dirname(output_file), "clips")
    os.makedirs(clips_dir, exist_ok=True)
    
    clip_list = []
    for i, (img, audio) in enumerate(zip(image_paths, audio_paths)):
        if not img:
            continue
        scene_num = i + 1
        clip_file = os.path.join(clips_dir, f"clip_{scene_num}.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", img,
            "-i", audio,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-vf", f"scale={width}:{height}",
            "-shortest",
            clip_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            clip_list.append(clip_file)
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    if not clip_list:
        # No clips available - create a single black video
        create_final_video(width, height, 30, None, subtitle_path, output_file)
        return
    
    # Concatenate all clips
    concat_file = os.path.join(clips_dir, "concat_list.txt")
    with open(concat_file, "w") as f:
        for clip in clip_list:
            f.write(f"file '{clip}'\n")
    
    # Check if subtitle file exists and is not empty
    has_subtitles = os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0
    has_audio = len(clip_list) > 0
    
    # Create final video with or without subtitles
    create_final_video(
        width, height, 30, concat_file,
        subtitle_path if has_subtitles else None,
        output_file,
        has_audio=has_audio
    )


def create_final_video(
    width: int, height: int, fps: int,
    concat_list: str,
    subtitle_path: str,
    output_file: str,
    has_audio: bool = True,
) -> None:
    """
    Create the final output video.
    """
    subtitle_filter = f"subtitles='{subtitle_path}'" if subtitle_path else ""
    
    if concat_list and os.path.exists(concat_list):
        # Concatenate clips then add subtitles
        temp_file = output_file.replace(".mp4", "_temp.mp4")
        
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            temp_file
        ]
        
        try:
            subprocess.run(concat_cmd, check=True, capture_output=True)
        except:
            return
        
        final_cmd = [
            "ffmpeg", "-y",
            "-i", temp_file,
            "-vf", subtitle_filter if subtitle_path else "scale=1080:1920",
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ]
    else:
        # Create single clip with subtitles
        final_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=navy:s={width}x{height}:r={fps}",
            "-vf", subtitle_filter if subtitle_path else r"drawtext=text='Databloom Studio AI':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-t", "30",
            "-c:v", "libx264",
            output_file
        ]
    
    try:
        subprocess.run(final_cmd, check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # FFmpeg not available
        pass


def cleanup_session(session_dir: str) -> None:
    """
    Clean up temporary files from a session.
    Keeps only the final output.
    """
    import shutil
    
    files_to_keep = ["final_output.mp4"]
    
    for root, dirs, files in os.walk(session_dir):
        for file in files:
            if file not in files_to_keep:
                try:
                    os.remove(os.path.join(root, file))
                except OSError:
                    pass
    
    # Remove empty subdirectories
    for root, dirs, files in os.walk(session_dir, topdown=False):
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass
