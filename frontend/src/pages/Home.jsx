import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle } from "lucide-react";
import Sidebar from "../components/Sidebar";
import ChatBox from "../components/ChatBox";
import Loader from "../components/Loader";
import ProposalPreview from "../components/ProposalPreview";
import { generateProposal } from "../api/api";

const WELCOME_MSG = {
  id: "welcome",
  role: "assistant",
  text: "Hey! 👋 Ready to crush that pitch today? What are we working on?",
};

const messageVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: "easeOut" },
  },
};

const Home = () => {
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async (query) => {
    const userMsg = { id: Date.now(), role: "user", text: query };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const result = await generateProposal(query);

      const assistantMsg = {
        id: Date.now() + 1,
        role: "assistant",
        proposalData: result,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg =
        err.response?.data?.error || "Failed to generate proposal. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="layout">
      <Sidebar />
      <main className="main">
        {/* Mobile header */}
        <header className="mobile-header">
          <div className="mobile-header-left">
            <div className="mobile-blob">
              <svg fill="none" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                <circle cx="20" cy="24" fill="currentColor" r="6" />
                <circle cx="44" cy="24" fill="currentColor" r="6" />
                <path d="M22 40C22 40 28 46 32 46C36 46 42 40 42 40" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
              </svg>
            </div>
            <h1 className="mobile-title">Dracarys</h1>
          </div>
          <button className="mobile-menu-btn">
            <span className="material-symbols-outlined">menu</span>
          </button>
        </header>

        {/* Chat area */}
        <div className="chat-area" id="chat-container">
          {/* Date separator */}
          <div className="chat-date">
            <span>Today</span>
          </div>

          <AnimatePresence mode="wait">
            {messages.map((msg) =>
              msg.role === "user" ? (
                <motion.div
                  key={msg.id}
                  className="message-user"
                  variants={messageVariants}
                  initial="hidden"
                  animate="visible"
                >
                  <div className="user-bubble">
                    <p>{msg.text}</p>
                  </div>
                </motion.div>
              ) : msg.proposalData ? (
                <motion.div
                  key={msg.id}
                  variants={messageVariants}
                  initial="hidden"
                  animate="visible"
                >
                  <ProposalPreview data={msg.proposalData} />
                </motion.div>
              ) : (
                <motion.div
                  key={msg.id}
                  className="message-sidekick"
                  variants={messageVariants}
                  initial="hidden"
                  animate="visible"
                >
                  <div className="sidekick-bubble">
                    <p className="sidekick-bubble-text">{msg.text}</p>
                  </div>
                </motion.div>
              )
            )}
          </AnimatePresence>

          {loading && <Loader />}

          {error && (
            <motion.div
              key="error"
              className="error-banner"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              role="alert"
            >
              <AlertTriangle size={18} className="error-icon" aria-hidden="true" />
              <span>{error}</span>
            </motion.div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Floating input dock */}
        <div className="input-dock">
          <ChatBox onSend={handleSend} disabled={loading} />
        </div>
      </main>
    </div>
  );
};

export default Home;
