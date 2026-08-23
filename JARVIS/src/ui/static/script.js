// =====================================================================
// JARVIS UI - Complete Script
// =====================================================================

// --- DOM Elements ---
const bgCanvas = document.getElementById('bgCanvas');
const bgCtx = bgCanvas.getContext('2d');
const orbCanvas = document.getElementById('orbCanvas');
const orbCtx = orbCanvas.getContext('2d');
const clockTime = document.getElementById('clock-time');
const clockDate = document.getElementById('clock-date');
const stateLabel = document.getElementById('state-label');
const pttBtn = document.getElementById('ptt-btn');
const textInput = document.getElementById('text-input');
const sendBtn = document.getElementById('send-btn');
const chatPanel = document.getElementById('chat-panel');
const chatMessages = document.getElementById('chat-messages');
const chatToggle = document.getElementById('chat-toggle');
const closeChat = document.getElementById('close-chat');
const ttsToggle = document.getElementById('tts-toggle');
const connIndicator = document.getElementById('conn-indicator');
const micIndicator = document.getElementById('mic-indicator');
const systemStatus = document.getElementById('system-status');

// =====================================================================
// STATE
// =====================================================================
let jarvisState = 'idle'; // idle | listening | thinking | speaking
let ttsEnabled = true;
let isRecording = false;
let animFrame = 0;

// =====================================================================
// RESIZE
// =====================================================================
function resizeAll() {
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
    orbCanvas.width = orbCanvas.offsetWidth;
    orbCanvas.height = orbCanvas.offsetHeight;
}
window.addEventListener('resize', resizeAll);
resizeAll();

// =====================================================================
// CLOCK
// =====================================================================
function updateClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    clockTime.textContent = `${h}:${m}`;

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    clockDate.textContent = `${days[now.getDay()]}, ${String(now.getDate()).padStart(2, '0')} ${months[now.getMonth()]}`;
}
updateClock();
setInterval(updateClock, 1000);

// =====================================================================
// BACKGROUND PARTICLES (subtle ambient dots)
// =====================================================================
const bgParticles = Array.from({ length: 120 }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    r: Math.random() * 1.2 + 0.3,
    vx: (Math.random() - 0.5) * 0.15,
    vy: (Math.random() - 0.5) * 0.15,
    opacity: Math.random() * 0.3 + 0.05
}));

function drawBg(t) {
    const W = bgCanvas.width, H = bgCanvas.height;
    bgCtx.clearRect(0, 0, W, H);

    // Dark radial gradient background
    const grad = bgCtx.createRadialGradient(W * 0.5, H * 0.5, 0, W * 0.5, H * 0.5, W * 0.7);
    grad.addColorStop(0, '#0e1520');
    grad.addColorStop(1, '#070a0f');
    bgCtx.fillStyle = grad;
    bgCtx.fillRect(0, 0, W, H);

    bgParticles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;

        bgCtx.beginPath();
        bgCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        bgCtx.fillStyle = `rgba(79,172,254,${p.opacity})`;
        bgCtx.fill();
    });
}

// =====================================================================
// ORB PARTICLE SPHERE (2000 particles on a globe)
// =====================================================================
const ORB_PARTICLES = 2000;
const orbParticles = [];

for (let i = 0; i < ORB_PARTICLES; i++) {
    const theta = Math.acos(2 * Math.random() - 1);
    const phi = Math.random() * Math.PI * 2;
    orbParticles.push({
        theta,
        phi,
        dPhi: (Math.random() - 0.5) * 0.003,
        dTheta: (Math.random() - 0.5) * 0.001,
        r: Math.random() * 0.5 + 0.5,  // 0.5 = inside, 1 = on surface
        size: Math.random() * 1.2 + 0.3,
        baseOpacity: Math.random() * 0.6 + 0.2,
    });
}

let orbRotation = 0;
let orbRotationSpeed = 0.0015;

// State-based visual config
const STATE_CONFIG = {
    idle: {
        speedMult: 1,
        color: (op) => `rgba(79,172,254,${op})`,
        edgeColor: 'rgba(79,172,254,0.5)',
        glowColor: 'rgba(79,172,254,0.15)',
        stateText: 'IDLE',
        stateLabelColor: 'rgba(79,172,254,0.4)',
    },
    listening: {
        speedMult: 2.5,
        color: (op) => `rgba(255,71,87,${op})`,
        edgeColor: 'rgba(255,71,87,0.6)',
        glowColor: 'rgba(255,71,87,0.2)',
        stateText: 'LISTENING',
        stateLabelColor: '#ff4757',
    },
    thinking: {
        speedMult: 4,
        color: (op) => `rgba(168,85,247,${op})`,
        edgeColor: 'rgba(168,85,247,0.6)',
        glowColor: 'rgba(168,85,247,0.2)',
        stateText: 'THINKING',
        stateLabelColor: '#a855f7',
    },
    speaking: {
        speedMult: 3,
        color: (op) => `rgba(0,242,254,${op})`,
        edgeColor: 'rgba(0,242,254,0.7)',
        glowColor: 'rgba(0,242,254,0.2)',
        stateText: 'SPEAKING',
        stateLabelColor: '#00f2fe',
    },
};

