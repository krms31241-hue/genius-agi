# 🧠 GENIUS AGI — Local AI Assistant PWA

A powerful, adaptive AI assistant that runs entirely in your browser. Works offline on any device — from low-end Android phones to high-end desktops.

## ✨ Features

- **🌍 15 Languages** — Full interface support for Arabic, English, Spanish, French, German, Chinese, Japanese, Russian, Portuguese, Italian, Korean, Turkish, Hindi, Indonesian, and more
- **📱 Adaptive Performance** — Automatically detects your device specs (RAM, CPU cores) and adjusts visual effects and processing accordingly
- **🔌 100% Offline** — Works without internet after first load. Service Worker caches everything
- **🧩 9 Specialized Agents** — General, Coder, Scientist, Translator, Creative, Tutor, Analyst, Philosopher, Health
- **💻 Code Sandbox** — Run JavaScript code safely in your browser
- **📎 File Upload** — Upload TXT, PDF, DOC, MD files for local RAG-style analysis
- **🎤 Voice Input** — Speech-to-text support (browser dependent)
- **🔊 Voice Output** — Text-to-speech for responses
- **🧠 Adaptive Memory** — Learns from your interactions, remembers facts and preferences
- **📊 Math Solver** — Solves equations, arithmetic, and quadratic formulas with step-by-step explanations
- **🎨 6 Themes** — Dark, Light, Ocean, Forest, Sunset, Cyber
- **💾 Persistent Storage** — All data stored locally via IndexedDB
- **📤 Export/Import** — Backup and restore all your data as JSON
- **⚡ PWA** — Install as a native app on Android, iOS, and desktop

## 🚀 Deployment

### Option 1: Vercel (Recommended)
1. Push this folder to a GitHub repository
2. Go to [vercel.com](https://vercel.com) and import the repo
3. Deploy — you'll get a URL like `https://your-project.vercel.app`

### Option 2: Netlify
1. Go to [app.netlify.com/drop](https://app.netlify.com/drop)
2. Drag and drop this folder
3. Get an instant live URL

### Option 3: GitHub Pages
1. Push to GitHub
2. Go to Settings → Pages
3. Select "Deploy from a branch" → main → / (root)

### Option 4: Local (No Server)
1. Copy all files to your phone
2. Open `index.html` in Chrome
3. Tap ⋮ → "Add to Home Screen"

## 📱 Install on Android (Realme Note 50 & Others)

1. Open the deployed URL in **Chrome**
2. Tap the menu (⋮) → **"Add to Home screen"**
3. Confirm — GENIUS will appear as a native app icon
4. Open it — works completely offline!

## 📁 File Structure

```
genius-agi-pwa/
├── index.html          # Main app (HTML + CSS + JS)
├── manifest.json       # PWA manifest
├── service-worker.js   # Offline caching
├── offline.html        # Offline fallback page
└── assets/
    └── icons/          # App icons (72px - 512px)
```

## ⚙️ Device Compatibility

| Device Type | RAM | Performance |
|-------------|-----|-------------|
| Low-end Android | 1-3GB | Reduced particles, faster responses |
| Mid-range (Realme Note 50) | 4GB | Balanced mode |
| High-end | 8GB+ | Full effects, richer animations |
| iPhone/iPad | Any | Optimized for Safari |
| Desktop | Any | Maximum visual effects |

## 🔒 Privacy

- **Zero data leaves your device**
- No cloud API calls
- No tracking or analytics
- All memory stored in browser IndexedDB
- Export your data anytime as JSON

## 🛠️ Tech Stack

- Vanilla JavaScript (no frameworks)
- HTML5 Canvas for particles
- IndexedDB for persistent storage
- Web Speech API for voice
- Service Workers for offline support
- CSS Grid/Flexbox for responsive layout

## 📝 License

MIT — Free to use, modify, and distribute.

---

**Built with ❤️ for offline AI accessibility.**
