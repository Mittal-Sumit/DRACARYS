import { useRef, useCallback, forwardRef, useImperativeHandle } from "react";
import { Globe, Send } from "lucide-react";

const MODE_OPTIONS = [
  { value: "ask",      label: "Ask",      title: "Direct answers — facts, experience, capabilities" },
  { value: "pitch",    label: "Pitch",    title: "Sales meeting prep — sections the sales person can speak from" },
  { value: "proposal", label: "Proposal", title: "Formal written document — sendable to the client" },
];

const AUDIENCE_OPTIONS = [
  { value: "general",   label: "General" },
  { value: "executive", label: "Executive" },
  { value: "technical", label: "Technical" },
];

// Derive the logical mode and audience from the raw tone value
const parseTone = (tone) => {
  if (tone === "ask")            return { mode: "ask",      audience: "general" };
  if (tone === "proposal")       return { mode: "proposal", audience: "general" };
  if (tone === "pitch_executive") return { mode: "pitch",   audience: "executive" };
  if (tone === "pitch_technical") return { mode: "pitch",   audience: "technical" };
  return { mode: "pitch", audience: "general" };
};

const buildTone = (mode, audience) => {
  if (mode === "ask")      return "ask";
  if (mode === "proposal") return "proposal";
  if (audience === "executive") return "pitch_executive";
  if (audience === "technical") return "pitch_technical";
  return "pitch";
};

const ChatBox = forwardRef(({ onSend, disabled, webSearch, onToggleWebSearch, tone, onToneChange }, ref) => {
  const inputRef = useRef(null);
  const { mode, audience } = parseTone(tone);

  useImperativeHandle(ref, () => ({
    fillInput(text) {
      if (!inputRef.current) return;
      inputRef.current.value = text;
      inputRef.current.style.height = "";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
      inputRef.current.focus();
    },
  }));

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      const value = inputRef.current?.value.trim();
      if (!value || disabled) return;
      onSend(value);
      inputRef.current.value = "";
      inputRef.current.style.height = "auto";
    },
    [onSend, disabled]
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
      }
    },
    [handleSubmit]
  );

  const handleInput = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, []);

  const handleModeChange = (newMode) => {
    onToneChange(buildTone(newMode, audience));
  };

  const handleAudienceChange = (newAudience) => {
    onToneChange(buildTone("pitch", newAudience));
  };

  return (
    <form className="chatbox-dock" onSubmit={handleSubmit}>
      <div className="chatbox-inner">
        <div className="chatbox-field">
          <textarea
            ref={inputRef}
            className="chatbox-input"
            placeholder={
              mode === "ask"      ? "Ask about our projects, clients, capabilities, or team..." :
              mode === "proposal" ? "Describe the client and engagement for the proposal..." :
                                   "Describe the client and their challenge..."
            }
            disabled={disabled}
            autoFocus
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            aria-label="Ask Dracarys"
          />
        </div>

        <button
          className="chatbox-send"
          type="submit"
          disabled={disabled}
          aria-label="Send message"
        >
          <Send size={20} />
        </button>
      </div>

      <div className="chatbox-toolbar">
        <button
          type="button"
          className={`web-toggle${webSearch ? " active" : ""}`}
          onClick={() => onToggleWebSearch(!webSearch)}
          title={webSearch ? "Web search on — click to disable" : "Web search off — click to enable"}
        >
          <Globe size={12} />
          {webSearch ? "Web on" : "Web search"}
        </button>

        <div className="mode-selector" role="group" aria-label="Response mode">
          {MODE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`mode-option${mode === opt.value ? " active" : ""}`}
              onClick={() => handleModeChange(opt.value)}
              title={opt.title}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {mode === "pitch" && (
        <div className="chatbox-audience-row">
          <span className="audience-label">Audience</span>
          <div className="audience-selector" role="group" aria-label="Pitch audience">
            {AUDIENCE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`audience-option${audience === opt.value ? " active" : ""}`}
                onClick={() => handleAudienceChange(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </form>
  );
});

export default ChatBox;
