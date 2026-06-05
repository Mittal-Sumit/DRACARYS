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
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.warn("Clipboard access denied");
    }
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
  [/(summary|overview|executive|background|objective|opportunity)/i, ClipboardList],
  [/(why|differenti|advantage|unique|partner|choose|points)/i, Star],
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

const CopyAllButton = ({ data }) => {
  const [copied, setCopied] = useState(false);
  const handleCopyAll = async () => {
    let text = "";
    if (data.subject && data.body) {
      text = `Subject: ${data.subject}\n\n${data.body}`;
    } else if (data.sections) {
      text = data.sections
        .map((s) => (s.heading ? `## ${s.heading}\n\n${s.content}` : s.content))
        .join("\n\n");
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      console.warn("Clipboard access denied");
    }
  };
  return (
    <button className="proposal-action-btn" onClick={handleCopyAll}>
      {copied ? (
        <>
          <Check size={13} />
          <span>Copied!</span>
        </>
      ) : (
        <>
          <Copy size={13} />
          <span>Copy All</span>
        </>
      )}
    </button>
  );
};

const ExportButton = ({ data }) => {
  const handleExport = () => {
    let text = "";
    let filename = "proposal.txt";
    if (data.subject && data.body) {
      text = `Subject: ${data.subject}\n\n${data.body}`;
      filename = `email_pitch_${Date.now()}.txt`;
    } else if (data.sections) {
      text = data.sections
        .map((s) => (s.heading ? `## ${s.heading}\n\n${s.content}` : s.content))
        .join("\n\n");
      filename = `proposal_${Date.now()}.txt`;
    }
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
  return (
    <button className="proposal-action-btn" onClick={handleExport} title="Download as text file">
      <ExternalLink size={13} />
      <span>Export</span>
    </button>
  );
};

const ProposalPreview = ({ data }) => (
  <div className="proposal-response">
    <div className="proposal-header-dock">
      <p className="proposal-byline">Dracarys</p>
      <div className="proposal-global-actions">
        <CopyAllButton data={data} />
        <ExportButton data={data} />
      </div>
    </div>

    {data.subject && data.body ? (
      <motion.div
        className="proposal-card email-preview-card"
        variants={cardVariants}
        custom={0}
        initial="hidden"
        animate="visible"
      >
        <div className="email-preview-header">
          <div className="email-header-line">
            <span className="email-header-label">Subject:</span>
            <span className="email-header-value">{data.subject}</span>
          </div>
        </div>
        <div className="email-preview-divider" />
        <div className="email-preview-body">
          {data.body.split("\n").map((line, idx) => (
            <p key={idx} className="email-body-line">
              {line.trim() === "" ? <br /> : line}
            </p>
          ))}
        </div>
      </motion.div>
    ) : (
      data.sections?.map((section, i) => {
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
      })
    )}

    {(data.sources?.length > 0 || data.web_sources?.length > 0) && (
      <motion.div
        className="proposal-sources"
        custom={data.sections?.length ?? 1}
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
