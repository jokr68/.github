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

  // دالة منفصلة لإرسال رسائل مع صور
  async function sendMessageWithImage(textContent, imageMessage) {
    const apiBase = state.apiBase.trim();
    const apiKey = state.apiKey.trim();
    const model = state.model.trim();
    const sys = state.systemPrompt.trim();

    if (!apiBase || !model) {
      showToast("ضبط الإعدادات أولاً: API Base و Model");
      return;
    }

    appendMessage("assistant", "… جارٍ تحليل الصورة …");

    try {
      const body = {
        model,
        messages: [
          ...(sys ? [{ role: "system", content: sys }] : []),
          ...state.messages
            .filter(m => m.role !== "assistant")
            .map(m => ({ role: m.role, content: m.content })),
          { 
            role: "user", 
            content: [
              { type: "text", text: textContent },
              imageMessage
            ]
          }
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

    showToast("جارٍ معالجة الملف...");

    // للصور: نرسل base64 مباشرة إذا كان النموذج يدعم الرؤية
    if (file.type.startsWith('image/')) {
      try {
        const base64 = await fileToBase64(file);
        const imageMessage = {
          type: "image_url",
          image_url: {
            url: `data:${file.type};base64,${base64}`
          }
        };
        const summary = `[صورة مرفقة: ${file.name}]\nيرجى تحليل هذه الصورة وشرح محتواها.`;
        await sendMessageWithImage(summary, imageMessage);
        showToast("تم إرسال الصورة للوكيل");
      } catch (err) {
        console.error(err);
        showToast("خطأ في معالجة الصورة");
      }
    } else if (file.type === 'application/pdf') {
      // للـ PDF: نرسل metadata فقط (يحتاج لمعالجة خارجية)
      const summary = `ملف PDF مرفوع:\nالاسم: ${file.name}\nالحجم: ${Math.round(file.size/1024)} KB\n\n(ملاحظة: استخراج نص PDF يتطلب معالجة خارجية)`;
      await sendMessage(summary);
      showToast("أُرسل معلومات الملف للوكيل");
    } else {
      // أنواع أخرى
      const summary = `ملف مرفوع:\nالاسم: ${file.name}\nالنوع: ${file.type}\nالحجم: ${file.size} bytes`;
      await sendMessage(summary);
      showToast("أُرسل معلومات الملف للوكيل");
    }

    state.pendingFile = null;
    fileName.textContent = "";
    fileInput.value = "";
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
    const hasModel = modelEl.value.trim();
    if (hasApi && hasModel) {
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
    showToast("تم مسح الملف");
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
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `lordos-chat-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    URL.revokeObjectURL(link.href);
    link.remove();
    showToast("تم تصدير المحادثة");
  }

  function importChat(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        if (!Array.isArray(parsed.messages)) {
          throw new Error("صيغة غير صالحة");
        }
        state.messages = parsed.messages.filter(m => m && m.role && m.content && ["user", "assistant", "system"].includes(m.role));
        saveState();
        renderMessages();
        showToast("تم استيراد المحادثة");
      } catch (err) {
        console.error(err);
        showToast("تعذر استيراد الملف");
      }
    };
    reader.readAsText(file);
  }

  btnSend.onclick = () => sendMessage();
  btnClear.onclick = () => { state.messages = []; saveState(); renderMessages(); showToast("تم مسح المحادثة"); };
  btnSettings.onclick = () => drawer.classList.remove("hidden");
  btnCloseSettings.onclick = () => drawer.classList.add("hidden");
  btnSaveSettings.onclick = () => {
    const apiBaseValue = apiBaseEl.value.trim();
    const modelValue = modelEl.value.trim();
    
    // التحقق من صيغة API Base
    if (apiBaseValue && !apiBaseValue.startsWith('http')) {
      showToast("خطأ: API Base يجب أن يبدأ بـ http أو https");
      return;
    }
    
    // التحقق من وجود النموذج
    if (!modelValue) {
      showToast("خطأ: يجب إدخال اسم النموذج");
      return;
    }
    
    state.apiBase = apiBaseValue || "https://openrouter.ai/api/v1";
    state.apiKey = apiKeyEl.value.trim();
    state.model = modelValue;
    state.systemPrompt = systemPromptEl.value.trim();
    saveState();
    updateStatusBadge();
    drawer.classList.add("hidden");
    showToast("تم الحفظ ✓");
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
