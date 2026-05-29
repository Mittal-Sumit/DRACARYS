import { useRef, useCallback } from "react";
import { Globe, Plus, Send } from "lucide-react";

const ChatBox = ({ onSend, disabled, webSearch, onToggleWebSearch }) => {
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
        <button
          type="button"
          className="chatbox-attach"
          title="Attach Proposal"
          tabIndex={-1}
        >
          <Plus size={28} />
        </button>

        <div className="chatbox-field">
          <textarea
            ref={inputRef}
            className="chatbox-input"
            placeholder="Type your pitch idea..."
            disabled={disabled}
            autoFocus
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            aria-label="Describe your client's need"
          />
        </div>

        <button
          className="chatbox-send"
          type="submit"
          disabled={disabled}
          aria-label="Generate proposal"
        >
          <Send size={24} />
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
          {webSearch ? "Web search on" : "Web search off"}
        </button>
      </div>

      <p className="chatbox-footer-text">
        Dracarys can make mistakes. Consider verifying important claims.
      </p>
    </form>
  );
};

export default ChatBox;
