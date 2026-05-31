import { useState } from "react";
import { motion } from "motion/react";
import {
  Briefcase,
  Globe,
  Wrench,
  ClipboardList,
  Star,
  Lightbulb,
  Inbox,
  Copy,
  Check,
  ExternalLink,
} from "lucide-react";

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button className="copy-btn" onClick={handleCopy} title="Copy section">
      {copied ? <Check size={13} /> : <Copy size={13} />}
    </button>
  );
};

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

const cardVariants = {
  hidden: { opacity: 0, y: 14 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.07, duration: 0.3, ease: "easeOut" },
  }),
};

const ProposalPreview = ({ data }) => (
  <div className="proposal-response">
    <p className="proposal-byline">Dracarys</p>

    {data.sections?.map((section, i) => {
      const Icon = getIcon(section.heading);
      return (
        <motion.div
          key={i}
          className="proposal-card"
          custom={i}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
        >
          {section.heading ? (
            <>
              <div className="proposal-card-header">
                <div className="proposal-card-icon">
                  <Icon size={15} />
                </div>
                <h3 className="proposal-card-title">{section.heading}</h3>
                <CopyButton text={section.content} />
              </div>
              <p className="proposal-card-body">{section.content}</p>
            </>
          ) : (
            <p className="proposal-card-body plain">{section.content}</p>
          )}
        </motion.div>
      );
    })}

    {(data.sources?.length > 0 || data.web_sources?.length > 0) && (
      <motion.div
        className="proposal-sources"
        custom={data.sections?.length ?? 0}
        variants={cardVariants}
        initial="hidden"
        animate="visible"
      >
        {data.sources?.length > 0 && (
          <div className="proposal-sources-group">
            <span className="proposal-sources-label">
              <Inbox size={11} />
              Sources
            </span>
            <div className="proposal-pills">
              {data.sources.map((src) => {
                const name = typeof src === "string" ? src : src.name;
                const url = typeof src === "string" ? null : src.url;
                return url ? (
                  <a key={name} href={url} target="_blank" rel="noopener noreferrer" className="pill pill-kb">
                    {name}
                    <ExternalLink size={10} />
                  </a>
                ) : (
                  <span key={name} className="pill pill-kb">{name}</span>
                );
              })}
            </div>
          </div>
        )}

        {data.web_sources?.length > 0 && (
          <div className="proposal-sources-group">
            <span className="proposal-sources-label">
              <Globe size={11} />
              Web
            </span>
            <div className="proposal-pills">
              {data.web_sources.map((src) => (
                <a key={src.url || src.name} href={src.url} target="_blank" rel="noopener noreferrer" className="pill pill-web">
                  {src.name}
                  <ExternalLink size={10} />
                </a>
              ))}
            </div>
          </div>
        )}
      </motion.div>
    )}
  </div>
);

export default ProposalPreview;
