import { useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatBox from "../components/ChatBox";
import Loader from "../components/Loader";
import ProposalPreview from "../components/ProposalPreview";
import { generateProposal } from "../api/api";

const Home = () => {
  const [proposalData, setProposalData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSend = async (query) => {
    setLoading(true);
    setError(null);
    setProposalData(null);

    try {
      const result = await generateProposal(query);
      setProposalData(result);
    } catch (err) {
      const msg =
        err.response?.data?.error || "Failed to generate proposal. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="layout">
      <Sidebar />
      <main className="main">
        <ChatBox onSend={handleSend} disabled={loading} />
        {loading && <Loader />}
        {error && <div className="error-banner">{error}</div>}
        {proposalData && <ProposalPreview data={proposalData} />}
        {!proposalData && !loading && !error && (
          <div className="empty-state">
            <p>Enter a client need above to generate a proposal draft.</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default Home;
