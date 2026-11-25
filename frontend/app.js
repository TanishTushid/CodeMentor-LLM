const API_BASE = "";

const state = {
  view: "chat",
  history: [],
  busy: false,
};

const titles = {
  chat: ["Programming Chat", "GENERAL ASSISTANCE"],
  generate: ["Code Generation", "CODE GENERATION"],
  explain: ["Code Explanation", "CODE EXPLANATION"],
  debug: ["Debugging Assistant", "CODE DEBUGGING"],
  optimize: ["Code Optimization", "CODE OPTIMIZATION"],
};

const navItems = [...document.querySelectorAll(".nav-item")];
const chatView = document.getElementById("chatView");
const toolView = document.getElementById("toolView");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatForm = document.getElementById("chatForm");
const toolForm = document.getElementById("toolForm");
const primaryInput = document.getElementById("primaryInput");
const secondaryInput = document.getElementById("secondaryInput");
const languageInput = document.getElementById("languageInput");
const levelInput = document.getElementById("levelInput");
const levelField = document.getElementById("levelField");
const secondaryField = document.getElementById("secondaryField");
const resultPanel = document.getElementById("resultPanel");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderInline(value) {
  let text = escapeHtml(value);
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return text;
}

function renderMarkdown(markdown) {
  if (!markdown) return "";
  const source = String(markdown).replace(/\r\n/g, "\n");
  const codeBlocks = [];
  let html = source.replace(/```(?:[^\n]*)\n([\s\S]*?)```/g, (_, code) => {
    const index = codeBlocks.push(code) - 1;
    return `\u0000CODEBLOCK${index}\u0000`;
  });

  const lines = html.split("\n");
  const output = [];
  let listType = null;

  function closeList() {
    if (listType) {
      output.push(`</${listType}>`);
      listType = null;
    }
  }

  lines.forEach((line) => {
    if (line.includes("\u0000CODEBLOCK")) {
      closeList();
      const match = line.match(/\u0000CODEBLOCK(\d+)\u0000/);
      if (match) {
        const code = escapeHtml(codeBlocks[Number(match[1])]).replace(/\n$/, "");
        output.push(`<pre class="code-block"><button class="copy-code" type="button">Copy</button><code>${code}</code></pre>`);
      }
      return;
    }

    if (/^###?\s/.test(line)) {
      closeList();
      const text = line.replace(/^###?\s*/, "");
      output.push(`<h3>${renderInline(text)}</h3>`);
      return;
    }

    const unordered = line.match(/^[-*]\s+(.+)/);
    const ordered = line.match(/^\d+[.)]\s+(.+)/);
    if (unordered || ordered) {
      const type = unordered ? "ul" : "ol";
      if (listType !== type) {
        closeList();
        listType = type;
        output.push(`<${type}>`);
      }
      output.push(`<li>${renderInline((unordered || ordered)[1])}</li>`);
      return;
    }

    closeList();
    if (!line.trim()) {
      return;
    }
    output.push(`<p>${renderInline(line)}</p>`);
  });
  closeList();
  return output.join("");
}

async function requestJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "The model could not complete the request.");
  }
  return data;
}

async function checkHealth() {
  const dot = document.getElementById("statusDot");
  const label = document.getElementById("statusLabel");
  const detail = document.getElementById("statusDetail");
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    if (data.model_status === "loaded") {
      dot.className = "status-dot ready";
      label.textContent = "Model online";
      detail.textContent = data.device || "Ready";
    } else {
      dot.className = "status-dot error";
      label.textContent = "Model unavailable";
      detail.textContent = data.model_status;
    }
  } catch (_) {
    dot.className = "status-dot error";
    label.textContent = "API offline";
    detail.textContent = "Check server";
  }
}

