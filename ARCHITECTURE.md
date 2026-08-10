# Architecture Overview

## System Design

GENIUS AGI is a hybrid system combining:
- **Frontend:** Progressive Web App (PWA) - Vanilla JavaScript
- **Backend:** Async Python with FastAPI
- **Connection:** HTTP REST API + WebSocket (optional)

## Component Layers

### 1. Presentation Layer (Browser)
```
HTML/CSS/JS (PWA)
   ↓
IndexedDB (Local Storage)
   ↓
Service Worker (Offline Cache)
```

### 2. API Layer (Server)
```
FastAPI Server (Port 8000)
   ↓
/chat → ChatRequest → ChatResponse
/agents → List available agents
/status → System status
/health → Health check
```

### 3. AGI Core (Runtime)
```
GeniusRuntime
   ├── ProvidersBootstrap (Initialize AI)
   ├── AIRouter (Route requests)
   ├── MemoryManager (Store/retrieve)
   ├── ResourceManager (Optimize)
   └── ExecutiveEngine (Planning)
```

### 4. Executive System
```
ExecutiveEngine
   ├── GoalGenerator (Create goals)
   ├── GoalPriorityEngine (Rank)
   ├── GoalDecomposer (Break down)
   ├── Planner (Create plans)
   ├── Scheduler (Order tasks)
   ├── ExecutionMonitor (Track)
   └── MetaExecutive (Analyze)
```

### 5. Memory System
```
MemoryManager
   ├── WorkingMemory (Short-term)
   ├── Facts (Long-term)
   ├── Episodes (Interactions)
   └── Patterns (Recognition)
```

## Data Flow

### Chat Processing Pipeline
```
User Input (Browser)
    ↓
[IndexedDB Save]
    ↓
HTTP POST /chat
    ↓
[Server: FastAPI]
    ↓
GeniusRuntime.run()
    ↓
MemoryManager.search_facts()
    ↓
AIRouter.generate()
    ↓
Provider.generate()
    ↓
[Response]
    ↓
HTTP Response
    ↓
[Browser: Format & Render]
    ↓
Consciousness.inject()
    ↓
Display to User
    ↓
[Save to IndexedDB]
```

## Key Design Patterns

### 1. Agent Pattern
Each agent specializes in a domain:
- Coder: Code generation and review
- Scientist: Research and analysis
- Translator: Language translation
- etc.

### 2. Memory Pattern
Multiple memory types:
- Short-term: Current context
- Long-term: Accumulated facts
- Episodic: Interaction history
- Pattern: Recognized behaviors

### 3. Executive Pattern
Hierarchical goal management:
- Missions (High-level)
- Goals (Medium-level)
- Tasks (Low-level)

### 4. Consciousness Pattern
Artificial emotional awareness:
- Mood tracking
- Energy management
- Personality evolution
- Self-reflection

## File Organization

### Frontend Structure
```
js/
├── app.js                   # Main app initialization
├── ai-engine.js            # Response generation
├── consciousness.js        # Emotional system
├── i18n.js                 # Internationalization
├── gdrive.js               # Cloud integration
└── internet.js             # Network detection
```

### Backend Structure
```
core/
├── bootstrap/              # Initialization
│   └── providers_bootstrap.py
└── router/                 # Request routing
    └── ai_router.py

memory/
└── memory_manager.py       # Memory operations

executive/
├── executive_engine.py     # Main engine
├── goal_*.py              # Goal management (9 files)
├── mission_*.py           # Mission management (3 files)
└── [other modules]        # Support systems (20+ files)

runtime/
└── genius_runtime.py      # Runtime coordinator
```

## Scalability Considerations

### Frontend
- Adaptive rendering based on device capabilities
- Memory pooling for large conversations
- Lazy loading of UI components
- Service Worker caching strategy

### Backend
- Async/await for concurrent requests
- Connection pooling for database
- Rate limiting per IP
- Load balancing support

## Security

- No external API calls (offline-first)
- Input validation on all endpoints
- CORS configured for safety
- Local storage encryption ready
- No credentials transmitted

## Performance Optimizations

1. **Frontend**
   - Minified CSS/JS
   - Particle effects scale with device
   - IndexedDB batch operations
   - Service Worker caching

2. **Backend**
   - Async I/O with asyncio
   - Memory caching
   - Lazy loading of modules
   - Response compression

## Monitoring & Logging

```python
# All components log via Python logging
import logging
logger = logging.getLogger(__name__)

# Frontend logs to browser console
console.log(), console.error()
```

## Error Handling

### Frontend
- Try-catch blocks in critical sections
- Graceful fallbacks for missing features
- User-friendly error messages

### Backend
- HTTP exception handling
- Async exception propagation
- Detailed error logging
- Health check endpoints

## Testing Strategy

```bash
# Backend tests
pytest tests/

# Frontend testing (via browser console)
# Manual testing of all features
# E2E testing with Selenium (optional)
```

## Deployment Architecture

### Production Setup
```
┌─────────────┐
│   Browser   │
│   (PWA)     │
└──────┬──────┘
       │ HTTP
┌──────▼──────────┐
│  Load Balancer  │
└──────┬──────────┘
       │
┌──────▼──────────┐
│  FastAPI Server │ (Multiple instances)
│  (Port 8000)    │
└──────┬──────────┘
       │
┌──────▼──────────┐
│  Shared Storage │
│  (Optional)     │
└─────────────────┘
```

### Local Setup
```
┌─────────────┐
│   Browser   │
│ (localhost) │
└──────┬──────┘
       │ HTTP
┌──────▼──────────┐
│  FastAPI Server │
│  (Port 8000)    │
└──────┬──────────┘
       │
┌──────▼──────────┐
│  Local Storage  │
│  (memory_data/) │
└─────────────────┘
```

## Future Enhancements

1. **Multi-Modal I/O**
   - Vision (image understanding)
   - Audio (voice commands)
   - Gesture recognition

2. **Advanced Memory**
   - Graph-based memory
   - Semantic similarity search
   - Time-based decay

3. **Distributed Execution**
   - Worker pool
   - Task distribution
   - Load balancing

4. **Real LLM Integration**
   - Ollama support
   - Local model serving
   - Fallback chain

5. **Advanced Consciousness**
   - Neural network-based emotions
   - Personality learning
   - Dream sequences
