import React, { useState } from 'react';
import { LogIn, AlertTriangle, Eye, EyeOff, Shield } from 'lucide-react';
import { apiFetch } from '../../config/api';

interface LoginFormProps {
  onLoginSuccess: (token: string, username: string, role: string) => void;
  onToggleSetup?: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onLoginSuccess, onToggleSetup }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;

    setLoading(true);
    setErrorMsg(null);

    try {
      const response = await apiFetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Authentication failed");
      }

      const data = await response.json() as { access_token: string; username: string; role: string };
      onLoginSuccess(data.access_token, data.username, data.role);
    } catch (err: any) {
      setErrorMsg(err.message || "Invalid username or password.");
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
      <div className="card" style={{ width: '100%', maxWidth: '380px', border: '1px solid #1e293b', backgroundColor: '#0d131f' }}>
        <div style={{ textAlign: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'inline-flex', padding: '10px', backgroundColor: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', marginBottom: '12px' }}>
            <Shield size={24} style={{ color: '#3b82f6' }} />
          </div>
          <h2 style={{ color: '#f8fafc', fontWeight: 700, fontSize: '18px', margin: '0 0 6px 0', letterSpacing: '0.5px' }}>CLARIUS</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>Sign in to access your business workspace</p>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', marginBottom: '16px' }}>
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
            Sign In
          </button>
          {onToggleSetup && (
            <button
              type="button"
              onClick={onToggleSetup}
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
              Sign Up
            </button>
          )}
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

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Username
            </label>
            <input
              type="text"
              className="input-field"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"}
                className="input-field"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
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

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '6px' }} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: '14px', height: '14px' }}></span> : <LogIn size={16} />}
            <span>Sign In</span>
          </button>
        </form>

        {onToggleSetup && (
          <div style={{ marginTop: '16px', textAlign: 'center', borderTop: '1px solid #1e293b', paddingTop: '12px' }}>
            <button
              type="button"
              onClick={onToggleSetup}
              style={{ background: 'none', border: 'none', color: '#3b82f6', fontSize: '12px', cursor: 'pointer', fontWeight: 500 }}
            >
              Sign up as new user
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
