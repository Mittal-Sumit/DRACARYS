import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { forgotPassword } from "../api/api";

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [devResetUrl, setDevResetUrl] = useState(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await forgotPassword(email);
      if (data.dev_reset_url) {
        setDevResetUrl(data.dev_reset_url);
      }
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDevLink = () => {
    // Extract the path from the full URL and navigate client-side
    const url = new URL(devResetUrl);
    navigate(url.pathname);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-blob">
          <svg fill="none" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
            <circle cx="20" cy="24" fill="currentColor" r="6" />
            <circle cx="44" cy="24" fill="currentColor" r="6" />
            <path d="M22 40C22 40 28 46 32 46C36 46 42 40 42 40" stroke="currentColor" strokeLinecap="round" strokeWidth="4" />
          </svg>
        </div>
        <h1 className="auth-title">Reset password</h1>

        {success ? (
          <>
            <p className="auth-subtitle" style={{ marginBottom: 0 }}>
              If <strong>{email}</strong> is registered, a reset link was sent.
            </p>
            {devResetUrl ? (
              <div className="auth-success" style={{ marginTop: 16 }}>
                <p style={{ margin: "0 0 10px" }}>
                  <strong>Dev mode</strong> — no email needed.
                </p>
                <button
                  className="auth-submit"
                  style={{ marginTop: 0 }}
                  onClick={handleDevLink}
                >
                  Continue to reset password
                </button>
              </div>
            ) : (
              <p className="auth-success">
                Check the <strong>Django terminal</strong> for the reset link.
              </p>
            )}
            <p className="auth-switch">
              <Link to="/login">Back to sign in</Link>
            </p>
          </>
        ) : (
          <>
            <p className="auth-subtitle">
              Enter your @ganitinc.com email and we&apos;ll send a reset link.
            </p>
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-field">
                <label className="auth-label">Email</label>
                <input
                  type="email"
                  className="auth-input"
                  placeholder="you@ganitinc.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              {error && <p className="auth-error">{error}</p>}

              <button type="submit" className="auth-submit" disabled={loading}>
                {loading ? "Sending…" : "Send reset link"}
              </button>
            </form>

            <p className="auth-switch">
              <Link to="/login">Back to sign in</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default ForgotPassword;