function drawOrb(t) {
    const W = orbCanvas.width;
    const H = orbCanvas.height;
    const CX = W / 2;
    const CY = H / 2;
    const RADIUS = Math.min(W, H) * 0.44;

    orbCtx.clearRect(0, 0, W, H);

    const cfg = STATE_CONFIG[jarvisState] || STATE_CONFIG.idle;
    orbRotationSpeed = 0.0015 * cfg.speedMult;
    orbRotation += orbRotationSpeed;

    // Glow aura
    const aura = orbCtx.createRadialGradient(CX, CY, RADIUS * 0.5, CX, CY, RADIUS * 1.3);
    aura.addColorStop(0, cfg.glowColor);
    aura.addColorStop(1, 'transparent');
    orbCtx.fillStyle = aura;
    orbCtx.beginPath();
    orbCtx.arc(CX, CY, RADIUS * 1.3, 0, Math.PI * 2);
    orbCtx.fill();

    // Outer ring
    orbCtx.beginPath();
    orbCtx.arc(CX, CY, RADIUS, 0, Math.PI * 2);
    orbCtx.strokeStyle = cfg.edgeColor;
    orbCtx.lineWidth = 0.8;
    orbCtx.stroke();

    // Wave distortion (for speaking/listening)
    let waveAmt = 0;
    if (jarvisState === 'speaking') waveAmt = Math.sin(t * 0.006) * 8;
    if (jarvisState === 'listening') waveAmt = Math.sin(t * 0.004) * 5;

    // Draw particles
    orbParticles.forEach(p => {
        p.phi += p.dPhi + orbRotationSpeed;
        p.theta += p.dTheta;

        const sineTheta = Math.sin(p.theta);
        const x = Math.sin(p.phi) * sineTheta;
        const y = Math.cos(p.theta);
        const z = Math.cos(p.phi) * sineTheta;

        // Rotate around Y-axis over time
        const cosR = Math.cos(orbRotation);
        const sinR = Math.sin(orbRotation);
        const rx = x * cosR + z * sinR;
        const rz = -x * sinR + z * cosR;

        // Perspective project
        const perspective = 2.2;
        const scale = perspective / (perspective - rz * 0.4);

        const px = CX + rx * RADIUS * scale + Math.sin(t * 0.002 + p.phi) * waveAmt;
        const py = CY + y * RADIUS * scale * 0.98;

        // Depth-based opacity + size
        const depth = (rz + 1) / 2;
        const opacity = p.baseOpacity * (0.4 + depth * 0.6);
        const size = p.size * scale;

        orbCtx.beginPath();
        orbCtx.arc(px, py, Math.max(0.1, size * p.r), 0, Math.PI * 2);
        orbCtx.fillStyle = cfg.color(opacity);
        orbCtx.fill();
    });
}

// =====================================================================
// MAIN ANIMATION LOOP
// =====================================================================
function loop(t) {
    animFrame = requestAnimationFrame(loop);
    drawBg(t);
    drawOrb(t);
}
loop(0);

// =====================================================================
// SET STATE
// =====================================================================
function setState(state) {
    jarvisState = state;
    const cfg = STATE_CONFIG[state] || STATE_CONFIG.idle;
    stateLabel.textContent = cfg.stateText;
    stateLabel.style.color = cfg.stateLabelColor;
    systemStatus.textContent = state === 'idle' ? 'SYSTEM ONLINE' : `SYSTEM — ${cfg.stateText}`;
    systemStatus.style.color = cfg.stateLabelColor;
}

// =====================================================================
// WEBSOCKET
// =====================================================================
let ws = null;

