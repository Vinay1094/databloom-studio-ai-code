"""
Script Agent - Databloom Studio AI
Generates scene-by-scene video scripts using Ollama LLM.
Produces structured JSON with text, visual prompts, and timings.
"""

import json
import requests
from typing import Dict, List, Any

# Ollama API endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"  # or mistral, qwen, etc.

SYSTEM_PROMPT = """You are a video script generator for educational content.
Your task is to create a scene-by-scene breakdown for a short video.
Each scene should have:
- text: what the narrator says
- visual_prompt: description for image/video generation
- duration: how long the scene lasts (in seconds)

Respond ONLY with a valid JSON array of scenes.
Include an intro, body (2-4 scenes), and CTA.
Language: Respond in the language requested by the user.
Style: {style}, Duration: {duration}"""


def generate_script(
    topic: str, style: str = "Educational", language: str = "English", duration: str = "60 sec"
) -> Dict[str, Any]:
    """
    Generate a video script using Ollama LLM.
    
    Args:
        topic: The video topic/idea
        style: Video style (YouTube Short, Educational, etc.)
        language: Output language (English, Hindi, Hinglish, etc.)
        duration: Target duration (30 sec, 60 sec, 90 sec)
    
    Returns:
        Dictionary with script data including scenes array
    """
    prompt = SYSTEM_PROMPT.format(style=style, duration=duration)
    prompt += f"\n\nGenerate a video script about: {topic}"
    prompt += f"\nLanguage: {language}"
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        raw_output = response.json().get("response", "")
        
        # Extract JSON from response
        script_data = parse_script_json(raw_output)
        
        return {
            "topic": topic,
            "style": style,
            "language": language,
            "duration": duration,
            "script": raw_output,
            "scenes": script_data
        }
    except requests.exceptions.ConnectionError:
        # Ollama not running - return mock data
        return generate_mock_script(topic, style, language, duration)
    except Exception as e:
        return generate_mock_script(topic, style, language, duration)


def parse_script_json(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parse JSON from LLM response.
    Handles cases where LLM adds extra text before/after JSON.
    """
    try:
        # Try direct parse first
        return json.loads(raw_output)
    except json.JSONDecodeError:
        # Extract JSON block
        import re
        json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return []


def generate_mock_script(
    topic: str, style: str, language: str, duration: str
) -> List[Dict[str, Any]]:
    """
    Generates a mock script when Ollama is not available.
    Useful for development and testing.
    """
    duration_sec = int(duration.split()[0])
    scenes = [
        {
            "scene": 1,
            "text": f"Hook: Did you know {topic} is transforming the world?",
            "visual_prompt": "Cinematic shot of technology and innovation, digital particles floating",
            "duration": 5
        },
        {
            "scene": 2,
            "text": f"Point 1: Here's what {topic} really means in simple terms...",
            "visual_prompt": "Clean infographic style, whiteboard animation look",
            "duration": 10
        },
        {
            "scene": 3,
            "text": f"Point 2: Real-world examples of {topic} in action...",
            "visual_prompt": "Dynamic montage of real-world applications",
            "duration": 10
        },
        {
            "scene": 4,
            "text": f"Point 3: Why {topic} matters for your future...",
            "visual_prompt": "Inspiring shot of students or professionals succeeding",
            "duration": 10
        },
        {
            "scene": 5,
            "text": "CTA: Follow for more AI-powered learning!",
            "visual_prompt": "Bold text on gradient background with subscribe button",
            "duration": 5
        }
    ]
    return scenes


def save_script(script_data: Dict[str, Any], filename: str = "script.json") -> str:
    """
    Save script to JSON file.
    
    Args:
        script_data: The script data dictionary
        filename: Output filename
    
    Returns:
        Path to saved file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)
    return filename
