(function (global) {
  const PROMPT = "user@gitplayground:~/repo$ ";
  const ANSI_ESCAPE = /\x1b\[[0-9;]*[A-Za-z]/g;
  const CONTROL_CHARS = /[\x00-\x1f\x7f]/g;

  function sanitizeTerminalPaste(text) {
    let cleaned = String(text || "").replace(ANSI_ESCAPE, "");
    cleaned = cleaned.split(PROMPT).join("");
    const lines = cleaned.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i].replace(CONTROL_CHARS, "").trim();
      if (line) {
        return line;
      }
    }
    return cleaned.replace(CONTROL_CHARS, "").trim();
  }

  global.GPTerminalPaste = { PROMPT, sanitizeTerminalPaste };
})(typeof window !== "undefined" ? window : globalThis);
