(function () {
  const csrfInput = document.querySelector("#csrf-holder input[name=csrfmiddlewaretoken]");
  const csrf = csrfInput ? csrfInput.value : "";
  const urls = (window.__GP_PLAYGROUND__ && window.__GP_PLAYGROUND__.urls) || {};
  const terminalBody = document.getElementById("terminal-body");
  const xtermHost = document.getElementById("xterm-host");
  const validateBtn = document.getElementById("validate-btn");
  const resetBtn = document.getElementById("reset-btn");
  const hintBtn = document.getElementById("hint-btn");
  const validateOutput = document.getElementById("validate-output");
  const hintOutput = document.getElementById("hint-output");
  const hintUiStateNode = document.getElementById("hint-ui-state-data");
  const hintUiState = hintUiStateNode
    ? JSON.parse(hintUiStateNode.textContent || "{}")
    : { revealed: [], next_hint_index: 1, exhausted: false, total: 0 };
  const maxHints = hintUiState.total != null ? hintUiState.total : 0;
  const commandHistory = [];
  let historyCursor = 0;
  let nextHintIndex = hintUiState.next_hint_index || 1;
  let commandBuffer = "";
  let cursorPos = 0;
  let isCommandRunning = false;
  let isNanoOpen = false;
  const promptLabel = window.GPTerminalPaste.PROMPT;
  const PROMPT_ANSI = "\u001b[1;32muser@gitplayground:~/repo$\u001b[0m ";
  let term = null;
  let fitAddon = null;
  let lastPasteAt = 0;

  function isLikelyPasteChunk(chunk) {
    const value = String(chunk || "");
    return value.includes("\n")
      || value.includes("\r")
      || value.includes("\x1b")
      || value.includes(promptLabel);
  }

  function extractBracketedPaste(chunk) {
    const match = String(chunk || "").match(/\x1b\[200~([\s\S]*?)\x1b\[201~/);
    return match ? match[1] : null;
  }

  function clampCursor() {
    if (cursorPos < 0) cursorPos = 0;
    if (cursorPos > commandBuffer.length) cursorPos = commandBuffer.length;
  }

  function rewriteInputLine() {
    clampCursor();
    term.write("\u001b[2K\r" + PROMPT_ANSI + commandBuffer);
    const back = commandBuffer.length - cursorPos;
    if (back > 0) {
      term.write("\u001b[" + back + "D");
    }
  }

  function insertAtCursor(text) {
    commandBuffer = commandBuffer.slice(0, cursorPos) + text + commandBuffer.slice(cursorPos);
    cursorPos += text.length;
    rewriteInputLine();
  }

  function applyPaste(raw) {
    const now = Date.now();
    if (now - lastPasteAt < 80) {
      return;
    }
    lastPasteAt = now;
    const chunk = window.GPTerminalPaste.sanitizeTerminalPaste(raw);
    if (!chunk || isCommandRunning) {
      return;
    }
    insertAtCursor(chunk);
  }

  function writePrompt() {
    term.write(`\r\n${PROMPT_ANSI}`);
  }

  function renderLocalHelp() {
    term.writeln("");
    term.writeln("Справка GitPlayground");
    term.writeln("----------------");
    term.writeln("Доступные команды:");
    term.writeln("  - git <...>");
    term.writeln("  - ls [путь], pwd, mkdir [-p] <папка>, find [путь]");
    term.writeln("  - touch <файл>, cat/head/tail/wc <файл>, cp/mv <откуда> <куда>, rm <файл>");
    term.writeln("  - echo <текст>  |  echo <текст> > <файл>  |  echo <текст> >> <файл>");
    term.writeln("  - type nul > <файл>");
    term.writeln("  - nano <файл>  |  edit <файл>  — редактор поверх терминала");
    term.writeln("  - whoami, clear");
    term.writeln("");
    term.writeln("Режим nano/edit:");
    term.writeln("  - Ctrl+S / Ctrl+O — сохранить");
    term.writeln("  - Ctrl+X — выйти в командную строку");
    term.writeln("  - Ctrl+V / Cmd+V — вставить в редактор");
    term.writeln("");
    term.writeln("Терминал:");
    term.writeln("  - Enter — выполнить команду");
    term.writeln("  - ArrowUp / ArrowDown — история");
    term.writeln("  - Ctrl+L / clear — очистить экран");
    term.writeln("  - Ctrl+V / Cmd+V — вставить в строку");
    term.writeln("  - Ctrl+C — копировать выделение");
    term.writeln("Локальная команда: help");
  }

  function showInitialTerminalWelcome() {
    term.write(PROMPT_ANSI + "help");
    renderLocalHelp();
    writePrompt();
    scrollTerminalDown();
  }

  function showTerminalUnavailable() {
    xtermHost.innerHTML = '<p class="xterm-unavailable muted">Терминал недоступен. Перезагрузите страницу.</p>';
  }

  function xtermTheme() {
    const root = getComputedStyle(document.documentElement);
    const background = root.getPropertyValue("--bg-terminal").trim() || "#ffffff";
    const foreground = root.getPropertyValue("--color-ink").trim() || "#24292f";
    const selectionBackground =
      root.getPropertyValue("--terminal-selection-bg").trim() || "rgba(17, 17, 17, 0.28)";
    const selectionInactiveBackground =
      root.getPropertyValue("--terminal-selection-inactive-bg").trim() || "rgba(17, 17, 17, 0.16)";
    return {
      background,
      foreground,
      cursor: foreground,
      selectionBackground,
      selectionForeground: foreground,
      selectionInactiveBackground,
    };
  }

  if (typeof window.Terminal === "function") {
    try {
      term = new window.Terminal({
        cursorBlink: true,
        theme: xtermTheme(),
        fontFamily: "\"JetBrains Mono\", \"Fira Code\", monospace",
        fontSize: 13,
        convertEol: true,
        scrollback: 2000,
        allowTransparency: false,
      });
      term.open(xtermHost);
      term.attachCustomKeyEventHandler((event) => {
        if (event.type !== "keydown") {
          return true;
        }
        if (isNanoOpen && nanoBody && document.activeElement === nanoBody) {
          return true;
        }
        const key = event.key.toLowerCase();
        if ((event.ctrlKey || event.metaKey) && !event.shiftKey && key === "v") {
          event.preventDefault();
          if (navigator.clipboard && typeof navigator.clipboard.readText === "function") {
            navigator.clipboard.readText().then((text) => {
              if (isNanoOpen && nanoBody) {
                insertTextAtSelection(nanoBody, text);
                focusWithoutScroll(nanoBody);
                return;
              }
              applyPaste(text);
            }).catch(() => {});
          }
          return false;
        }
        if ((event.ctrlKey || event.metaKey) && !event.shiftKey && key === "c" && term.hasSelection()) {
          event.preventDefault();
          const selected = term.getSelection();
          if (selected && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
            navigator.clipboard.writeText(selected).catch(() => {});
          }
          return false;
        }
        return true;
      });
      const FitCtor = window.FitAddon && (window.FitAddon.FitAddon || window.FitAddon);
      if (typeof FitCtor === "function") {
        fitAddon = new FitCtor();
        term.loadAddon(fitAddon);
        fitAddon.fit();
        window.addEventListener("resize", () => fitAddon.fit());
      }
      showInitialTerminalWelcome();
    } catch (error) {
      term = null;
    }
  }

  if (!term) {
    showTerminalUnavailable();
  }

  function scrollTerminalDown() {
    if (term) {
      term.scrollToBottom();
    }
  }

  function renderHintBlock(index, content, pointsSpent) {
    const wrap = document.createElement("div");
    wrap.className = "hint-reveal-block";
    const title = document.createElement("p");
    const spent = pointsSpent ? ` (списано ${pointsSpent} баллов)` : "";
    title.textContent = `Подсказка ${index}${spent}`;
    const body = document.createElement("p");
    body.textContent = content;
    wrap.appendChild(title);
    wrap.appendChild(body);
    hintOutput.appendChild(wrap);
  }

  function hydrateHintsFromServer() {
    hintOutput.innerHTML = "";
    if (!maxHints) {
      hintOutput.textContent = "Для этой задачи подсказки не настроены.";
      return;
    }
    const revealed = hintUiState.revealed || [];
    if (!revealed.length) {
      hintOutput.textContent = "Подсказки пока не открыты.";
      return;
    }
    revealed.forEach((row) => {
      renderHintBlock(row.index, row.content, row.points_spent);
    });
  }

  async function post(url, payload) {
    const body = new URLSearchParams(payload);
    const response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    return response.json();
  }

  const nanoOverlay = document.getElementById("nano-overlay");
  const nanoPathEl = document.getElementById("nano-overlay-path");
  const nanoBody = document.getElementById("nano-overlay-body");
  const nanoStatus = document.getElementById("nano-overlay-status");
  let nanoCurrentPath = "";

  function focusWithoutScroll(node) {
    if (!node || typeof node.focus !== "function") {
      return;
    }
    try {
      node.focus({ preventScroll: true });
    } catch (_error) {
      node.focus();
    }
  }

  function setNanoStatus(text, isError) {
    if (!nanoStatus) {
      return;
    }
    nanoStatus.textContent = text || "";
    nanoStatus.classList.toggle("nano-overlay__status--error", Boolean(isError));
  }

  function ensureTerminalTabVisible() {
    const terminalTab = document.querySelector('.tab-btn[data-tab="terminal"]');
    if (terminalTab && !terminalTab.classList.contains("active")) {
      terminalTab.click();
    }
  }

  function focusTerminal() {
    if (!term) {
      return;
    }
    if (typeof term.focus === "function") {
      term.focus();
      return;
    }
    focusWithoutScroll(term.element || term.textarea || terminalBody);
  }

  function refocusTerminalAfterNano() {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        focusTerminal();
        if (terminalBody && typeof terminalBody.focus === "function") {
          terminalBody.focus();
        }
        if (term && term.textarea && typeof term.textarea.focus === "function") {
          term.textarea.focus();
        }
      });
    });
  }

  function closeNanoEditor(message) {
    isNanoOpen = false;
    nanoCurrentPath = "";
    if (nanoOverlay) {
      nanoOverlay.classList.remove("nano-overlay--open");
      nanoOverlay.hidden = true;
      nanoOverlay.setAttribute("aria-hidden", "true");
    }
    if (term) {
      if (message) {
        term.writeln(message);
        writePrompt();
        scrollTerminalDown();
      }
      refocusTerminalAfterNano();
    }
  }

  async function readRepoFileContent(path) {
    const url = new URL(urls.readFile, window.location.origin);
    url.searchParams.set("path", path);
    const response = await fetch(url.toString(), { method: "GET", credentials: "same-origin" });
    return response.json();
  }

  async function saveNanoFile() {
    const path = nanoCurrentPath;
    const content = nanoBody ? nanoBody.value : "";
    if (!path) {
      setNanoStatus("Не указан путь к файлу.", true);
      return false;
    }
    const data = await post(urls.writeFile, { path, content });
    if (!data.ok) {
      setNanoStatus(data.message || "Ошибка записи", true);
      return false;
    }
    setNanoStatus(`Записано ${data.bytes_written != null ? data.bytes_written : 0} байт. ^X — выйти`);
    return true;
  }

  async function openNanoEditor(path) {
    if (!nanoOverlay || !nanoBody) {
      return;
    }
    ensureTerminalTabVisible();
    isNanoOpen = true;
    nanoCurrentPath = path;
    if (nanoPathEl) {
      nanoPathEl.textContent = path;
    }
    nanoOverlay.hidden = false;
    nanoOverlay.setAttribute("aria-hidden", "false");
    nanoOverlay.classList.add("nano-overlay--open");
    setNanoStatus("Загрузка…");
    try {
      const data = await readRepoFileContent(path);
      if (data.ok) {
        nanoBody.value = data.content != null ? data.content : "";
        setNanoStatus(
          data.truncated
            ? "Файл обрезан по лимиту. ^S сохранить · ^X выйти"
            : "^S сохранить · ^O записать · ^X выйти"
        );
      } else {
        nanoBody.value = "";
        setNanoStatus("Новый файл. ^S сохранить · ^X выйти");
      }
    } catch (_error) {
      nanoBody.value = "";
      setNanoStatus("Не удалось загрузить файл.", true);
    }
    focusWithoutScroll(nanoBody);
  }

  function handleNanoShortcuts(event) {
    if (!isNanoOpen) {
      return;
    }
    if (!event.ctrlKey && !event.metaKey) {
      return;
    }
    const key = event.key.toLowerCase();
    if (key === "s" || key === "o") {
      event.preventDefault();
      saveNanoFile().catch(() => setNanoStatus("Сбой сети.", true));
      return;
    }
    if (key === "x") {
      event.preventDefault();
      closeNanoEditor(`[ Закрыт редактор: ${nanoCurrentPath} ]`);
    }
  }

  function parseEditorCommand(command) {
    const match = /^(nano|edit)\s+(\S+)$/i.exec(String(command || "").trim());
    return match ? match[2] : null;
  }

  function insertTextAtSelection(textarea, text) {
    if (!textarea || text == null) {
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    textarea.value = value.slice(0, start) + text + value.slice(end);
    const pos = start + text.length;
    textarea.selectionStart = pos;
    textarea.selectionEnd = pos;
  }

  function handleTerminalPaste(event) {
    if (isNanoOpen && nanoBody && (event.target === nanoBody || (nanoOverlay && nanoOverlay.contains(event.target)))) {
      return;
    }
    const pasted = event.clipboardData && event.clipboardData.getData("text");
    if (!pasted) {
      return;
    }
    event.preventDefault();
    applyPaste(pasted);
  }

  function handleNanoPaste(event) {
    if (!isNanoOpen || !nanoBody) {
      return;
    }
    const pasted = event.clipboardData && event.clipboardData.getData("text");
    if (!pasted) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    insertTextAtSelection(nanoBody, pasted);
  }

  async function submitCommand(command) {
    if (!term || !command || isCommandRunning) {
      return;
    }
    isCommandRunning = true;
    commandHistory.push(command);
    historyCursor = commandHistory.length;
    term.write("\r\n");
    if (command.toLowerCase() === "help") {
      renderLocalHelp();
      writePrompt();
      isCommandRunning = false;
      scrollTerminalDown();
      return;
    }
    const isClear = command.trim().toLowerCase() === "clear";
    const editorPath = !isClear ? parseEditorCommand(command) : null;
    const data = await post(urls.run, { command });
    if (!data.ok) {
      validateOutput.textContent = data.message || "Команда не выполнена";
      validateOutput.className = "hint-box validate-banner validate-failed";
      term.writeln(`Ошибка: ${data.message || "Команда не выполнена"}`);
      writePrompt();
      isCommandRunning = false;
      return;
    }
    if (isClear) {
      term.clear();
      writePrompt();
      isCommandRunning = false;
      scrollTerminalDown();
      return;
    }
    const editorPathAfterRun = editorPath ?? parseEditorCommand(command);
    if (editorPathAfterRun) {
      term.writeln(`[ Открыт редактор: ${editorPathAfterRun} ]`);
      await openNanoEditor(editorPathAfterRun);
      isCommandRunning = false;
      scrollTerminalDown();
      return;
    }
    if (data.output) {
      term.writeln(data.output);
    }
    writePrompt();
    isCommandRunning = false;
    scrollTerminalDown();
  }

  validateBtn.addEventListener("click", async function () {
    validateOutput.textContent = "Проверка...";
    validateOutput.className = "hint-box validate-banner muted";
    const data = await post(urls.validate, {});
    if (!data.ok) {
      validateOutput.textContent = data.message || "Ошибка проверки";
      validateOutput.className = "hint-box validate-banner validate-failed";
      return;
    }
    if (data.verdict === "passed") {
      validateOutput.textContent = "Успешно";
    } else {
      const details = data.diagnostics ? `: ${data.diagnostics}` : "";
      validateOutput.textContent = `Не прошло (попытка #${data.attempt_no})${details}`;
    }
    validateOutput.className = data.verdict === "passed"
      ? "hint-box validate-banner validate-passed"
      : "hint-box validate-banner validate-failed";
    if (Array.isArray(data.awarded_achievements) && data.awarded_achievements.length && window.gitplaygroundToast) {
      data.awarded_achievements.forEach((achievement, index) => {
        window.setTimeout(() => {
          window.gitplaygroundToast({ tags: "achievement", achievement });
        }, index * 180);
      });
    }
    if (data.verdict === "passed" && data.next_task_route_id) {
      setTimeout(() => {
        window.location.href = `/playground/${data.next_task_route_id}/`;
      }, 1200);
    }
  });

  resetBtn.addEventListener("click", async function () {
    const data = await post(urls.reset, {});
    if (!data.ok) {
      return;
    }
    validateOutput.textContent = "Песочница сброшена.";
    validateOutput.className = "hint-box validate-banner muted";
    if (term) {
      closeNanoEditor();
      term.clear();
      term.writeln("Песочница сброшена. Можно снова вводить команды Git.");
      commandBuffer = "";
      cursorPos = 0;
      writePrompt();
    }
  });

  hintBtn.addEventListener("click", async function () {
    if (nextHintIndex > maxHints || hintUiState.exhausted) {
      hintOutput.textContent = "Подсказки закончились.";
      hintBtn.disabled = true;
      return;
    }
    const data = await post(urls.hint, { hint_index: nextHintIndex });
    if (!data.ok) {
      const msg = data.message || "Не удалось открыть подсказку.";
      hintOutput.querySelectorAll(".hint-error").forEach((n) => n.remove());
      const err = document.createElement("p");
      err.className = "hint-error";
      err.textContent = msg;
      hintOutput.appendChild(err);
      if (data.message && data.message.includes("закончились")) {
        hintBtn.disabled = true;
      }
      return;
    }
    if (hintOutput.querySelector(".hint-error")) {
      hintOutput.querySelectorAll(".hint-error").forEach((n) => n.remove());
    }
    if (hintOutput.textContent === "Подсказки пока не открыты.") {
      hintOutput.innerHTML = "";
    }
    if (!data.already_unlocked) {
      renderHintBlock(data.hint_index, data.content, data.points_spent);
    }
    nextHintIndex = data.next_hint_index != null ? data.next_hint_index : nextHintIndex + 1;
    if (data.hints_exhausted) {
      hintBtn.disabled = true;
    }
  });

  function setBufferFromHistory(value) {
    commandBuffer = value;
    cursorPos = commandBuffer.length;
    rewriteInputLine();
  }

  if (term) {
    term.onData(async (dataChunk) => {
      if (isNanoOpen) {
        return;
      }
      if (dataChunk === "\r") {
        const command = commandBuffer.trim();
        commandBuffer = "";
        cursorPos = 0;
        await submitCommand(command);
        return;
      }
      if (dataChunk === "\u007F" || dataChunk === "\b") {
        if (cursorPos > 0) {
          commandBuffer = commandBuffer.slice(0, cursorPos - 1) + commandBuffer.slice(cursorPos);
          cursorPos -= 1;
          rewriteInputLine();
        }
        return;
      }
      if (dataChunk === "\u001b[3~") {
        if (cursorPos < commandBuffer.length) {
          commandBuffer = commandBuffer.slice(0, cursorPos) + commandBuffer.slice(cursorPos + 1);
          rewriteInputLine();
        }
        return;
      }
      if (dataChunk === "\u001b[D") {
        if (cursorPos > 0) {
          cursorPos -= 1;
          rewriteInputLine();
        }
        return;
      }
      if (dataChunk === "\u001b[C") {
        if (cursorPos < commandBuffer.length) {
          cursorPos += 1;
          rewriteInputLine();
        }
        return;
      }
      if (dataChunk === "\u001b[H" || dataChunk === "\u001b[1~" || dataChunk === "\u0001") {
        cursorPos = 0;
        rewriteInputLine();
        return;
      }
      if (dataChunk === "\u001b[F" || dataChunk === "\u001b[4~" || dataChunk === "\u0005") {
        cursorPos = commandBuffer.length;
        rewriteInputLine();
        return;
      }
      if (dataChunk === "\u001b[A") {
        if (!commandHistory.length) {
          return;
        }
        historyCursor = Math.max(0, historyCursor - 1);
        setBufferFromHistory(commandHistory[historyCursor] || "");
        return;
      }
      if (dataChunk === "\u001b[B") {
        if (!commandHistory.length) {
          return;
        }
        historyCursor = Math.min(commandHistory.length, historyCursor + 1);
        setBufferFromHistory(commandHistory[historyCursor] || "");
        return;
      }
      if (dataChunk === "\u000c") {
        void submitCommand("clear");
        return;
      }
      if (dataChunk.length > 1) {
        const bracketed = extractBracketedPaste(dataChunk);
        if (bracketed !== null || isLikelyPasteChunk(dataChunk)) {
          applyPaste(bracketed !== null ? bracketed : dataChunk);
        }
        return;
      }
      if (dataChunk.length === 1 && dataChunk >= " ") {
        insertAtCursor(dataChunk);
      }
    });

    term.focus();
    terminalBody.addEventListener("click", () => {
      if (isNanoOpen) {
        focusWithoutScroll(nanoBody);
        return;
      }
      term.focus();
    });
    terminalBody.addEventListener("paste", handleTerminalPaste);
  }

  if (nanoBody) {
    nanoBody.addEventListener("keydown", handleNanoShortcuts);
    nanoBody.addEventListener("paste", handleNanoPaste);
  }

  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");
  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      tabButtons.forEach((x) => {
        x.classList.remove("active");
        x.setAttribute("aria-selected", "false");
      });
      tabPanels.forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      const panel = document.querySelector(`[data-panel="${target}"]`);
      if (panel) panel.classList.add("active");
      if (fitAddon && target === "terminal") {
        requestAnimationFrame(() => fitAddon.fit());
      }
    });
  });

  hydrateHintsFromServer();
  if (maxHints === 0) {
    hintBtn.disabled = true;
    if (!hintOutput.textContent) {
      hintOutput.textContent = "Для этой задачи подсказки не настроены.";
    }
  } else if (hintUiState.exhausted) {
    hintBtn.disabled = true;
  }
})();
