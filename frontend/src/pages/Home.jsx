import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { AlertTriangle } from "lucide-react";
import Sidebar from "../components/Sidebar";
import ChatBox from "../components/ChatBox";
import Loader from "../components/Loader";
import ProposalPreview from "../components/ProposalPreview";
import {
  generateProposal,
  getConversations,
  getConversation,
  deleteConversation,
} from "../api/api";
import { useAuth } from "../context/AuthContext";

const WELCOME_MSG = {
  id: "welcome",
  role: "assistant",
  text: "Hey! 👋 Ready to crush that pitch today? What are we working on?",
};

const PROMPT_CHIPS = [
  "What FMCG projects have we delivered?",
  "What Azure experience do we have?",
  "Generate a pitch for a pharma supply chain client",
  "Explain our data warehousing capabilities",
];

const CONVERSATIONAL_RE = /^(hi+|hello|hey|howdy|yo|sup|good\s+morning|good\s+afternoon|good\s+evening|thanks|thank\s+you|ok+|okay|yes|no+|bye|great|cool|nice|test|ping|check)[\s!?.]*$/i;

const isConversational = (query) =>
  CONVERSATIONAL_RE.test(query.trim()) || query.trim().length < 4;

const messageVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: "easeOut" },
  },
};

const dbMsgToReact = (msg) => ({
  id: msg.id,
  role: msg.role,
  ...(msg.proposal_data ? { proposalData: msg.proposal_data } : { text: msg.text }),
});

const Home = () => {
  const { user } = useAuth();

  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [webSearch, setWebSearch] = useState(false);
  const [tone, setTone] = useState("balanced");
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  const chatEndRef = useRef(null);
  const prevUserRef = useRef(user);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // On login: load conversation list and most-recent conversation.
  // On logout: reset to blank state.
  useEffect(() => {
    if (user === prevUserRef.current) return;
    prevUserRef.current = user;

    if (user) {
      getConversations()
        .then(async (convs) => {
          setConversations(convs);
          if (convs.length > 0) {
            const conv = await getConversation(convs[0].id);
            setMessages([WELCOME_MSG, ...conv.messages.map(dbMsgToReact)]);
            setActiveConversationId(convs[0].id);
          }
        })
        .catch(() => {});
    } else {
      setMessages([WELCOME_MSG]);
      setConversations([]);
      setActiveConversationId(null);
    }
  }, [user]);

  const handleNewChat = useCallback(() => {
    setMessages([WELCOME_MSG]);
    setActiveConversationId(null);
    setError(null);
  }, []);

  const handleSelectConversation = useCallback(async (id) => {
    if (id === activeConversationId) return;
    try {
      const conv = await getConversation(id);
      setMessages([WELCOME_MSG, ...conv.messages.map(dbMsgToReact)]);
      setActiveConversationId(id);
      setError(null);
    } catch {}
  }, [activeConversationId]);

  const handleDeleteConversation = useCallback(async (id) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        setMessages([WELCOME_MSG]);
        setActiveConversationId(null);
      }
    } catch {}
  }, [activeConversationId]);

  const handleSend = useCallback(async (query) => {
    const userMsg = { id: Date.now(), role: "user", text: query };
    setMessages((prev) => [...prev, userMsg]);

    if (isConversational(query)) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: "I'm here to help with your sales conversations! Ask me about our past projects, industry experience, or technical capabilities — or ask me to generate a pitch for a specific client.",
        },
      ]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await generateProposal(query, webSearch, activeConversationId, tone);

      const assistantMsg = {
        id: Date.now() + 1,
        role: "assistant",
        proposalData: result,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (user && result.conversation_id) {
        const newId = result.conversation_id;
        setActiveConversationId(newId);
        setConversations((prev) => {
          if (prev.some((c) => c.id === newId)) return prev;
          return [
            { id: newId, title: result.conversation_title, created_at: new Date().toISOString() },
            ...prev,
          ];
        });
      }
    } catch (err) {
      const msg =
        err.response?.data?.error || "Failed to get a response. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [webSearch, tone, activeConversationId, user]);

  return (
    <div className="layout">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
      />
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
          <div className="chat-date">
            <span>Today</span>
            {messages.length > 1 && (
              <button className="clear-btn" onClick={handleNewChat} title="New chat">
                + New chat
              </button>
            )}
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

          {messages.length === 1 && !loading && (
            <div className="prompt-chips">
              {PROMPT_CHIPS.map((chip) => (
                <button
                  key={chip}
                  className="prompt-chip"
                  onClick={() => handleSend(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Floating input dock */}
        <div className="input-dock">
          <ChatBox
            onSend={handleSend}
            disabled={loading}
            webSearch={webSearch}
            onToggleWebSearch={setWebSearch}
            tone={tone}
            onToneChange={setTone}
          />
        </div>
      </main>
    </div>
  );
};

export default Home;
