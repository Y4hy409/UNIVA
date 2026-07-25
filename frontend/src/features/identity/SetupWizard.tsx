import React, { useState } from 'react';
import { Sparkles, UserPlus, AlertTriangle, Eye, EyeOff } from 'lucide-react';

interface SetupWizardProps {
  onSetupSuccess: (token: string, username: string, role: string) => void;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ onSetupSuccess }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !email || !password) return;

    setLoading(true);
    setErrorMsg(null);

    try {
      const response = await fetch('http://localhost:8000/auth/setup-owner', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Setup failed");
      }

      const data = await response.json() as { access_token: string; username: string; role: string };
      onSetupSuccess(data.access_token, data.username, data.role);
    } catch (err: any) {
      setErrorMsg(err.message || "An error occurred during setup wizard.");
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
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
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
          <h2 style={{ color: '#f8fafc', fontWeight: 700, fontSize: '18px', margin: '0 0 6px 0' }}>CLARIUS Setup Wizard</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>Configure your owner account to begin.</p>
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
              Owner Username
            </label>
            <input
              type="text"
              className="input-field"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. systemowner"
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', color: '#f8fafc', fontSize: '13px', fontWeight: 500, marginBottom: '6px' }}>
              Owner Email
            </label>
            <input
              type="email"
              className="input-field"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="owner@company.com"
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

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '6px' }} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: '14px', height: '14px' }}></span> : <UserPlus size={16} />}
            <span>Initialize Installation</span>
          </button>
        </form>
      </div>
    </div>
  );
};
