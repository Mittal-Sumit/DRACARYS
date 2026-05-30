import { motion } from "motion/react";
import { MessageCircle, Archive, Settings, LogOut, Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { icon: MessageCircle, label: "Chat", active: true },
  { icon: Archive, label: "Archive", active: false },
  { icon: Settings, label: "Settings", active: false },
];

const sidebarVariants = {
  hidden: { x: -20, opacity: 0 },
  visible: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.4, ease: "easeOut" },
  },
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
};

const Sidebar = ({
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
}) => {
  const { user, logout, bootstrapping } = useAuth();

  return (
    <motion.aside
      className="sidebar"
      variants={sidebarVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Avatar */}
      <div className="sidebar-avatar-section">
        <div className="blob-avatar">
          <svg
            className="blob-face"
            fill="none"
            viewBox="0 0 64 64"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="20" cy="24" fill="currentColor" r="5" />
            <circle cx="44" cy="24" fill="currentColor" r="5" />
            <path
              d="M22 40C22 40 28 46 32 46C36 46 42 40 42 40"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="4"
            />
          </svg>
        </div>
        <h1 className="sidebar-title">Dracarys</h1>
        <div className="sidebar-status">
          <span className="status-dot" />
          Ready to pitch
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ icon: Icon, label, active }) => (
          <a
            key={label}
            className={`sidebar-nav-link ${active ? "active" : ""}`}
            href="#"
            onClick={(e) => e.preventDefault()}
          >
            <Icon size={22} className={`nav-icon ${active ? "fill-current" : ""}`} />
            {label}
          </a>
        ))}
      </nav>

      {/* Conversation history — authenticated only */}
      {!bootstrapping && user && (
        <div className="sidebar-conversations">
          <div className="sidebar-conversations-header">
            <span className="sidebar-conversations-label">Conversations</span>
            <button
              className="new-chat-btn"
              onClick={onNewChat}
              title="New chat"
            >
              <Plus size={15} />
              New
            </button>
          </div>

          <div className="conv-list">
            {conversations.length === 0 ? (
              <p className="conv-empty">No conversations yet. Send your first message!</p>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conv-item ${conv.id === activeConversationId ? "active" : ""}`}
                  onClick={() => onSelectConversation(conv.id)}
                >
                  <div className="conv-item-body">
                    <p className="conv-item-title">{conv.title}</p>
                    <p className="conv-item-date">{formatDate(conv.created_at)}</p>
                  </div>
                  <button
                    className="conv-delete-btn"
                    onClick={(e) => { e.stopPropagation(); onDeleteConversation(conv.id); }}
                    title="Delete conversation"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Guest sign-in prompt — shown only while not bootstrapping and not logged in */}
      {!bootstrapping && !user && (
        <div className="sidebar-guest">
          <Link to="/login" className="sidebar-signin-btn">Sign in</Link>
          <Link to="/signup" className="sidebar-signup-link">Create account</Link>
        </div>
      )}

      {/* User info / logout — pinned to bottom */}
      {!bootstrapping && user && (
        <div className="sidebar-user">
          <div className="sidebar-user-info">
            <p className="sidebar-user-name">{user.username}</p>
            <p className="sidebar-user-email">{user.email}</p>
          </div>
          <button className="sidebar-logout-btn" onClick={logout} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      )}
    </motion.aside>
  );
};

export default Sidebar;
