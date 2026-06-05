import { useRef, useCallback, useState } from "react";
import { Globe, Send, User, Building, Sliders } from "lucide-react";

const ChatBox = ({ onSend, disabled, webSearch, onToggleWebSearch, tone, onToneChange, personName, onPersonNameChange, companyName, onCompanyNameChange, format, onFormatChange }) => {
  const inputRef = useRef(null);
  const [showSettings, setShowSettings] = useState(false);

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
      {showSettings && (
        <div className="personalization-panel">
          <div className="personalization-field">
            <User size={14} className="personalization-icon" />
            <input
              type="text"
              className="personalization-input"
              placeholder="Stakeholder name (e.g. Sumit Mittal)"
              value={personName}
              onChange={(e) => onPersonNameChange(e.target.value)}
              disabled={disabled}
            />
          </div>
          <div className="personalization-field">
            <Building size={14} className="personalization-icon" />
            <input
              type="text"
              className="personalization-input"
              placeholder="Company name (e.g. Google)"
              value={companyName}
              onChange={(e) => onCompanyNameChange(e.target.value)}
              disabled={disabled}
            />
          </div>
        </div>
      )}

      <div className="chatbox-inner">
        <div className="chatbox-field">
          <textarea
            ref={inputRef}
            className="chatbox-input"
            placeholder="Describe your client's need or industry..."
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

        <button
          type="button"
          className={`web-toggle${showSettings || personName || companyName ? " active" : ""}`}
          onClick={() => setShowSettings(!showSettings)}
          title="Tailor proposal to a specific stakeholder and company news/pain points"
        >
          <Sliders size={12} />
          {personName || companyName ? "Personalized" : "Personalize"}
        </button>

        <div className="format-selector">
          <select
            value={format}
            onChange={(e) => onFormatChange(e.target.value)}
            disabled={disabled}
            className="format-dropdown"
            title="Choose output format"
          >
            <option value="proposal">📄 Proposal</option>
            <option value="email">✉️ Outreach Email</option>
            <option value="meeting_brief">🤝 Meeting Brief</option>
            <option value="one_pager">⚡ One-Pager</option>
          </select>
        </div>

        <div className="tone-pills">
          {["executive", "balanced", "technical"].map((t) => (
            <button
              key={t}
              type="button"
              className={`tone-pill${tone === t ? " active" : ""}`}
              onClick={() => onToneChange(t)}
              title={`Set tone to ${t}`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
};

export default ChatBox;
