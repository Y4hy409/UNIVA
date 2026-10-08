import React, { useState, useEffect } from 'react';
import { 
  User as UserIcon, Shield, Key, LogOut, CheckCircle2, 
  AlertCircle, Building2, Briefcase, Mail, 
  Eye, EyeOff, RefreshCw
} from 'lucide-react';
import { apiFetch } from '../../config/api';

export interface UserProfileData {
  id?: string;
  username?: string;
  email?: string;
  role?: string;
  full_name?: string;
  phone?: string;
  department?: string;
  branch?: string;
  team?: string;
  status?: string;
  employee_id?: string;
  created_at?: string;
  updated_at?: string;
  permissions?: string[];
}

export interface AccountProfileWorkspaceProps {
  username: string;
  role: string;
  onLogout: () => void;
}

export const formatErrorMessage = (err: any): string => {
  if (!err) return 'An unexpected error occurred.';
  if (typeof err === 'string') return err;
  if (err instanceof Error && err.message) return formatErrorMessage(err.message);
  
  if (typeof err === 'object') {
    if (typeof err.detail === 'string') return err.detail;
    if (Array.isArray(err.detail)) {
      return err.detail.map((e: any) => {
        if (typeof e === 'string') return e;
        return e.msg || e.message || (e.loc ? `${e.loc.join('.')}: invalid input` : JSON.stringify(e));
      }).join('; ');
    }
    if (typeof err.detail === 'object') return formatErrorMessage(err.detail);
    if (typeof err.message === 'string') return err.message;
    if (typeof err.error === 'string') return err.error;
    try {
      return JSON.stringify(err);
    } catch {
      return 'An unexpected error occurred.';
    }
  }
  
  return String(err);
};

