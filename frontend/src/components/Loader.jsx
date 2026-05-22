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

const Loader = () => (
  <div className="message-sidekick">
    <div className="sidekick-bubble is-typing">
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
