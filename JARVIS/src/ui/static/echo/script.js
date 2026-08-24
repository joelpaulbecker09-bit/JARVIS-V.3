const stateEl = document.getElementById('state');
const substateEl = document.getElementById('substate');
const responseTextEl = document.getElementById('responseText');
const connectionEl = document.getElementById('connection');
const clockEl = document.getElementById('clock');
const time2El = document.getElementById('time2');
const body = document.body;

function updateClock() {
  const now = new Date();
  const value = now.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  clockEl.textContent = value;
  time2El.textContent = value;
}
setInterval(updateClock, 1000);
updateClock();

let socket;
let reconnectTimer;

function setState(title, subtitle, thinking = false) {
  stateEl.textContent = title;
  substateEl.textContent = subtitle;
  body.classList.toggle('thinking', thinking);
}

function connect() {
  clearTimeout(reconnectTimer);
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/ws/chat`);

  socket.addEventListener('open', () => {
    connectionEl.textContent = 'ONLINE';
    setState('SYSTEM ONLINE', 'Awaiting command, Sir.');
  });

  socket.addEventListener('message', async (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'status') {
        setState('THINKING', data.text || 'Processing request, Sir.', true);
      } else if (data.type === 'message') {
        responseTextEl.textContent = data.text || '';
        setState('SYSTEM ONLINE', 'Response ready, Sir.');
        if (data.audio_url) {
          try {
            const audio = new Audio(data.audio_url);
            audio.play().catch(() => {});
          } catch (_) {}
        }
      }
    } catch (_) {}
  });

  socket.addEventListener('close', () => {
    connectionEl.textContent = 'OFFLINE';
    setState('SYSTEM OFFLINE', 'Attempting reconnection...');
    reconnectTimer = setTimeout(connect, 3000);
  });

  socket.addEventListener('error', () => {
    connectionEl.textContent = 'ERROR';
  });
}

connect();
