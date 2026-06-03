import { useRef, useCallback } from "react";
import { Globe, Send } from "lucide-react";

const TONE_OPTIONS = [
  { value: "technical", label: "Technical" },
  { value: "balanced", label: "Balanced" },
  { value: "executive", label: "Executive" },
];

const ChatBox = ({ onSend, disabled, webSearch, onToggleWebSearch, tone, onToneChange }) => {
  const inputRef = useRef(null);

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

  return (
    <form className="chatbox-dock" onSubmit={handleSubmit}>
      <div className="chatbox-inner">
        <div className="chatbox-field">
          <textarea
            ref={inputRef}
            className="chatbox-input"
            placeholder="Ask about our projects, clients, capabilities, or request a pitch..."
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

        <div className="tone-selector" role="group" aria-label="Response tone">
          {TONE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={`tone-option${tone === opt.value ? " active" : ""}`}
              onClick={() => onToneChange(opt.value)}
              title={`Tone: ${opt.label}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
};

export default ChatBox;
