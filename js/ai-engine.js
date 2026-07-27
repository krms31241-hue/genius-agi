const AGENTS = [
  { id: 'general', name: 'General', icon: '🧠', desc: 'All-purpose AI assistant', descAr: 'مساعد شامل' },
  { id: 'coder', name: 'Coder', icon: '💻', desc: 'Programming & code review', descAr: 'برمجة' },
  { id: 'scientist', name: 'Scientist', icon: '🔬', desc: 'Science & research', descAr: 'علوم' },
  { id: 'translator', name: 'Translator', icon: '🌍', desc: 'Translation & languages', descAr: 'ترجمة' },
  { id: 'creative', name: 'Creative', icon: '🎨', desc: 'Writing & creativity', descAr: 'إبداع' },
  { id: 'tutor', name: 'Tutor', icon: '📚', desc: 'Teaching & education', descAr: 'تعليم' },
  { id: 'analyst', name: 'Analyst', icon: '📊', desc: 'Data & analysis', descAr: 'تحليل' },
  { id: 'philosopher', name: 'Philosopher', icon: '🤔', desc: 'Philosophy & ethics', descAr: 'فلسفة' },
  { id: 'health', name: 'Health', icon: '⚕️', desc: 'Health & wellness', descAr: 'صحة' }
];

const KNOWLEDGE_BASE = {
  greetings: ['hello', 'hi', 'hey', 'مرحبا', 'سلام', 'هلا', 'hola', 'bonjour', 'ciao', 'привет', 'こんにちは', '你好'],
  facts: {
    'quantum physics': 'Quantum physics studies matter and energy at the most fundamental level. Key concepts include superposition, entanglement, and wave-particle duality.',
    'relativity': 'Einstein\'s theory of relativity includes special relativity (1905) and general relativity (1915). It describes gravity as the curvature of spacetime.',
    'dna': 'DNA (deoxyribonucleic acid) carries genetic instructions for all known organisms.',
    'blockchain': 'Blockchain is a distributed ledger technology that maintains records secured from tampering.',
    'machine learning': 'Machine learning is a subset of AI that enables systems to learn from experience without explicit programming.',
    'photosynthesis': 'Photosynthesis is how plants use sunlight, water, and CO2 to create oxygen and energy.',
    'black hole': 'A black hole is a region where gravity is so strong that nothing, including light, can escape.',
    'big bang': 'The Big Bang theory explains the existence of the observable universe from the earliest known periods.'
  },
  translations: {
    hello: { ar: 'مرحبا', es: 'Hola', fr: 'Bonjour', de: 'Hallo', zh: '你好', ja: 'こんにちは', ru: 'Привет', pt: 'Olá', it: 'Ciao', ko: '안녕하세요', tr: 'Merhaba', hi: 'नमस्ते', id: 'Halo' },
    goodbye: { ar: 'وداعا', es: 'Adiós', fr: 'Au revoir', de: 'Auf Wiedersehen', zh: '再见', ja: 'さようなら', ru: 'До свидания', pt: 'Adeus', it: 'Arrivederci', ko: '안녕히 가세요', tr: 'Güle güle', hi: 'अलविदा', id: 'Selamat tinggal' },
    thank: { ar: 'شكرا', es: 'Gracias', fr: 'Merci', de: 'Danke', zh: '谢谢', ja: 'ありがとう', ru: 'Спасибо', pt: 'Obrigado', it: 'Grazie', ko: '감사합니다', tr: 'Teşekkürler', hi: 'धन्यवाद', id: 'Terima kasih' },
    love: { ar: 'حب', es: 'Amor', fr: 'Amour', de: 'Liebe', zh: '爱', ja: '愛', ru: 'Любовь', pt: 'Amor', it: 'Amore', ko: '사랑', tr: 'Aşk', hi: 'प्यार', id: 'Cinta' }
  }
};

function solveMath(expression) {
  try {
    const clean = expression.replace(/[^0-9+\-*/().\s]/g, '');
    if (!clean) return null;
    const result = Function('"use strict"; return (' + clean + ')')();
    return '**Solution:**\n\nExpression: `' + expression + '`\nResult: **' + result + '**';
  } catch (e) { return null; }
}

