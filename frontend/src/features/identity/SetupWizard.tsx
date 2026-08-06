import React, { useState, useEffect } from 'react';
import { Sparkles, UserPlus, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { apiFetch } from '../../config/api';

interface SetupWizardProps {
  onSetupSuccess: (token: string, username: string, role: string) => void;
  onToggleLogin?: () => void;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ onSetupSuccess, onToggleLogin }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('analyst');
  const [availableRoles, setAvailableRoles] = useState<{id: string, name: string}[]>([]);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const res = await apiFetch('/auth/roles');
        if (res.ok) {
          const data = await res.json();
          setAvailableRoles(data);
          if (data.length > 0) {
            setRole(data[0].id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch roles", err);
      }
    };
    fetchRoles();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !email || !password) return;

    setLoading(true);
    setErrorMsg(null);

    try {
      // Try /auth/signup first; if system is not setup yet, fallback to /auth/setup-owner
      let response = await apiFetch('/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password, role })
      });

      if (!response.ok) {
        response = await apiFetch('/auth/setup-owner', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, email, password })
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Account creation failed");
      }

      const data = await response.json() as { access_token: string; username: string; role: string };
      onSetupSuccess(data.access_token, data.username, data.role);
    } catch (err: any) {
      setErrorMsg(err.message || "An error occurred during account creation.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      width: '100vw',
      backgroundColor: '#090d16'
    }}>
      <div className="card" style={{ width: '100%', maxWidth: '420px', border: '1px solid #1e293b', backgroundColor: '#0d131f' }}>
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderRadius: '50%',
            padding: '10px',
            marginBottom: '12px'
          }}>
            <Sparkles size={28} style={{ color: '#3b82f6' }} />
          </div>
          <h2 style={{ color: '#f8fafc', fontWeight: 700, fontSize: '18px', margin: '0 0 6px 0' }}>CLARIUS User Registration</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>Create your account to access the workspace.</p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', marginBottom: '16px' }}>
          {onToggleLogin && (
            <button
              type="button"
              onClick={onToggleLogin}
              style={{
                flex: 1,
                padding: '8px',
                background: 'none',
                border: 'none',
                borderBottom: '2px solid transparent',
                color: '#94a3b8',
                fontWeight: 500,
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              Sign In
            </button>
          )}
          <button
            type="button"
            style={{
              flex: 1,
              padding: '8px',
              background: 'none',
              border: 'none',
              borderBottom: '2px solid #3b82f6',
              color: '#3b82f6',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer'
            }}
          >
            Sign Up
          </button>
        </div>

        {errorMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '6px',
            padding: '8px 12px',
            color: '#ef4444',
            marginBottom: '16px',
            fontSize: '13px'
          }}>
            <AlertTriangle size={16} style={{ flexShrink: 0 }} />
            <div>{errorMsg}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Username
            </label>
            <input
              type="text"
              className="input-field"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. johndoe"
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Email Address
            </label>
            <input
              type="email"
              className="input-field"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@company.com"
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Account Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"}
                className="input-field"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                required
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              User Role
            </label>
            <select
              className="input-field"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{ width: '100%' }}
            >
              {availableRoles.length === 0 ? (
                <>
                  <option value="admin">Admin</option>
                  <option value="manager">Manager</option>
                  <option value="analyst">Analyst</option>
                  <option value="staff">Staff</option>
                </>
              ) : (
                availableRoles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))
              )}
            </select>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '6px' }} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: '14px', height: '14px' }}></span> : <UserPlus size={16} />}
            <span>Create Account</span>
          </button>
        </form>

        {onToggleLogin && (
          <div style={{ marginTop: '16px', textAlign: 'center', borderTop: '1px solid #1e293b', paddingTop: '12px' }}>
            <button
              type="button"
              onClick={onToggleLogin}
              style={{ background: 'none', border: 'none', color: '#3b82f6', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}
            >
              Already have an account? Sign In
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
