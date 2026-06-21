---
layout: home

hero:
  name: Cantus
  text: Compose LLM agents like polyphony
  tagline: A teaching-oriented, Colab-first framework for building agent harnesses from two protocols — Skill and Memory.
  actions:
    - theme: brand
      text: Quickstart (Colab)
      link: /quickstart
    - theme: alt
      text: Overview
      link: /overview
    - theme: alt
      text: Interactive manual
      link: /interactive/
      target: _blank
      rel: noopener

features:
  - title: Two protocols, one loop
    details: Skills are callable behaviours; Memory holds state. An Agent runs the read–act–observe loop over them, recording every step in an EventStream.
  - title: Local or cloud models
    details: Run Gemma on Colab, MLX on Apple Silicon, or any of eight providers — OpenAI, Anthropic, Google, Groq, NVIDIA, Ollama, MLX, and a local OpenAI-compatible server.
  - title: Serve and observe
    details: Expose a registry over HTTP with `cantus serve`, connect LINE, Telegram, Discord, or Google Chat, and watch sessions live in the `cantus tui` dashboard.
  - title: Built for the classroom
    details: Designed so students write a skill, swap a provider, and inspect what the agent did — without leaving a notebook.
---
