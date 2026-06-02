import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { resetPassword } from "../api/api";

const ResetPassword = () => {
  const { uid, token } = useParams();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(uid, token, password);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.error || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
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
        <h1 className="auth-title">New password</h1>

        {success ? (
          <>
            <p className="auth-success" style={{ marginTop: 8 }}>
              Password reset successfully.
            </p>
            <p className="auth-switch">
              <Link to="/login">Sign in with your new password</Link>
            </p>
          </>
        ) : (
          <>
            <p className="auth-subtitle">Choose a new password for your account.</p>
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-field">
                <label className="auth-label">New password</label>
                <input
                  type="password"
                  className="auth-input"
                  placeholder="Min. 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
                />
              </div>
              <div className="auth-field">
                <label className="auth-label">Confirm password</label>
                <input
                  type="password"
                  className="auth-input"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              {error && <p className="auth-error">{error}</p>}

              <button type="submit" className="auth-submit" disabled={loading}>
                {loading ? "Resetting…" : "Reset password"}
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

export default ResetPassword;
