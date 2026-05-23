import { motion } from "motion/react";
import {
  Briefcase,
  Wrench,
  ClipboardList,
  Star,
  Lightbulb,
  Inbox,
} from "lucide-react";

const ICON_RULES = [
  [/(experience|project|case\s*stud|work|client|delivered)/i, Briefcase],
  [/(solution|approach|architect|technical|implementation|build|stack)/i, Wrench],
  [/(summary|overview|executive|background)/i, ClipboardList],
  [/(why|differenti|advantage|unique|partner|choose)/i, Star],
];

const getIcon = (heading) => {
  if (!heading) return Lightbulb;
  for (const [pattern, Icon] of ICON_RULES) {
    if (pattern.test(heading)) return Icon;
  }
  return Lightbulb;
};

const sectionVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.35, ease: "easeOut" },
  }),
};

const ProposalPreview = ({ data }) => (
  <div className="message-sidekick">
    <div className="sidekick-bubble">
      {data.sections?.map((section, i) => {
        const Icon = getIcon(section.heading);
        return (
          <motion.div
            key={i}
            className={section.heading ? "proposal-section-inset" : "plain-section"}
            custom={i}
            variants={sectionVariants}
            initial="hidden"
            animate="visible"
          >
            {section.heading && (
              <h3 className="proposal-section-heading">
                <Icon size={14} />
                {section.heading}
              </h3>
            )}
            <p className="proposal-section-text">{section.content}</p>
          </motion.div>
        );
      })}

      {data.sources?.length > 0 && (
        <motion.div
          className="proposal-section-inset"
          custom={data.sections?.length ?? 0}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
        >
          <h3 className="proposal-section-heading">
            <Inbox size={14} />
            Generated Using
          </h3>
          <ul className="proposal-sources-list">
            {data.sources.map((src) => (
              <li key={src}>{src}</li>
            ))}
          </ul>
        </motion.div>
      )}
    </div>
  </div>
);

export default ProposalPreview;
