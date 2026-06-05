import { motion } from "motion/react";

const dotVariants = {
  animate: (i) => ({
    scale: [0, 1, 0],
    transition: {
      duration: 1.4,
      repeat: Infinity,
      delay: i * 0.16,
      ease: "easeInOut",
    },
  }),
};

const Loader = ({ message }) => (
  <div className="message-sidekick">
    <div className="sidekick-bubble is-typing" style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "flex-start" }}>
      {message && <div className="loader-stage-msg" style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--accent-orange, #f97316)" }}>{message}</div>}
      <div className="typing-dots">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="typing-dot"
            custom={i}
            variants={dotVariants}
            initial="animate"
            animate="animate"
          />
        ))}
      </div>
    </div>
  </div>
);

export default Loader;
