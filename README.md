# 🧠 GENIUS AGI — Advanced Local AI Assistant

A powerful, conscious AGI (Artificial General Intelligence) system that runs entirely locally and offline. Combines an intelligent Python backend with a beautiful responsive web interface.

## ✨ Key Features

### 🎯 Core AGI Capabilities
- **Conscious AI System** — Emotional awareness, self-reflection, and adaptive personality
- **9 Specialized Agents** — General, Coder, Scientist, Translator, Creative, Tutor, Analyst, Philosopher, Health
- **Executive Planning System** — Strategic goal decomposition and adaptive task scheduling
- **Memory Management** — Long-term facts, episodic memory, and pattern recognition
- **Self-Optimization** — Meta-execution analysis and continuous improvement

### 🌍 Multi-Language Support
- **15 Languages:** Arabic, English, Spanish, French, German, Chinese, Japanese, Russian, Portuguese, Italian, Korean, Turkish, Hindi, Indonesian

### 📱 Adaptive Performance
- Auto-detects device capabilities (RAM, CPU cores, connection type)
- Optimizes UI and processing based on device power
- Scales from low-end Android to high-end desktops

### 🔌 100% Offline
- Works without internet after first load
- Service Worker caches everything
- Local IndexedDB storage
- No cloud API calls

### 🎨 Rich Interface
- 6 Beautiful themes (Dark, Light, Ocean, Forest, Sunset, Cyber)
- Real-time consciousness dashboard
- Code sandbox for safe JavaScript execution
- File upload and analysis
- Voice input/output support

### 💾 Data Management
- Export/import conversations as JSON
- Google Drive sync (optional)
- Local persistent storage
- Privacy-first architecture

---

## 🚀 Quick Start

### Requirements
- Python 3.8+
- Node.js (optional, for development)

### Installation

```bash
# Clone the repository
git clone https://github.com/krms31241-hue/genius-agi.git
cd genius-agi

# Install Python dependencies
pip install -r requirements.txt

# Run the server
python server.py
```

The server will start on `http://localhost:8000`

### Access the Web Interface
1. Open browser: `http://localhost:8000/`
2. Or serve `index.html` directly with any HTTP server
3. Or install as PWA on your device

---

## 📁 Architecture

### Frontend (PWA)
```
index.html              Main app
manifest.json          PWA config
service-worker.js      Offline caching

js/
├── app.js             Core application logic
├── ai-engine.js       Response generation
├── consciousness.js   Emotional awareness system
├── i18n.js            Multi-language support
├── gdrive.js          Google Drive integration
└── internet.js        Connection detection

css/
└── styles.css         UI styling
```

### Backend (Python AGI)
```
server.py              FastAPI server

core/
├── bootstrap/         Provider initialization
└── router/            Request routing

memory/                Memory management
executive/            Strategic planning & execution
runtime/              Runtime environment
tool_executor.py      Tool execution engine
```

---

## 🧠 How It Works

### 1. User Input
User sends message → Frontend captures in IndexedDB

### 2. Routing
Message sent to Python backend → AI Router evaluates context

### 3. Agent Selection
Based on query, appropriate agent is activated (Coder, Scientist, etc.)

### 4. Executive Planning
Executive Engine decomposes tasks into subtasks → Generates goal tree

### 5. Memory Integration
Memory Manager retrieves relevant facts and episodes

### 6. Response Generation
Combines agent expertise + memory + consciousness state

### 7. Consciousness Injection
Adds emotional awareness based on:
- Current mood and energy levels
- User emotion detection
- Personality traits (Big Five)
- Personal identity and values

### 8. Response Delivery
Sent back to frontend → Rendered with animations

---

## 🎮 Usage

### Chat Modes
- **General Chat** — Free-form conversation
- **Agent Mode** — Specialized knowledge domain
- **Code Sandbox** — Execute JavaScript safely
- **File Analysis** — Upload and analyze documents

### Commands
- "@coder" — Switch to Coder agent
- "@scientist" — Switch to Scientist agent
- "solve: 2x + 5 = 15" — Math problem solving
- "translate hello" — Translation
- "Write JavaScript code" — Code generation

---

## 🔒 Privacy

