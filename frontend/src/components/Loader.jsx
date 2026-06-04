const Loader = () => (
  <div className="message-sidekick">
    <div className="sidekick-bubble is-typing">
      <div className="typing-dots">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="typing-dot"
            style={{ animationDelay: `${i * 0.16}s` }}
          />
        ))}
      </div>
    </div>
  </div>
);

export default Loader;
