const SECTIONS = [
  { label: "Executive Summary", key: "executive_summary" },
  { label: "Proposed Solution", key: "proposed_solution" },
  { label: "Relevant Experience", key: "relevant_experience" },
  { label: "Why Us", key: "why_us" },
];

const ProposalPreview = ({ data }) => (
  <div className="proposal">
    {SECTIONS.map(({ label, key }) =>
      data[key] ? (
        <div key={key} className="proposal-section">
          <h2 className="proposal-heading">{label}</h2>
          <p className="proposal-text">{data[key]}</p>
        </div>
      ) : null
    )}
    {data.sources?.length > 0 && (
      <div className="proposal-section">
        <h2 className="proposal-heading">Generated Using</h2>
        <ul className="proposal-sources">
          {data.sources.map((src) => (
            <li key={src}>{src}</li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

export default ProposalPreview;