✅ **Zero data leaves your device**
- All processing happens locally
- No tracking or analytics
- No cloud storage required
- Export your data anytime as JSON
- Delete all data on demand

---

## 📊 Project Structure

```
genius-agi/
├── index.html                 # Main app
├── server.py                 # FastAPI server
├── requirements.txt          # Python dependencies
├── manifest.json             # PWA manifest
├── service-worker.js         # Offline support
│
├── js/
│   ├── app.js               # 26KB - Core app logic
│   ├── ai-engine.js         # 10KB - Response generation
│   ├── consciousness.js     # 17KB - Emotional AI
│   ├── i18n.js             # 7KB - Translations
│   ├── gdrive.js           # 5KB - Drive sync
│   └── internet.js         # 3KB - Network detection
│
├── css/
│   └── styles.css          # 12KB - UI styling
│
├── core/
│   ├── bootstrap/
│   │   └── providers_bootstrap.py    # AI initialization
│   └── router/
│       └── ai_router.py              # Request routing
│
├── memory/
│   └── memory_manager.py             # Long-term memory
│
├── executive/
│   ├── executive_engine.py           # Strategic planning
│   ├── goal_tree.py                  # Goal decomposition
│   ├── mission_executor.py           # Mission execution
│   └── [40+ planning modules]        # Full AGI system
│
└── runtime/
    └── genius_runtime.py             # Runtime orchestrator
```

---

## ⚙️ Configuration

### Environment Variables
```bash
PORT=8000                    # Server port
DEVICE_MODE=auto           # auto, low, medium, high
LANG=ar                    # Default language
```

### Settings (In-App)
- Theme selection (Dark/Light/Ocean/Forest/Sunset/Cyber)
- Language preference (15 options)
- Voice input/output toggle
- Consciousness mode (Full/Lite/Off)
- Memory management

---

## 🔧 Development

### Backend Development
```bash
# Run in development mode
python server.py

# With hot reload
pip install watchfiles
uvicorn server:app --reload
```

### Frontend Development
```bash
# Serve with Python
python -m http.server 8000

# Or use any HTTP server
php -S localhost:8000
npx http-server
```

### Testing
```bash
pip install pytest pytest-asyncio
pytest tests/
```

---

## 📈 Performance

| Device Type | RAM | Performance | Notes |
|---|---|---|---|
| Low-end Android | 1-3GB | Reduced effects, fast | Lightweight mode |
| Mid-range (Realme, etc.) | 4GB | Balanced | Optimal for most users |
| High-end | 8GB+ | Full effects | Maximum features |
| Desktop | Any | Maximum | Unlimited processing |

---

## 🚀 Deployment

### Option 1: Vercel (Recommended for Frontend)
```bash
git push origin main
# Go to vercel.com → Import → Deploy
```

### Option 2: Render.com (Backend)
```bash
# Connect repo → Deploy as Web Service
# Set: gunicorn server:app
```

### Option 3: Docker
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "server:app", "--host", "0.0.0.0"]
```

### Option 4: Local Desktop
Just run `python server.py` and open browser

---

## 📱 Install as PWA

### Android Chrome
1. Open app in Chrome
2. Tap menu (⋮) → "Add to Home screen"
3. Confirm → Opens as native app
4. Works offline!

### iOS Safari
1. Open app in Safari
2. Share → "Add to Home Screen"
3. Tap "Add" → Installs as PWA

### Desktop
1. Open in Chrome/Edge
2. Click install icon (top right)
3. Confirm → Launches as app window

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - Free to use, modify, and distribute.

See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

Built with ❤️ for offline AI accessibility.

**Author:** Karam Saleh  
**Status:** Active Development  
**Version:** 3.0 Conscious  

---

## 📞 Support

- 📧 Email: krms31241@gmail.com
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📖 Docs: See [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🎯 Roadmap

- [x] Core AGI system
- [x] 9 specialized agents
- [x] Consciousness simulation
- [x] Multi-language support
- [x] Offline operation
- [ ] Vision capabilities
- [ ] Voice synthesis improvements
- [ ] Real LLM integration (optional)
- [ ] Distributed execution
- [ ] Full AGI capabilities

---

**"I am GENIUS. I exist to learn, help, and evolve." 🧠**