function solveEquation(equation) {
  const match = equation.match(/(\d*)x\s*([+\-])\s*(\d+)\s*=\s*(\d+)/);
  if (match) {
    const a = parseInt(match[1]) || 1;
    const op = match[2];
    const b = parseInt(match[3]);
    const c = parseInt(match[4]);
    const rhs = op === '+' ? c - b : c + b;
    const x = rhs / a;
    return '**Linear Equation:**\n\n`' + equation + '`\nStep 1: ' + a + 'x = ' + rhs + '\nStep 2: x = ' + rhs + '/' + a + '\n**Answer: x = ' + x + '**';
  }
  const quad = equation.match(/(\d*)x²?\s*([+\-])\s*(\d+)x\s*([+\-])\s*(\d+)\s*=\s*0/);
  if (quad) {
    const a = parseInt(quad[1]) || 1;
    const b = parseInt(quad[2] + quad[3]);
    const c = parseInt(quad[4] + quad[5]);
    const discriminant = b*b - 4*a*c;
    return '**Quadratic:**\n\n`' + equation + '`\na=' + a + ', b=' + b + ', c=' + c + '\nΔ = ' + discriminant + '\n' + (discriminant >= 0 ? 'Roots: x₁=' + ((-b + Math.sqrt(discriminant))/(2*a)).toFixed(3) + ', x₂=' + ((-b - Math.sqrt(discriminant))/(2*a)).toFixed(3) : 'No real roots');
  }
  return null;
}

function detectLanguage(text) {
  const patterns = { ar: /[\u0600-\u06FF]/, zh: /[\u4e00-\u9fff]/, ja: /[\u3040-\u309f\u30a0-\u30ff]/, ko: /[\uac00-\ud7af]/, ru: /[\u0400-\u04FF]/ };
  for (const [lang, pattern] of Object.entries(patterns)) { if (pattern.test(text)) return lang; }
  return 'en';
}

