const PLACEHOLDER = "We need a retail analytics dashboard...";

const ChatBox = ({ onSend, disabled }) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.query;
    const value = input.value.trim();
    if (!value || disabled) return;
    onSend(value);
    input.value = "";
  };

  return (
    <form className="chatbox" onSubmit={handleSubmit}>
      <input
        name="query"
        className="chatbox-input"
        type="text"
        placeholder={PLACEHOLDER}
        disabled={disabled}
        autoFocus
      />
      <button className="chatbox-btn" type="submit" disabled={disabled}>
        Generate
      </button>
    </form>
  );
};

export default ChatBox;
