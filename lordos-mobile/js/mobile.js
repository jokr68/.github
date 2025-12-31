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
  const btnClearFile = document.getElementById("btnClearFile");
  const btnExportChat = document.getElementById("btnExportChat");
  const importChatInput = document.getElementById("importChatInput");
  const statusBadge = document.getElementById("statusBadge");

  const apiBaseEl = document.getElementById("apiBase");
  const apiKeyEl = document.getElementById("apiKey");
  const modelEl = document.getElementById("model");
  const systemPromptEl = document.getElementById("systemPrompt");
  const quickActions = Array.from(document.querySelectorAll(".quick-action"));

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
      updateStatusBadge();
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

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`خطأ في الاتصال بـ OpenRouter: ${res.status}`);
      }
      const data = await res.json();
      const reply = data.choices?.[0]?.message?.content || "لم يصل رد من النموذج.";
      state.messages.pop(); // remove placeholder
      appendMessage("assistant", reply);
    } catch (err) {
      console.error(err);
      state.messages.pop();
      const errorMsg = err.message || "تعذر الحصول على رد. تحقق من OpenRouter / المفتاح / النموذج.";
      appendMessage("assistant", errorMsg);
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

    // هذه خطوة بسيطة: نأخذ meta ونرسلها كرسالة نص
    // لاحقاً يمكن استبدالها بـ OCR/رؤية آلية على الخادم.
    const summary = `ملف مرفوع:\nالاسم: ${file.name}\nالنوع: ${file.type}\nالحجم: ${file.size} bytes\n\n(ملاحظة: معالجة المحتوى تتطلب خدمة OCR/رؤية آلية)`;
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

  function updateStatusBadge() {
    const hasApi = apiBaseEl.value.trim();
    const hasKey = apiKeyEl.value.trim();
    const hasModel = modelEl.value.trim();
    if (hasApi && hasKey && hasModel) {
      statusBadge.textContent = "جاهز للاتصال";
      statusBadge.classList.remove("warning");
      statusBadge.classList.add("success");
    } else {
      statusBadge.textContent = "تحقق من الإعدادات";
      statusBadge.classList.remove("success");
      statusBadge.classList.add("warning");
    }
  }

  function clearFileSelection() {
    state.pendingFile = null;
    fileName.textContent = "";
    fileInput.value = "";
  }

  function exportChat() {
    if (!state.messages.length) {
      showToast("لا توجد محادثة للتصدير");
      return;
    }
    const payload = {
      exportedAt: new Date().toISOString(),
      messages: state.messages
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `lordos-chat-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    showToast("تم تصدير المحادثة");
  }

  function importChat(file) {
    if (!file) return;
    // Limit file size to 5MB to prevent memory issues
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      showToast("الملف كبير جداً (الحد الأقصى 5MB)");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        if (!reader.result || typeof reader.result !== "string" || reader.result.trim() === "") {
          throw new Error("الملف فارغ أو غير قابل للقراءة");
        }
        const parsed = JSON.parse(reader.result);
        if (!Array.isArray(parsed.messages)) {
          throw new Error("صيغة غير صالحة");
        }
        const allowedRoles = ["user", "assistant", "system"];
        state.messages = parsed.messages.filter(m =>
          m &&
          typeof m === "object" &&
          allowedRoles.includes(m.role) &&
          typeof m.content === "string" &&
          m.content.length > 0
        );
        saveState();
        renderMessages();
        showToast("تم استيراد المحادثة");
      } catch (err) {
        console.error(err);
        showToast("تعذر استيراد الملف");
      }
    };
    reader.onerror = () => {
      console.error(reader.error);
      showToast("تعذر قراءة الملف");
    };
    reader.readAsText(file);
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
    updateStatusBadge();
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
  btnClearFile.onclick = clearFileSelection;
  btnExportChat.onclick = exportChat;
  importChatInput.addEventListener("change", e => importChat(e.target.files[0]));
  quickActions.forEach(btn => {
    btn.addEventListener("click", () => {
      userInput.value = btn.dataset.template;
      userInput.focus();
    });
  });

  loadState();
})();
