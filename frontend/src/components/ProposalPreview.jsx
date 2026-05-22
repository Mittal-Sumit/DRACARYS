import { motion } from "motion/react";
import {
  ClipboardList,
  Wrench,
  Briefcase,
  Star,
  Inbox,
} from "lucide-react";

const SECTIONS = [
  { label: "Executive Summary", key: "executive_summary", icon: ClipboardList },
  { label: "Proposed Solution", key: "proposed_solution", icon: Wrench },
  { label: "Relevant Experience", key: "relevant_experience", icon: Briefcase },
  { label: "Why Us", key: "why_us", icon: Star },
];

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
      <p className="sidekick-bubble-text mb-4">
        Here&rsquo;s your proposal draft based on past work:
      </p>

      {SECTIONS.map(({ label, key, icon: Icon }, i) =>
        data[key] ? (
          <motion.div
            key={key}
            className="proposal-section-inset"
            custom={i}
            variants={sectionVariants}
            initial="hidden"
            animate="visible"
          >
            <h3 className="proposal-section-heading">
              <Icon size={14} />
              {label}
            </h3>
            <p className="proposal-section-text">{data[key]}</p>
          </motion.div>
        ) : null
      )}

      {data.sources?.length > 0 && (
        <div className="proposal-section-inset">
          <h3 className="proposal-section-heading">
            <Inbox size={14} />
            Generated Using
          </h3>
          <ul className="proposal-sources-list">
            {data.sources.map((src) => (
              <li key={src}>{src}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  </div>
);

export default ProposalPreview;
