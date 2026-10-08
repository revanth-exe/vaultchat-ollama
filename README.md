# 🦙 LLM Chatbot (Ollama-Powered)

> **A privacy-first local conversational assistant featuring sliding-window context memory management, real-time token streaming, transcript persistence, and an interactive slash-command shell.**

---

## 📌 Architecture Overview

When deploying local conversational agents, two critical engineering challenges arise:
1. **Context Window Degradation**: Unbounded conversation history eventually exceeds the context window, causing OOM crashes or high memory latency.
2. **Interactive User Experience**: Waiting for full generation on local hardware creates poor UX without streaming.

This project implements a lightweight client architecture:

```
[User Terminal Input]
          │
          ├──── Is Slash Command? ───> [/clear, /save, /model, /system]
          │
          ▼
 [Sliding Window Memory Buffer]
 Preserves: [System Persona Prompt] + [Last N Conversation Turns]
          │
          ▼
 [HTTP Streaming Request to Ollama Runtime] (POST /api/chat, stream=True)
          │
          ▼
 [Real-Time Token Stream to Terminal Console]
          │
          ▼
 [Session JSON Persistence] (chat_transcripts/)
```

---

## ✨ Key Features

- **Sliding-Window Memory Manager**: Caps context size to the last $N$ turns (configurable via `.env`), preserving the system prompt while dropping stale turns to maintain low latency on local hardware.
- **True Token Streaming**: Parses SSE JSON streams from Ollama for immediate sub-100ms response feedback.
- **Dynamic Slash-Command Shell**:
  - `/clear`: Flush memory buffer.
  - `/model <name>`: Switch models on the fly (e.g. `llama3.2`, `mistral`, `deepseek-r1`).
  - `/system <prompt>`: Dynamically adjust agent behavior or tone.
  - `/save <name>`: Export session history to JSON in `chat_transcripts/`.
- **Zero Cloud Leakage**: Runs 100% locally with zero external API calls or third-party tracking.

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Runtime**: Ollama (`http://localhost:11434`)
- **HTTP Client**: `requests` (streaming chunks)
- **Terminal Styling**: `rich`
- **Environment**: `python-dotenv`

---

## 🚀 Quickstart

### 1. Prerequisites (Install Ollama)
Download Ollama from [ollama.com](https://ollama.com) and pull your model:
```bash
ollama run llama3.2
```

### 2. Installation
```bash
git clone https://github.com/<your-username>/llm-chatbot-ollama.git
cd llm-chatbot-ollama
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run
```bash
python app.py
```

---

## 🎯 Interview Cheat-Sheet: How to Explain This Project

### 1. The Elevator Pitch
> *"I built a local, privacy-first conversational assistant running on top of Ollama. Rather than building a naive chat loop, I implemented production memory management: a sliding-window buffer that guarantees context bounds while preserving the core system prompt, real-time chunk streaming over HTTP, and a shell command processor allowing dynamic model switching, runtime persona updates, and JSON transcript persistence."*

### 2. Common Interview Questions & Answers

#### Q: How does your memory management work under the hood?
- **Answer**: *"An LLM conversation grows linearly with every user and assistant turn. Without memory pruning, you quickly blow past the model's KV cache and context limits. In `ChatSession`, I maintain full history for persistence, but when constructing the payload for Ollama, I slice `history[-(MAX_HISTORY_TURNS * 2):]` and prepend the immutable `system_prompt`. This keeps inference latency constant regardless of conversation length."*

#### Q: What are the trade-offs of local LLMs vs Cloud APIs like OpenAI or Groq?
- **Answer**: *"Local LLMs provide complete privacy, zero per-token cost, and work offline, making them essential for healthcare, finance, or air-gapped internal tools. The trade-off is hardware dependency (VRAM and compute limits) and slightly lower reasoning capacity compared to 70B+ or 400B parameter cloud models. In production, I often use a hybrid router: simple tasks run locally on 3B/8B models, while complex multi-step reasoning routes to larger cloud models."*
