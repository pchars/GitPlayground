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
    const syntaxLiveTip = document.getElementById("syntax-live-tip");
    const recommendationsList = document.getElementById("task-recommendations");
    const terminalLogNode = document.getElementById("terminal-log-data");
    const initialTerminalLog = terminalLogNode ? JSON.parse(terminalLogNode.textContent || "\"\"") : "";
    const hintsDataNode = document.getElementById("task-hints-data");
    const hintsData = hintsDataNode ? JSON.parse(hintsDataNode.textContent || "[]") : [];
    const hintUiStateNode = document.getElementById("hint-ui-state-data");
    const hintUiState = hintUiStateNode
      ? JSON.parse(hintUiStateNode.textContent || "{}")
      : { revealed: [], next_hint_index: 1, exhausted: false, total: 0 };
    const syntaxHintsDataNode = document.getElementById("syntax-hints-data");
    const syntaxHints = syntaxHintsDataNode ? JSON.parse(syntaxHintsDataNode.textContent || "[]") : [];
    const recommendationsDataNode = document.getElementById("task-recommendations-data");
    const taskRecommendations = recommendationsDataNode
      ? JSON.parse(recommendationsDataNode.textContent || "[]")
      : [];
    const maxHints = hintsData.length;
    const commandHistory = [];
    let historyCursor = 0;
    let nextHintIndex = hintUiState.next_hint_index || 1;
    let commandBuffer = "";
    let isCommandRunning = false;
    const promptLabel = "user@gitplayground:~/repo$ ";
    let term = null;

    function createFallbackTerminal() {
      const output = document.createElement("pre");
      output.className = "terminal-log";
      const liveLine = document.createElement("div");
      liveLine.className = "terminal-live-line";
      liveLine.innerHTML = `<span class="terminal-prompt">${promptLabel}</span><span class="terminal-fallback-command"></span><span class="terminal-cursor">█</span>`;
      xtermHost.innerHTML = "";
      xtermHost.appendChild(output);
      xtermHost.appendChild(liveLine);
      const liveCommand = liveLine.querySelector(".terminal-fallback-command");
      let fallbackOnData = null;

      term = {
        write: (text) => {
          const value = String(text || "");
          if (!value) return;
          if (value === "\b \b") return;
          if (value.includes("\u001b[2K")) return;
          if (value.length === 1 && value >= " ") return;
          output.textContent += value.replace(/\r/g, "");
        },
        writeln: (text) => {
          output.textContent += `${String(text || "")}\n`;
        },
        clear: () => {
          output.textContent = "";
        },
        scrollToBottom: () => {
          terminalBody.scrollTop = terminalBody.scrollHeight;
        },
        focus: () => {
          terminalBody.focus();
        },
        onData: (handler) => {
          fallbackOnData = handler;
        },
        _setLiveCommand: (value) => {
          if (liveCommand) {
            liveCommand.textContent = value;
          }
        },
      };

      terminalBody.addEventListener("keydown", (event) => {
        if (!fallbackOnData) return;
        if (event.key === "Enter") {
          event.preventDefault();
          fallbackOnData("\r");
          return;
        }
        if (event.key === "Backspace") {
          event.preventDefault();
          fallbackOnData("\u007F");
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          fallbackOnData("\u001b[A");
          return;
        }
        if (event.key === "ArrowDown") {
          event.preventDefault();
          fallbackOnData("\u001b[B");
          return;
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "l") {
          event.preventDefault();
          fallbackOnData("\u000c");
          return;
        }
        if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
          event.preventDefault();
          fallbackOnData(event.key);
        }
      });
    }

    function xtermTheme() {
      return { background: "#ffffff", foreground: "#24292f", cursor: "#24292f" };
    }

    try {
      if (typeof window.Terminal === "function") {
        term = new window.Terminal({
          cursorBlink: true,
          theme: xtermTheme(),
          fontFamily: "\"JetBrains Mono\", \"Fira Code\", monospace",
          fontSize: 13,
          convertEol: true,
          scrollback: 2000,
        });
        term.open(xtermHost);
        const FitCtor = window.FitAddon && (window.FitAddon.FitAddon || window.FitAddon);
        if (typeof FitCtor === "function") {
          const fitAddon = new FitCtor();
          term.loadAddon(fitAddon);
          fitAddon.fit();
          window.addEventListener("resize", () => fitAddon.fit());
        }
      } else {
        createFallbackTerminal();
      }
    } catch (error) {
      createFallbackTerminal();
    }
    if (!term) {
      createFallbackTerminal();
    }

    function writePrompt() {
      term.write(`\r\n${promptLabel}`);
    }

    if (initialTerminalLog) {
      term.write(initialTerminalLog.replace(/\n/g, "\r\n"));
    }
    if (typeof term._setLiveCommand === "function") {
      term._setLiveCommand("");
    } else {
      term.write(`\r\n${promptLabel}`);
    }

    function scrollTerminalDown() {
      term.scrollToBottom();
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
      const total = hintUiState.total != null ? hintUiState.total : maxHints;
      if (!total) {
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

    function renderRecommendations() {
      if (!recommendationsList) {
        return;
      }
      recommendationsList.innerHTML = "";
      taskRecommendations.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        recommendationsList.appendChild(li);
      });
      if (!taskRecommendations.length) {
        const li = document.createElement("li");
        li.textContent = "Нет специальных рекомендаций для этой задачи.";
        recommendationsList.appendChild(li);
      }
    }

    function updateSyntaxHint(value) {
      if (!syntaxLiveTip) {
        return;
      }
      const input = (value || "").trim().toLowerCase();
      if (!input) {
        syntaxLiveTip.textContent = "Подсказка по синтаксису появится, когда вы начнете ввод команды.";
        return;
      }
      const match = syntaxHints.find((hint) => input.startsWith(hint.command.toLowerCase()));
      if (!match) {
        syntaxLiveTip.textContent = "Совет: начните с git status, чтобы увидеть текущее состояние.";
        return;
      }
      syntaxLiveTip.textContent = `${match.syntax} | Пример: ${match.example}`;
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

    function renderLocalHelp() {
      term.writeln("");
      term.writeln("GitPlayground help");
      term.writeln("----------------");
      term.writeln("Доступные команды:");
      term.writeln("  - git <...>");
      term.writeln("  - touch <file>");
      term.writeln("  - cat <file>   (только путь, без флагов)");
      term.writeln("  - type nul > <file>");
      term.writeln("  - echo <text> > <file>");
      term.writeln("  - echo <text> >> <file>");
      term.writeln("  - многострочный текст: блок «Редактор файла» под терминалом");
      term.writeln("");
      term.writeln("Горячие клавиши:");
      term.writeln("  - Enter: выполнить команду");
      term.writeln("  - ArrowUp / ArrowDown: история команд");
      term.writeln("  - Ctrl+L: очистить терминал");
      term.writeln("Локальная команда: help");
    }

    async function submitCommand(command) {
      if (!command || isCommandRunning) {
        return;
      }
      isCommandRunning = true;
      commandHistory.push(command);
      historyCursor = commandHistory.length;
      if (typeof term._setLiveCommand === "function") {
        term.writeln(`${promptLabel}${command}`);
        term._setLiveCommand("");
      }
      if (typeof term._setLiveCommand !== "function") {
        term.write("\r\n");
      }
      if (command.toLowerCase() === "help") {
        renderLocalHelp();
        writePrompt();
        isCommandRunning = false;
        scrollTerminalDown();
        return;
      }
      const data = await post(urls.run, { command });
      if (!data.ok) {
        validateOutput.textContent = data.message || "Command failed";
        validateOutput.className = "hint-box validate-banner validate-failed";
        term.writeln(`Error: ${data.message || "Command failed"}`);
        writePrompt();
        if (typeof term._setLiveCommand === "function") {
          term._setLiveCommand("");
        }
        isCommandRunning = false;
        return;
      }
      if (data.output) {
        term.writeln(data.output);
      }
      writePrompt();
      if (typeof term._setLiveCommand === "function") {
        term._setLiveCommand("");
      }
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
      validateOutput.textContent = `${data.verdict.toUpperCase()} (#${data.attempt_no}) - ${data.diagnostics || "No diagnostics"}`;
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
      if (data.ok) {
        validateOutput.textContent = "Песочница сброшена.";
        validateOutput.className = "hint-box validate-banner muted";
        term.clear();
        term.writeln("Песочница сброшена. Можно снова вводить команды Git.");
        writePrompt();
        if (typeof term._setLiveCommand === "function") {
          term._setLiveCommand("");
        }
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

    term.onData(async (dataChunk) => {
      if (dataChunk === "\r") {
        const command = commandBuffer.trim();
        commandBuffer = "";
        updateSyntaxHint("");
        await submitCommand(command);
        return;
      }
      if (dataChunk === "\u007F") {
        if (commandBuffer.length > 0) {
          commandBuffer = commandBuffer.slice(0, -1);
          term.write("\b \b");
          if (typeof term._setLiveCommand === "function") {
            term._setLiveCommand(commandBuffer);
          }
          updateSyntaxHint(commandBuffer);
        }
        return;
      }
      if (dataChunk === "\u001b[A") {
        if (!commandHistory.length) {
          return;
        }
        historyCursor = Math.max(0, historyCursor - 1);
        commandBuffer = commandHistory[historyCursor] || "";
        term.write("\u001b[2K\r" + promptLabel + commandBuffer);
        if (typeof term._setLiveCommand === "function") {
          term._setLiveCommand(commandBuffer);
        }
        updateSyntaxHint(commandBuffer);
        return;
      }
      if (dataChunk === "\u001b[B") {
        if (!commandHistory.length) {
          return;
        }
        historyCursor = Math.min(commandHistory.length, historyCursor + 1);
        commandBuffer = commandHistory[historyCursor] || "";
        term.write("\u001b[2K\r" + promptLabel + commandBuffer);
        if (typeof term._setLiveCommand === "function") {
          term._setLiveCommand(commandBuffer);
        }
        updateSyntaxHint(commandBuffer);
        return;
      }
      if (dataChunk === "\u000c") {
        term.clear();
        commandBuffer = "";
        writePrompt();
        if (typeof term._setLiveCommand === "function") {
          term._setLiveCommand("");
        }
        updateSyntaxHint("");
        return;
      }
      if (dataChunk.length === 1 && dataChunk >= " ") {
        commandBuffer += dataChunk;
        term.write(dataChunk);
        if (typeof term._setLiveCommand === "function") {
          term._setLiveCommand(commandBuffer);
        }
        updateSyntaxHint(commandBuffer);
      }
    });

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
      });
    });

    const fileEditorPath = document.getElementById("file-editor-path");
    const fileEditorBody = document.getElementById("file-editor-body");
    const fileEditorLoad = document.getElementById("file-editor-load");
    const fileEditorSave = document.getElementById("file-editor-save");
    const fileEditorStatus = document.getElementById("file-editor-status");

    function setFileEditorStatus(text, isError) {
      if (!fileEditorStatus) {
        return;
      }
      fileEditorStatus.textContent = text || "";
      fileEditorStatus.style.color = isError ? "var(--danger)" : "";
    }

    async function loadRepoFile() {
      const path = (fileEditorPath && fileEditorPath.value) ? fileEditorPath.value.trim() : "";
      if (!path) {
        setFileEditorStatus("Укажите путь к файлу.", true);
        return;
      }
      const url = new URL(urls.readFile, window.location.origin);
      url.searchParams.set("path", path);
      const response = await fetch(url.toString(), { method: "GET", credentials: "same-origin" });
      const data = await response.json();
      if (!data.ok) {
        setFileEditorStatus(data.message || "Ошибка чтения", true);
        return;
      }
      if (fileEditorBody) {
        fileEditorBody.value = data.content != null ? data.content : "";
      }
      setFileEditorStatus(data.truncated ? "Загружено (файл обрезан по лимиту песочницы)." : "Загружено.");
    }

    async function saveRepoFile() {
      const path = (fileEditorPath && fileEditorPath.value) ? fileEditorPath.value.trim() : "";
      const body = fileEditorBody ? fileEditorBody.value : "";
      if (!path) {
        setFileEditorStatus("Укажите путь к файлу.", true);
        return;
      }
      const data = await post(urls.writeFile, { path, content: body });
      if (!data.ok) {
        setFileEditorStatus(data.message || "Ошибка записи", true);
        return;
      }
      setFileEditorStatus(`Сохранено (${data.bytes_written != null ? data.bytes_written : 0} байт).`);
    }

    if (fileEditorLoad) {
      fileEditorLoad.addEventListener("click", () => {
        loadRepoFile().catch(() => setFileEditorStatus("Сбой сети.", true));
      });
    }
    if (fileEditorSave) {
      fileEditorSave.addEventListener("click", () => {
        saveRepoFile().catch(() => setFileEditorStatus("Сбой сети.", true));
      });
    }

    renderRecommendations();
    updateSyntaxHint("");
    hydrateHintsFromServer();
    if (maxHints === 0) {
      hintBtn.disabled = true;
      if (!hintOutput.textContent) {
        hintOutput.textContent = "Для этой задачи подсказки не настроены.";
      }
    } else if (hintUiState.exhausted) {
      hintBtn.disabled = true;
    }
    term.focus();
    terminalBody.addEventListener("click", () => term.focus());
  })();