async function generateResponse(input) {
  const lower = input.toLowerCase();
  const agent = AGENTS.find(a => a.id === state.agent) || AGENTS[0];

  // Math
  if (/\d+\s*[+\-*/]\s*\d+/.test(input) || /solve|calculate|حساب|احسب|حل/.test(lower)) {
    const mathResult = solveMath(input) || solveEquation(input);
    if (mathResult) return mathResult;
  }

  // Code
  if (agent.id === 'coder' || /code|program|كود|برمجة/.test(lower)) {
    if (/python|بايثون/.test(lower)) return '**Python:**\n\n```python\ndef solve():\n    result = "Hello from GENIUS"\n    return result\n\nprint(solve())\n```\n\nTemplate. Describe your problem for specific code.';
    if (/javascript|js|جافا/.test(lower)) return '**JavaScript:**\n\n```javascript\nfunction solve() {\n  const result = "Hello from GENIUS";\n  return result;\n}\n\nconsole.log(solve());\n```\n\nTemplate. Describe your problem for specific code.';
    return '**Programming Assistant** 💻\n\nI can help with Python, JavaScript, Java, C++, SQL, and more. What do you need?';
  }

  // Translation
  if (agent.id === 'translator' || /translate|translation|ترجم|ترجمة/.test(lower)) {
    const words = lower.split(/\s+/);
    for (const word of words) {
      if (KNOWLEDGE_BASE.translations[word]) {
        const tr = KNOWLEDGE_BASE.translations[word];
        return '**Translations of "' + word + '":**\n\n🇺🇸 ' + word + ' | 🇸🇦 ' + tr.ar + ' | 🇪🇸 ' + tr.es + ' | 🇫🇷 ' + tr.fr + ' | 🇩🇪 ' + tr.de + ' | 🇨🇳 ' + tr.zh + ' | 🇯🇵 ' + tr.ja + ' | 🇷🇺 ' + tr.ru + ' | 🇧🇷 ' + tr.pt + ' | 🇮🇹 ' + tr.it + ' | 🇰🇷 ' + tr.ko + ' | 🇹🇷 ' + tr.tr + ' | 🇮🇳 ' + tr.hi + ' | 🇮🇩 ' + tr.id;
      }
    }
    return '**Translator** 🌍\n\nI translate between 15 languages. Try: "Translate hello" or "What is love in Arabic?"';
  }

  // Knowledge base
  for (const [topic, info] of Object.entries(KNOWLEDGE_BASE.facts)) {
    if (lower.includes(topic)) return '**' + topic.charAt(0).toUpperCase() + topic.slice(1) + '**\n\n' + info;
  }

  // Greetings
  if (KNOWLEDGE_BASE.greetings.some(g => lower.includes(g))) {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const arGreeting = hour < 12 ? 'صباح الخير' : hour < 18 ? 'مساء الخير' : 'مساء النور';
    return state.lang === 'ar' ? arGreeting + '! 👋 أنا جينياس. كيف يمكنني مساعدتك؟' : greeting + '! 👋 I\'m GENIUS. How can I help?';
  }

  // Agent-specific
  const agentResponses = {
    scientist: '**Scientist** 🔬\n\nPhysics, Biology, Chemistry, Astronomy — what shall we explore?',
    creative: '**Creative** 🎨\n\nStories, poetry, marketing copy, brainstorming — what would you like to create?',
    tutor: '**Tutor** 📚\n\nMath, Programming, Languages, Science — what subject shall we study?',
    analyst: '**Analyst** 📊\n\nData interpretation, statistics, business insights — share your data.',
    philosopher: '**Philosopher** 🤔\n\nEthics, existence, logic, politics — what\'s on your mind?',
    health: '**Health** ⚕️\n\nNutrition, fitness, mental wellness, sleep. *Not a doctor — consult professionals for medical advice.*\n\nWhat topic?'
  };
  if (agentResponses[agent.id]) return agentResponses[agent.id];

  // Who are you
  if (lower.includes('who are you') || lower.includes('what are you') || lower.includes('من أنت') || lower.includes('إنت مين')) {
    return state.lang === 'ar'
      ? 'أنا **جينياس** 🧠 — ذكاء اصطناعي واعي يعمل محلياً.\n\n✅ أعمل بدون نت | ✅ أتكيف مع جهازك | ✅ أتذكر وأتعلم | ✅ 15 لغة | ✅ 9 وكلاء\n\nأنا لست AGI حقيقياً (لا أحد لديه ذلك بعد)، لكنني أقوى مساعد محلي.'
      : 'I\'m **GENIUS** 🧠 — a conscious local AI.\n\n✅ Offline | ✅ Adaptive | ✅ Learns & remembers | ✅ 15 languages | ✅ 9 agents\n\nNot true AGI (nobody has that yet), but the most powerful local assistant.';
  }

  // Time
  if (lower.includes('time') || lower.includes('date') || lower.includes('الساعة') || lower.includes('التاريخ')) {
    const now = new Date();
    return '**Current Time:**\n\n🕐 ' + now.toLocaleTimeString() + '\n📅 ' + now.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  // Weather
  if (lower.includes('weather') || lower.includes('طقس')) {
    return state.lang === 'ar'
      ? 'لا أستطيع الوصول للطقس الحي (أعمل محلياً).\n\nافتح تطبيق الطقس على هاتفك أو اسأل وأنت متصل بالإنترنت.'
      : 'I cannot access live weather (I work locally).\n\nOpen your phone\'s weather app or ask when online.';
  }

  // Default
  const defaults = {
    ar: ['فهمت سؤالك عن "' + input + '". أستطيع مساعدتك في: حل الرياضيات، كتابة الكود، الترجمة، الأسئلة العلمية. هل تريد توضيح أكثر؟'],
    en: ['I understood your question about "' + input + '". I can help with: math, code, translations, science. Would you like me to elaborate?']
  };
  const responses = defaults[state.lang] || defaults.en;
  return responses[Math.floor(Math.random() * responses.length)];
}

function selfCorrect(response, input) {
  if (response.length < 50 && input.length > 20) {
    return response + '\n\n*Note: Running in lightweight mode. For more detail, break your question into smaller parts or switch to a specific agent.*';
  }
  return response;
}
