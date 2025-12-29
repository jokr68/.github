(() => {
  const chatWindow = document.getElementById("chatWindow");
  const userInput = document.getElementById("userInput");
  const btnSend = document.getElementById("btnSend");
  const btnClear = document.getElementById("btnClear");
  const btnSettings = document.getElementById("btnSettings");
  const btnCloseSettings = document.getElementById("btnCloseSettings");
  const btnSaveSettings = document.getElementById("btnSaveSettings");
  const drawer = document.getElementById("settingsDrawer");
  const toast = document.getElementById("toast");
  const fileInput = document.getElementById("fileInput");
  const fileName = document.getElementById("fileName");
  const btnProcessFile = document.getElementById("btnProcessFile");

  const apiBaseEl = document.getElementById("apiBase");
  const apiKeyEl = document.getElementById("apiKey");
  const modelEl = document.getElementById("model");
  const systemPromptEl = document.getElementById("systemPrompt");

  const state = {
    apiBase: "",
    apiKey: "",
    model: "",
    systemPrompt: "",
    messages: [],
    pendingFile: null
  };

  function loadState() {
    try {
      const raw = localStorage.getItem("lordos-state");
      if (raw) Object.assign(state, JSON.parse(raw));
      apiBaseEl.value = state.apiBase || "https://openrouter.ai/api/v1";
      apiKeyEl.value = state.apiKey || "";
      modelEl.value = state.model || "qwen/qwen-2.5-72b-instruct";
      systemPromptEl.value = state.systemPrompt || "وكيل عربي متعدد اللهجات، خبير تطوير ومنتاج، دقيق وعميق التفكير.";
      renderMessages();
    } catch (e) { console.error(e); }
  }

  function saveState() {
    localStorage.setItem("lordos-state", JSON.stringify({
      ...state,
      pendingFile: null // لا نخزن الملف
    }));
  }

  function renderMessages() {
    chatWindow.innerHTML = "";
    state.messages.forEach(msg => appendMessage(msg.role, msg.content, msg.time, true));
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function appendMessage(role, content, time = new Date().toLocaleTimeString(), skipPush=false) {
    if (!skipPush) state.messages.push({ role, content, time });
    const div = document.createElement("div");
    div.className = `msg ${role === "user" ? "user" : "bot"}`;
    div.innerHTML = `<span class="role">${role === "user" ? "أنت" : "AtheerGAI"}</span>${escapeHtml(content)}<span class="time">${time}</span>`;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    if (!skipPush) saveState();
  }

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  }

  async function sendMessage(extraUserContent = "") {
    const text = (userInput.value || "").trim();
    if (!text && !extraUserContent) return;
    const finalUser = [text, extraUserContent].filter(Boolean).join("\n\n");
    if (!finalUser) return;

    appendMessage("user", finalUser);
    userInput.value = "";

    const apiBase = state.apiBase.trim();
    const apiKey = state.apiKey.trim();
    const model = state.model.trim();
    const sys = state.systemPrompt.trim();

    if (!apiBase || !model) {
      showToast("ضبط الإعدادات أولاً: API Base و Model");
      return;
    }

    appendMessage("assistant", "… جارٍ المعالجة …");

    try {
      const body = {
        model,
        messages: [
          ...(sys ? [{ role: "system", content: sys }] : []),
          ...state.messages
            .filter(m => m.role !== "assistant")
            .map(m => ({ role: m.role, content: m.content })),
          { role: "user", content: finalUser }
        ],
        stream: false
      };

      const res = await fetch(apiBase.replace(/\/+$/,"") + "/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { "Authorization": `Bearer ${apiKey}` } : {})
        },
        body: JSON.stringify(body)
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const reply = data.choices?.[0]?.message?.content || "لم يصل رد من النموذج.";
      state.messages.pop(); // remove placeholder
      appendMessage("assistant", reply);
    } catch (err) {
      console.error(err);
      state.messages.pop();
      appendMessage("assistant", "تعذر الحصول على رد. تحقق من OpenRouter / المفتاح / النموذج.");
    }
  }

  // ملف → تحويل إلى نص (base64 + وصف) لإرساله للوكيل
  function handleFileSelect(file) {
    if (!file) return;
    state.pendingFile = file;
    fileName.textContent = `${file.name} (${Math.round(file.size/1024)} KB)`;
  }

  async function processFile() {
    const file = state.pendingFile;
    if (!file) { showToast("اختر ملفاً أولاً"); return; }

    // هذه خطوة بسيطة: نأخذ Base64 + meta ونرسلها كرسالة نص
    // لاحقاً يمكن استبدالها بـ OCR/رؤية آلية على الخادم.
    const base64 = await fileToBase64(file);
    const summary = `ملف مرفوع:\nالاسم: ${file.name}\nالنوع: ${file.type}\nالحجم: ${file.size} bytes\nالمحتوى(Base64 مختصر): ${base64.slice(0, 120)}...`;
    await sendMessage(summary);
    showToast("أُرسل للوكيل");
    state.pendingFile = null;
    fileName.textContent = "";
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(",")[1]);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => toast.classList.add("hidden"), 2200);
  }

  btnSend.onclick = () => sendMessage();
  btnClear.onclick = () => { state.messages = []; saveState(); renderMessages(); showToast("تم مسح المحادثة"); };
  btnSettings.onclick = () => drawer.classList.remove("hidden");
  btnCloseSettings.onclick = () => drawer.classList.add("hidden");
  btnSaveSettings.onclick = () => {
    state.apiBase = apiBaseEl.value.trim() || "https://openrouter.ai/api/v1";
    state.apiKey = apiKeyEl.value.trim();
    state.model = modelEl.value.trim() || "qwen/qwen-2.5-72b-instruct";
    state.systemPrompt = systemPromptEl.value.trim();
    saveState();
    drawer.classList.add("hidden");
    showToast("تم الحفظ");
  };

  userInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  fileInput.addEventListener("change", e => handleFileSelect(e.target.files[0]));
  btnProcessFile.onclick = processFile;

  loadState();
})();