export const AccountProfileWorkspace: React.FC<AccountProfileWorkspaceProps> = ({
  username,
  role,
  onLogout
}) => {
  const [profile, setProfile] = useState<UserProfileData>({
    username: username,
    role: role,
    email: '',
    full_name: '',
    phone: '',
    department: '',
    branch: '',
    team: '',
    status: 'Active',
    employee_id: '',
    permissions: []
  });

  const [loading, setLoading] = useState<boolean>(true);
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Security Form State
  const [securityForm, setSecurityForm] = useState({
    newPassword: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [updatingPassword, setUpdatingPassword] = useState<boolean>(false);
  const [securitySuccess, setSecuritySuccess] = useState<string | null>(null);
  const [securityError, setSecurityError] = useState<string | null>(null);

  const fetchProfile = async () => {
    setLoading(true);
    setProfileError(null);
    try {
      const res = await apiFetch('/auth/me');
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      } else {
        const err = await res.json();
        setProfileError(formatErrorMessage(err));
      }
    } catch (err: any) {
      console.error("Failed to load user profile", err);
      setProfileError(formatErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setProfileSuccess(null);
    setProfileError(null);

    try {
      const res = await apiFetch('/auth/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: profile.full_name,
          email: profile.email,
          phone: profile.phone
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw errData;
      }

      setProfileSuccess("Profile updated successfully.");
      await fetchProfile();
    } catch (err: any) {
      setProfileError(formatErrorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSecuritySuccess(null);
    setSecurityError(null);

    if (!securityForm.newPassword) {
      setSecurityError("Please enter a new password.");
      return;
    }

    if (securityForm.newPassword !== securityForm.confirmPassword) {
      setSecurityError("New password and confirmation do not match.");
      return;
    }

    if (securityForm.newPassword.length < 6) {
      setSecurityError("Password must be at least 6 characters long.");
      return;
    }

    setUpdatingPassword(true);

    try {
      const res = await apiFetch('/auth/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          password: securityForm.newPassword
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw errData;
      }

      setSecuritySuccess("Password updated successfully.");
      setSecurityForm({ newPassword: '', confirmPassword: '' });
    } catch (err: any) {
      setSecurityError(formatErrorMessage(err));
    } finally {
      setUpdatingPassword(false);
    }
  };

  const initialLetter = (profile.full_name || profile.username || username || 'U')[0].toUpperCase();
  const displayRole = (profile.role || role || 'User').toUpperCase();

  const getScopeDescription = (r: string) => {
    const norm = r.toLowerCase();
    if (norm === 'owner') return 'Full Organization Ownership & Administration';
    if (norm === 'admin') return 'System Administration & Configuration';
    if (norm === 'manager') return 'Branch Management & Operational Oversight';
    if (norm === 'analyst') return 'Analytics & Reporting Data Scope';
    return 'Regular Staff Access';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* Top Header / Breadcrumb */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <div style={{ fontSize: '12px', fontWeight: 600, color: '#3b82f6', letterSpacing: '0.5px', textTransform: 'uppercase', marginBottom: '4px' }}>
            Administration / My Profile
          </div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            Account Management
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={fetchProfile}
            disabled={loading}
            style={{ padding: '8px 14px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              if (window.confirm("Are you sure you want to sign out of your session?")) {
                onLogout();
              }
            }}
            style={{ padding: '8px 14px', fontSize: '13px', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <LogOut size={15} />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {/* Profile Hero Summary Card */}
      <div className="card" style={{ padding: '24px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '12px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '24px', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <div style={{
            width: '68px', height: '68px', borderRadius: '50%',
            background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
            color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '28px', fontWeight: 800, boxShadow: '0 4px 14px rgba(59, 130, 246, 0.35)', flexShrink: 0
          }}>
            {initialLetter}
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '4px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                {profile.full_name || profile.username || username}
              </h2>
              <span style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)', padding: '2px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 700, letterSpacing: '0.5px' }}>
                {displayRole}
              </span>
              <span style={{ backgroundColor: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '2px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
                {profile.status || 'Active'}
              </span>
            </div>

            <div style={{ color: '#94a3b8', fontSize: '13px', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
              <span>@{profile.username || username}</span>
              {profile.email && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Mail size={13} style={{ color: '#64748b' }} />
                  {profile.email}
                </span>
              )}
              {profile.branch && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Building2 size={13} style={{ color: '#64748b' }} />
                  {profile.branch}
                </span>
              )}
            </div>
          </div>
        </div>

        <div style={{ fontSize: '12px', color: '#64748b', textAlign: 'right', minWidth: '160px' }}>
          <div>Account Security: <strong style={{ color: '#10b981' }}>Authenticated</strong></div>
          <div style={{ marginTop: '4px' }}>Role Scope: <strong style={{ color: '#f8fafc' }}>{getScopeDescription(profile.role || role)}</strong></div>
        </div>
      </div>

      {/* Main Grid: Account Info & RBAC Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        
        {/* Account Information Details */}
        <div className="card" style={{ padding: '20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
            <UserIcon size={18} style={{ color: '#3b82f6' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Account Information
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>Username</span>
              <strong style={{ color: '#f8fafc' }}>{profile.username || username}</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>System Role</span>
              <span style={{ color: '#60a5fa', fontWeight: 600, textTransform: 'capitalize' }}>{profile.role || role}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>Account Status</span>
              <span style={{ color: '#10b981', fontWeight: 600 }}>{profile.status || 'Active'}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>Assigned Branch</span>
              <span style={{ color: profile.branch ? '#f8fafc' : '#64748b' }}>
                {profile.branch || 'Not configured'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>Department</span>
              <span style={{ color: profile.department ? '#f8fafc' : '#64748b' }}>
                {profile.department || 'Not configured'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>Operational Team</span>
              <span style={{ color: profile.team ? '#f8fafc' : '#64748b' }}>
                {profile.team || 'Not configured'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #161e2e', paddingBottom: '8px' }}>
              <span style={{ color: '#94a3b8' }}>Employee ID</span>
              <span style={{ color: profile.employee_id ? '#f8fafc' : '#64748b' }}>
                {profile.employee_id || 'Not configured'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px' }}>
              <span style={{ color: '#94a3b8' }}>Account Created</span>
              <span style={{ color: profile.created_at ? '#f8fafc' : '#64748b' }}>
                {profile.created_at ? new Date(profile.created_at).toLocaleDateString() : 'Active session'}
              </span>
            </div>
          </div>
        </div>

        {/* Role & Access Permissions Summary */}
        <div className="card" style={{ padding: '20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
            <Shield size={18} style={{ color: '#10b981' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Access & Role Permissions
            </h3>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>Access Scope</div>
            <div style={{ fontSize: '13px', color: '#f8fafc', fontWeight: 500, backgroundColor: '#070b14', padding: '8px 12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
              {getScopeDescription(profile.role || role)}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '8px' }}>Effective Permissions</div>
            {profile.permissions && profile.permissions.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                {profile.permissions.map((perm, idx) => (
                  <span key={idx} style={{ backgroundColor: '#1e293b', color: '#cbd5e1', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontFamily: 'monospace' }}>
                    {perm}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic', backgroundColor: '#070b14', padding: '12px', borderRadius: '6px', border: '1px dashed #1e293b' }}>
                Standard role capabilities enabled for role '{profile.role || role}'.
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Main Grid: Edit Personal Information & Security Forms */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        
        {/* Personal Information Form */}
        <div className="card" style={{ padding: '20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
            <Briefcase size={18} style={{ color: '#3b82f6' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Personal Information
            </h3>
          </div>

          {profileSuccess && (
            <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', color: '#10b981', fontSize: '13px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={16} />
              <span>{profileSuccess}</span>
            </div>
          )}

          {profileError && (
            <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#ef4444', fontSize: '13px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={16} />
              <span>{profileError}</span>
            </div>
          )}

          <form onSubmit={handleProfileSave} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>Full Name</label>
              <input
                type="text"
                className="input-field"
                value={profile.full_name || ''}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                placeholder="Enter full display name"
                style={{ width: '100%', backgroundColor: '#070b14', border: '1px solid #1e293b', fontSize: '13px' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>Email Address</label>
              <input
                type="email"
                className="input-field"
                value={profile.email || ''}
                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                placeholder="Enter email address"
                style={{ width: '100%', backgroundColor: '#070b14', border: '1px solid #1e293b', fontSize: '13px' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>Phone Number</label>
              <input
                type="text"
                className="input-field"
                value={profile.phone || ''}
                onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                placeholder="Enter contact phone number"
                style={{ width: '100%', backgroundColor: '#070b14', border: '1px solid #1e293b', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={savingProfile}
                style={{ padding: '8px 18px', fontSize: '13px', fontWeight: 600 }}
              >
                {savingProfile ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>

        {/* Security & Password Update Section */}
        <div className="card" style={{ padding: '20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
            <Key size={18} style={{ color: '#f59e0b' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Password & Security
            </h3>
          </div>

          {securitySuccess && (
            <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', color: '#10b981', fontSize: '13px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={16} />
              <span>{securitySuccess}</span>
            </div>
          )}

          {securityError && (
            <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#ef4444', fontSize: '13px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={16} />
              <span>{securityError}</span>
            </div>
          )}

          <form onSubmit={handlePasswordUpdate} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>New Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? "text" : "password"}
                  className="input-field"
                  value={securityForm.newPassword}
                  onChange={(e) => setSecurityForm({ ...securityForm, newPassword: e.target.value })}
                  placeholder="Enter new password"
                  style={{ width: '100%', backgroundColor: '#070b14', border: '1px solid #1e293b', fontSize: '13px', paddingRight: '38px' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex'
                  }}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', color: '#cbd5e1', fontSize: '12px', fontWeight: 500, marginBottom: '6px' }}>Confirm New Password</label>
              <input
                type={showPassword ? "text" : "password"}
                className="input-field"
                value={securityForm.confirmPassword}
                onChange={(e) => setSecurityForm({ ...securityForm, confirmPassword: e.target.value })}
                placeholder="Confirm new password"
                style={{ width: '100%', backgroundColor: '#070b14', border: '1px solid #1e293b', fontSize: '13px' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
              <button
                type="submit"
                className="btn"
                disabled={updatingPassword}
                style={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc', padding: '8px 18px', fontSize: '13px', fontWeight: 600 }}
              >
                {updatingPassword ? 'Updating...' : 'Update Password'}
              </button>
            </div>
          </form>
        </div>

      </div>

      {/* Account Security & Actions Zone */}
      <div className="card" style={{ padding: '20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '10px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#f8fafc', margin: '0 0 4px 0' }}>
            Active Session & Sign Out
          </h4>
          <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
            Sign out of your active UNIVA session on this browser. Your credentials will remain securely stored on backend.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => {
            if (window.confirm("Are you sure you want to sign out?")) {
              onLogout();
            }
          }}
          style={{ padding: '8px 18px', fontSize: '13px', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)', display: 'inline-flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}
        >
          <LogOut size={16} />
          <span>Sign Out of Account</span>
        </button>
      </div>

    </div>
  );
};
