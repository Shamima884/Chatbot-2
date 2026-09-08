/* TMMCH Virtual Assistant — UI logic */
"use strict";

const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const messagesEl = document.getElementById("messages");
const typingEl = document.getElementById("typing");
const resetBtn = document.getElementById("reset-btn");
const sendBtn = document.getElementById("send-btn");

/* ---------- helpers ---------- */

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

/* Lightweight markdown-ish formatter (bold, italic, inline code, code blocks) */
function formatMessage(text) {
  const escaped = escapeHtml(text);
  const blocks = [];
  let html = escaped.replace(/```([\s\S]*?)```/g, (m, code) => {
    blocks.push(code.trim());
    return `\u0000${blocks.length - 1}\u0000`;
  });
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\n/g, "<br>");
  blocks.forEach((b, i) => {
    html = html.replace(`\u0000${i}\u0000`, `<pre class="code-block">${b}</pre>`);
  });
  return html;
}

function addMessage(role, content) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  const avatar = role === "user" ? "👤" : "T";
  const body = role === "assistant" ? formatMessage(content) : escapeHtml(content);
  message.innerHTML = `
    <div class="avatar" aria-hidden="true">${avatar}</div>
    <div class="bubble">${body}</div>`;
  messagesEl.appendChild(message);
  scrollToBottom();
}

function setTyping(visible) {
  typingEl.classList.toggle("visible", visible);
  if (visible) {
    messagesEl.append(typingEl); // keep it below the latest message
    scrollToBottom();
  }
}

/* ---------- actions ---------- */

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  addMessage("user", message);
  setTyping(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    addMessage("assistant", data.reply);
  } catch (err) {
    addMessage("assistant", `⚠️ Something went wrong: ${err.message}`);
  } finally {
    setTyping(false);
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

async function resetConversation() {
  try {
    await fetch("/api/reset", { method: "POST" });
  } catch (_) {
    /* server-side history will be cleared on next restart anyway */
  }
  messagesEl.innerHTML = "";
  if (typingEl.parentNode !== messagesEl) {
    messagesEl.append(typingEl); // keep the typing indicator usable
  }
  addMessage(
    "assistant",
    "New conversation started. How may I help you?"
  );
}

/* ---------- event wiring ---------- */

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage();
});

resetBtn.addEventListener("click", resetConversation);

/* ---------- initial greeting ---------- */

addMessage(
  "assistant",
  "Welcome to **TMMCH**. I'm the college virtual assistant — ask me about admissions, departments, hospital services or contact details."
);