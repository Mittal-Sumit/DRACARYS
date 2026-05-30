import { motion } from "motion/react";
import {
  MessageCircle,
  Archive,
  Settings,
  Trophy,
  Search,
  LogOut,
} from "lucide-react";
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

const Sidebar = () => {
  const { user, logout } = useAuth();
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
          <Icon
            size={22}
            className={`nav-icon ${active ? "fill-current" : ""}`}
          />
          {label}
        </a>
      ))}
    </nav>

    {/* Search */}
    <div className="sidebar-search">
      <Search size={16} className="search-icon" />
      <input
        className="search-input"
        type="text"
        placeholder="Search pitches..."
      />
    </div>

    {/* Stats */}
    <div className="sidebar-stats">
      <div className="stats-card">
        <div className="stats-info">
          <p className="stats-label">Pitches Saved</p>
          <p className="stats-value">12</p>
        </div>
        <div className="stats-icon">
          <Trophy size={20} />
        </div>
      </div>
    </div>

    {/* User info + logout */}
    {user && (
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
