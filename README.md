# Databloom Studio AI

> Open Source Text-to-Video AI Tool | Make AI creation accessible to everyone in India

## Mission

**"Anyone with an idea should be able to create a professional video without camera, editing skills, or expensive software."**

Databloom Studio AI is a free, open-source **Text -> Video** AI tool designed by [DataBloom AI & Tech](https://databloom.in). It empowers creators, educators, and students across India to generate professional-quality videos from simple text prompts.

---

## How It Works

User enters a topic, and the AI generates everything needed:

| Step | Component | Technology |
|------|-----------|------------|
| 1 | Script | Ollama (Llama/Mistral) |
| 2 | Voice/TTS | Coqui TTS / Piper |
| 3 | Visuals | Stable Diffusion / Flux |
| 4 | Animation | Stable Video Diffusion / AnimateDiff |
| 5 | Subtitles | Whisper |
| 6 | Video Assembly | FFmpeg |

---

## Architecture

```
User Prompt (e.g., "Explain photosynthesis for class 10 in Hindi")
        |
[AI Planner Agent]
        |
    LLM (Ollama)
        |
  Scene JSON Output
        |
[Generation Pipeline]
        |
   Images + Animation + Voice + Music + Captions
        |
     [FFmpeg Assembly]
        |
       Final MP4
```

---

## Project Structure

```
databloom-studio-ai-code/
|-- backend/
|   |-- app.py              # Main Streamlit app
|   |-- agents/
|   |   |-- script_agent.py # Generates scene-by-scene JSON
|   |   +-- video_agent.py  # Orchestrates video generation
|-- frontend/
|-- exports/
|-- requirements.txt
+-- README.md
```

---

## Installation

### Prerequisites
- Python 3.9+
- Ollama installed and running (`ollama run llama3.2`)
- FFmpeg installed on your system

### Setup

```bash
# Clone the repository
git clone https://github.com/Vinay1094/databloom-studio-ai-code.git
cd databloom-studio-ai-code

# Install dependencies
pip install -r requirements.txt

# Make sure Ollama is running
ollama serve

# Run the application
streamlit run backend/app.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-script` | POST | Accepts prompt, returns JSON scene breakdown |
| `/generate-assets` | POST | Generates images via SD + audio via TTS |
| `/assemble-video` | POST | Merges assets into final MP4 |

---

## Features

- AI Script Generation (multi-language support including Hindi/Hinglish)
- Scene-by-scene breakdown with visual prompts
- Image/Video scene rendering
- Auto-subtitle integration with Whisper
- YouTube Shorts style output (MVP focus)
- Educational mode with India-specific examples

---

## Tech Stack

- **Frontend:** Streamlit
- **Backend:** FastAPI
- **LLM:** Ollama (Llama 3.2 / Mistral / Qwen)
- **Image Gen:** Stable Diffusion XL / Flux
- **Video:** Stable Video Diffusion / AnimateDiff
- **TTS:** Coqui TTS / Piper
- **Transcription:** Whisper
- **Assembly:** FFmpeg

---

## Roadmap

- [x] Initial repo setup
- [ ] Script Agent (Ollama integration)
- [ ] Video Agent (image + audio generation)
- [ ] FFmpeg assembly pipeline
- [ ] Hinglish language support
- [ ] YouTube Shorts export optimization
- [ ] Multi-agent system (Research -> Director -> QA)
- [ ] Docker containerization
- [ ] Docker Compose setup
- [ ] Demo deployment on Streamlit Cloud

---

## License

MIT License - feel free to use, modify, and contribute!

---

*Built by [DataBloom AI & Tech](https://databloom.in) | Making AI creation accessible to every Indian.*
