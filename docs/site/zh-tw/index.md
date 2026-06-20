---
layout: home

hero:
  name: Cantus
  text: 像複音音樂一樣組合 LLM agent
  tagline: 教學導向、Colab 優先的框架，用 Skill 與 Memory 兩個 protocol 組出 agent harness。
  actions:
    - theme: brand
      text: 快速上手（Colab）
      link: /zh-tw/quickstart
    - theme: alt
      text: 總覽
      link: /zh-tw/overview
    - theme: alt
      text: 互動式手冊
      link: /interactive/

features:
  - title: 兩個 protocol、一個迴圈
    details: Skill 是可呼叫的行為，Memory 持有狀態。Agent 在它們之上跑「讀取—行動—觀察」迴圈，每一步都記進 EventStream。
  - title: 本機或雲端模型
    details: 在 Colab 跑 Gemma、在 Apple Silicon 跑 MLX，或接八個 provider——OpenAI、Anthropic、Google、Groq、NVIDIA、Ollama、MLX、本機 OpenAI 相容伺服器。
  - title: 服務化與觀測
    details: 用 cantus serve 把 registry 開成 HTTP，接上 LINE、Telegram、Discord 或 Google Chat，再用 cantus tui 儀表板即時看 session。
  - title: 為課堂而生
    details: 設計成讓學生寫一個 skill、換一個 provider、檢視 agent 做了什麼——全程不用離開 notebook。
---