function setView(view) {
  state.view = view;
  navItems.forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  document.getElementById("pageTitle").textContent = titles[view][0];
  chatView.classList.toggle("active", view === "chat");
  toolView.classList.toggle("active", view !== "chat");
  document.querySelector(".sidebar").classList.remove("open");
  document.getElementById("sidebarBackdrop").classList.remove("open");

  if (view === "chat") return;

  const configs = {
    generate: {
      eyebrow: "CODE GENERATION",
      title: "Generate code",
      primary: "Problem description",
      primaryPlaceholder: "Describe the problem or feature you want to build...",
      secondary: "Additional instructions",
      secondaryPlaceholder: "Optional requirements, style, or constraints",
      secondaryHidden: false,
      levelHidden: true,
      button: "Generate solution",
      empty: "Add a problem description to generate code.",
    },
    explain: {
      eyebrow: "CODE EXPLANATION",
      title: "Explain code",
      primary: "Code to explain",
      primaryPlaceholder: "Paste a function or code snippet...",
      secondary: "Additional context",
      secondaryPlaceholder: "Optional: add context or a specific question",
      secondaryHidden: true,
      levelHidden: false,
      button: "Explain code",
      empty: "Paste code and choose an explanation level.",
    },
    debug: {
      eyebrow: "CODE DEBUGGING",
      title: "Debug code",
      primary: "Code",
      primaryPlaceholder: "Paste the code that is failing...",
      secondary: "Error message",
      secondaryPlaceholder: "Optional: paste the error or expected behavior",
      secondaryHidden: false,
      levelHidden: true,
      button: "Find the issue",
      empty: "Add the code and any available error message.",
    },
    optimize: {
      eyebrow: "CODE OPTIMIZATION",
      title: "Optimize code",
      primary: "Code",
      primaryPlaceholder: "Paste the implementation to improve...",
      secondary: "Optimization objective",
      secondaryPlaceholder: "Improve clarity and efficiency",
      secondaryHidden: false,
      levelHidden: true,
      button: "Optimize solution",
      empty: "Paste code and describe your optimization goal.",
    },
  };
  const config = configs[view];
  document.getElementById("toolEyebrow").textContent = config.eyebrow;
  document.getElementById("toolTitle").textContent = config.title;
  document.getElementById("primaryLabel").textContent = config.primary;
  primaryInput.placeholder = config.primaryPlaceholder;
  document.getElementById("secondaryLabel").textContent = config.secondary;
  secondaryInput.placeholder = config.secondaryPlaceholder;
  secondaryField.hidden = config.secondaryHidden;
  levelField.hidden = config.levelHidden;
  document.querySelector("#submitButton span").textContent = config.button;
  primaryInput.value = "";
  secondaryInput.value = view === "optimize" ? "Improve clarity and efficiency" : "";
  levelInput.value = "beginner";
  resultPanel.innerHTML = `<div class="empty-result"><div class="empty-orb"><svg viewBox="0 0 24 24"><path d="m8.5 7-5 5 5 5M15.5 7l5 5-5 5M14 4l-4 16"/></svg></div><h3>Ready to help</h3><p>${config.empty}</p></div>`;
}

function appendChat(role, content) {
  const welcome = chatMessages.querySelector(".welcome-state");
  if (welcome) welcome.remove();
  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  row.innerHTML = `
    ${role === "assistant" ? '<div class="message-avatar">CM</div>' : ""}
    <div class="message-bubble">${role === "assistant" ? renderMarkdown(content) : escapeHtml(content).replace(/\n/g, "<br>")}</div>
  `;
  chatMessages.appendChild(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  attachCopyButtons(row);
  return row;
}

function attachCopyButtons(container = document) {
  container.querySelectorAll(".copy-code").forEach((button) => {
    if (button.dataset.bound) return;
    button.dataset.bound = "true";
    button.addEventListener("click", async () => {
      const code = button.nextElementSibling?.textContent || "";
      await navigator.clipboard.writeText(code);
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = "Copy"; }, 1200);
    });
  });
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message || state.busy) return;
  appendChat("user", message);
  chatInput.value = "";
  chatInput.style.height = "auto";
  state.busy = true;
  const submit = chatForm.querySelector(".send-button");
  submit.disabled = true;

  const loading = document.createElement("div");
  loading.className = "message-row assistant";
  loading.innerHTML = '<div class="message-avatar">CM</div><div class="message-bubble loading-row"><span>Thinking</span><span class="loading-dots"><i></i><i></i><i></i></span></div>';
  chatMessages.appendChild(loading);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const data = await requestJson("/api/chat", {
      message,
      conversation_history: state.history,
      generation: { max_new_tokens: 512, temperature: 0.7, top_p: 0.9, do_sample: false, repetition_penalty: 1.05 },
    });
    loading.remove();
    appendChat("assistant", data.response);
    state.history.push({ role: "user", content: message });
    state.history.push({ role: "assistant", content: data.response });
    state.history = state.history.slice(-20);
  } catch (error) {
    loading.remove();
    appendChat("assistant", `**Unable to respond:** ${error.message}`);
  } finally {
    state.busy = false;
    submit.disabled = false;
  }
});

chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = `${Math.min(chatInput.scrollHeight, 180)}px`;
});

chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

toolForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) return;
  const primary = primaryInput.value.trim();
  if (!primary) {
    primaryInput.focus();
    return;
  }

  const language = languageInput.value.trim();
  const secondary = secondaryInput.value.trim();
  const generation = { max_new_tokens: 512, temperature: 0.7, top_p: 0.9, do_sample: false, repetition_penalty: 1.05 };
  let payload;
  let path;

  if (state.view === "generate") {
    path = "/api/generate";
    payload = { programming_language: language, problem_description: primary, additional_instructions: secondary || null, generation };
  } else if (state.view === "explain") {
    path = "/api/explain";
    payload = { code: primary, programming_language: language, explanation_level: levelInput.value, generation };
  } else if (state.view === "debug") {
    path = "/api/debug";
    payload = { code: primary, programming_language: language, error_message: secondary || null, generation };
  } else {
    path = "/api/optimize";
    payload = { code: primary, programming_language: language, optimization_objective: secondary || "Improve clarity and efficiency", generation };
  }

  state.busy = true;
  const submit = document.getElementById("submitButton");
  submit.disabled = true;
  resultPanel.innerHTML = '<div class="empty-result"><div class="loading-row"><span>Code Mentor is working</span><span class="loading-dots"><i></i><i></i><i></i></span></div></div>';

  try {
    const data = await requestJson(path, payload);
    renderToolResult(data);
  } catch (error) {
    resultPanel.innerHTML = `<div class="error-card"><strong>Request failed</strong><br>${escapeHtml(error.message)}</div>`;
  } finally {
    state.busy = false;
    submit.disabled = false;
  }
});

function section(title, content, asCode = false) {
  if (!content) return "";
  const body = asCode
    ? `<pre class="code-block"><button class="copy-code" type="button">Copy</button><code>${escapeHtml(content).replace(/\n/g, "<br>").replace(/<br>/g, "\n")}</code></pre>`
    : `<div class="result-card">${renderMarkdown(content)}</div>`;
  return `<div class="result-section"><h3>${escapeHtml(title)}</h3>${body}</div>`;
}

function renderToolResult(data) {
  let html = '<div class="result-content">';
  if (state.view === "generate") {
    html += section("Generated code", data.generated_code, true);
    html += section("Explanation", data.explanation);
  } else if (state.view === "explain") {
    html += section("Explanation", data.code_explanation);
    html += section("Important concepts", (data.important_concepts || []).join("\n"));
    html += section("Step-by-step breakdown", (data.step_by_step_breakdown || []).join("\n"));
  } else if (state.view === "debug") {
    html += section("Identified issue", data.identified_issue);
    html += section("Corrected code", data.corrected_code, true);
    html += section("Explanation of the fix", data.explanation_of_the_fix);
  } else {
    html += section("Optimized code", data.optimized_code, true);
    html += section("Improvements", data.explanation_of_improvements);
    html += section("Time complexity", data.time_complexity);
    html += section("Space complexity", data.space_complexity);
  }
  html += "</div>";
  resultPanel.innerHTML = html;
  attachCopyButtons(resultPanel);
}

navItems.forEach((item) => item.addEventListener("click", () => setView(item.dataset.view)));

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    chatInput.value = button.dataset.prompt;
    chatInput.focus();
  });
});

document.getElementById("clearButton").addEventListener("click", () => {
  if (state.view === "chat") {
    state.history = [];
    chatMessages.innerHTML = `
      <div class="welcome-state">
        <h2>What would you like to learn?</h2>
        <p>Ask a programming question or choose a starting point.</p>
        <div class="prompt-grid">
          <button type="button" data-prompt="Explain recursion with a simple Python example">Explain recursion</button>
          <button type="button" data-prompt="How should I design a REST API for a todo application?">Design a REST API</button>
          <button type="button" data-prompt="What is the difference between a stack and a queue?">Compare data structures</button>
        </div>
      </div>
    `;
    document.querySelectorAll("#chatMessages [data-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        chatInput.value = button.dataset.prompt;
        chatInput.focus();
      });
    });
  } else {
    primaryInput.value = "";
    setView(state.view);
  }
});

document.getElementById("menuButton").addEventListener("click", () => {
  document.querySelector(".sidebar").classList.add("open");
  document.getElementById("sidebarBackdrop").classList.add("open");
});
document.getElementById("sidebarBackdrop").addEventListener("click", () => {
  document.querySelector(".sidebar").classList.remove("open");
  document.getElementById("sidebarBackdrop").classList.remove("open");
});

checkHealth();