function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/chat`);

    ws.onopen = () => {
        connIndicator.querySelector('.dot').classList.add('connected');
        setState('idle');
    };

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'status') {
            setState(data.status);
        } else if (data.type === 'message') {
            addMessage(data.text, 'jarvis-msg');
            setState('speaking');
            if (ttsEnabled) {
                speak(data.text, data.audio_url, () => setState('idle'));
            } else {
                setState('idle');
            }
        }
    };

    ws.onclose = () => {
        connIndicator.querySelector('.dot').classList.remove('connected');
        setTimeout(connectWS, 3000);
    };
}
connectWS();

function sendMessage(text) {
    if (!text.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;
    addMessage(text, 'user-msg');

    // Auto-open chat panel on first message
    if (chatPanel.classList.contains('hidden')) {
        chatPanel.classList.remove('hidden');
        chatToggle.classList.add('active');
    }

    setState('thinking');
    ws.send(JSON.stringify({ text }));
}

// =====================================================================
// CHAT UI
// =====================================================================
function addMessage(text, cls) {
    const div = document.createElement('div');
    div.className = `message ${cls}`;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatToggle.addEventListener('click', () => {
    const hidden = chatPanel.classList.toggle('hidden');
    chatToggle.classList.toggle('active', !hidden);
});
closeChat.addEventListener('click', () => {
    chatPanel.classList.add('hidden');
    chatToggle.classList.remove('active');
});

sendBtn.addEventListener('click', () => {
    sendMessage(textInput.value);
    textInput.value = '';
});
textInput.addEventListener('keypress', e => {
    if (e.key === 'Enter') {
        sendMessage(textInput.value);
        textInput.value = '';
    }
});

// =====================================================================
// TEXT-TO-SPEECH (Piper TTS / Browser Fallback)
// =====================================================================
let currentAudio = null;
let currentUtterance = null;

function speak(text, audioUrl, onEnd) {
    if (!ttsEnabled) { if (onEnd) onEnd(); return; }

    // Stop any playing audio or speech
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }

    // 1. Prefer Piper TTS (Thorsten German male voice)
    if (audioUrl) {
        try {
            currentAudio = new Audio(audioUrl);
            currentAudio.onended = () => {
                currentAudio = null;
                if (onEnd) onEnd();
            };
            currentAudio.onerror = () => {
                console.warn("Piper audio playback failed, falling back to Web Speech API.");
                currentAudio = null;
                fallbackSpeak(text, onEnd);
            };
            currentAudio.play().catch(err => {
                console.warn("Audio autoplay blocked or failed:", err);
                fallbackSpeak(text, onEnd);
            });
            return;
        } catch (e) {
            console.error("Audio error:", e);
        }
    }

    // 2. Fallback to Web Speech API
    fallbackSpeak(text, onEnd);
}

function fallbackSpeak(text, onEnd) {
    if (!window.speechSynthesis) { if (onEnd) onEnd(); return; }
    const utterance = new SpeechSynthesisUtterance(text);
    currentUtterance = utterance;

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v => v.lang === 'de-DE') || voices[0];
    if (preferred) utterance.voice = preferred;

    utterance.lang = 'de-DE';
    utterance.rate = 1.05;
    utterance.pitch = 0.9;

    utterance.onend = () => { if (onEnd) onEnd(); };
    utterance.onerror = () => { if (onEnd) onEnd(); };

    window.speechSynthesis.speak(utterance);
}

// TTS Toggle Button
ttsToggle.addEventListener('click', () => {
    ttsEnabled = !ttsEnabled;
    ttsToggle.classList.toggle('active', ttsEnabled);
    if (!ttsEnabled) {
        window.speechSynthesis.cancel();
        if (jarvisState === 'speaking') setState('idle');
    }
});
// Start as active
ttsToggle.classList.add('active');

// =====================================================================
// PUSH-TO-TALK (Web Speech API)
// =====================================================================
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'de-DE';
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        isRecording = true;
        pttBtn.classList.add('listening');
        micIndicator.querySelector('.dot').classList.add('recording');
        setState('listening');
        // Stop TTS while listening
        window.speechSynthesis.cancel();
    };

    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        textInput.value = transcript;
    };

    recognition.onend = () => {
        pttBtn.classList.remove('listening');
        micIndicator.querySelector('.dot').classList.remove('recording');
        isRecording = false;
        const val = textInput.value.trim();
        if (val) {
            sendMessage(val);
            textInput.value = '';
        } else {
            setState('idle');
        }
    };

    recognition.onerror = (e) => {
        console.warn('Speech error:', e.error);
        pttBtn.classList.remove('listening');
        micIndicator.querySelector('.dot').classList.remove('recording');
        isRecording = false;
        setState('idle');
    };
} else {
    pttBtn.style.opacity = '0.3';
    pttBtn.title = 'Spracherkennung nicht verfügbar';
}

function startListening() {
    if (!recognition || isRecording) return;
    try {
        window.speechSynthesis.cancel(); // stop speaking
        recognition.start();
    } catch (e) {}
}

function stopListening() {
    if (!recognition || !isRecording) return;
    recognition.stop();
}

// Mouse
pttBtn.addEventListener('mousedown', (e) => { e.preventDefault(); startListening(); });
window.addEventListener('mouseup', stopListening);

// Touch
pttBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startListening(); });
window.addEventListener('touchend', stopListening);

// Keyboard: SPACE = push to talk
window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && document.activeElement !== textInput && !isRecording) {
        e.preventDefault();
        startListening();
    }
});
window.addEventListener('keyup', (e) => {
    if (e.code === 'Space' && isRecording) {
        e.preventDefault();
        stopListening();
    }
});
