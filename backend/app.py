"""
Databloom Studio AI - Main Streamlit Application
A free open-source Text-to-Video AI tool for creators in India.
"""

import streamlit as st
import json
import os
from agents.script_agent import generate_script
from agents.video_agent import generate_video

# Page Configuration
st.set_page_config(
    page_title="Databloom Studio AI",
    page_icon="🎬",
    layout="wide",
)

# Sidebar
st.sidebar.title("🎬 Databloom Studio AI")
st.sidebar.markdown("---")
st.sidebar.markdown("**Open Source Text-to-Video Tool**")
st.sidebar.markdown("Make AI creation accessible to everyone in India.")
st.sidebar.markdown("---")
st.sidebar.markdown("### Pipeline Stages")
st.sidebar.markdown("1. 📝 Script Generation")
st.sidebar.markdown("2. 🖼️ Visual Generation")
st.sidebar.markdown("3. 🎙️ Voice/TTS")
st.sidebar.markdown("4. 🎵 Music & Subtitles")
st.sidebar.markdown("5. 🎞️ Video Assembly")

# Main Title
st.title("🎬 Databloom Studio AI")
st.markdown(
    '## Make AI-powered video creation accessible to *every Indian creator.*'
)
st.markdown(
    "Enter a topic and let our AI pipeline generate a professional video "
    "with script, visuals, voice, and subtitles."
)

# Video Settings
with st.expander("⚙️ Video Settings"):
    col1, col2, col3 = st.columns(3)
    with col1:
        video_style = st.selectbox(
            "Style",
            ["YouTube Short", "Educational", "Animated", "Slideshow", "Documentary"],
        )
    with col2:
        language = st.selectbox(
            "Language", ["English", "Hindi", "Hinglish", "Tamil", "Bengali"]
        )
    with col3:
        duration = st.selectbox("Duration", ["30 sec", "60 sec", "90 sec"])
    with col1:
        voice = st.selectbox("Voice", ["Male", "Female", "Energetic", "Calm"])
    with col2:
        format = st.selectbox("Format", ["Portrait (9:16)", "Landscape (16:9)"])

# Main Input
st.markdown("---")
col1, col2 = st.columns([3, 1])
with col1:
    topic = st.text_area(
        "📝 Enter your video topic or idea:",
        placeholder="e.g., Explain photosynthesis for class 10 students in Hindi",
        height=100,
    )

with col2:
    st.markdown("### Quick Prompts")
    quick_prompts = [
        "What is AI and why it matters?",
        "Explain blockchain in simple terms",
        "How to learn Python in 30 days",
        "Climate change impact on India",
    ]
    for prompt in quick_prompts:
        if st.button(prompt):
            topic = prompt

# Generate Button
st.markdown("---")
col1, col2, col3 = st.columns([4, 1, 4])
with col2:
    generate_btn = st.button(
        "🎞️ Generate Video", type="primary", use_container_width=True
    )

if generate_btn and topic:
    st.markdown("### Processing Pipeline")

    # Step 1: Script Generation
    with st.spinner("🤖 AI Planner - Writing script..."):
        try:
            script_data = generate_script(topic, video_style, language, duration)
            st.json(script_data)
        except Exception as e:
            st.error(f"Script generation failed: {str(e)}")
            script_data = None

    # Step 2: Video Generation
    if script_data:
        with st.spinner("🎬 Video Agent - Generating visuals and audio..."):
            try:
                video_path = generate_video(script_data, voice, format)
                st.success("🎉 Video generated successfully!")
                st.video(video_path)
            except Exception as e:
                st.error(f"Video generation failed: {str(e)}")
                video_path = None

elif generate_btn:
    st.warning("Please enter a topic first!")

# Footer
st.markdown("---")
st.markdown(
    "**Built by [DataBloom AI & Tech](https://databloom.in)** | "
    "Making AI creation accessible to every Indian.")
)
