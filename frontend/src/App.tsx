import { useState, useEffect } from 'react';
import { StartupSplash } from './features/startup/StartupSplash';
import { SetupWizard } from './features/identity/SetupWizard';
import { LoginForm } from './features/identity/LoginForm';
import { AppShell } from './components/AppShell';

function App() {
  const [booted, setBooted] = useState(false);
  const [isSetup, setIsSetup] = useState<boolean | null>(null);
  
  // User session state
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [username, setUsername] = useState<string>(localStorage.getItem("username") || "");
  const [role, setRole] = useState<string>(localStorage.getItem("role") || "");

  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  // Check setup status once startup splash loading succeeds
  useEffect(() => {
    if (!booted) return;

    const checkSetupStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/auth/status');
        if (response.ok) {
          const data = await response.json();
          setIsSetup(data.is_setup);
          if (!data.is_setup) {
            setAuthMode('signup');
          }
        } else {
          setIsSetup(true);
        }
      } catch (err) {
        console.error("Failed to fetch setup status", err);
        setIsSetup(true);
      }
    };

    checkSetupStatus();
  }, [booted]);

  // Verify active session token on application boot
  useEffect(() => {
    if (!booted || !token) return;

    const validateToken = async () => {
      try {
        const res = await fetch('http://localhost:8000/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.username) setUsername(data.username);
          if (data.role) setRole(data.role);
        } else if (res.status === 401) {
          handleLogout();
        }
      } catch (err) {
        console.error("Failed to validate token:", err);
      }
    };

    validateToken();
  }, [booted]);

  const handleAuthSuccess = (newToken: string, newUsername: string, newRole: string) => {
    localStorage.setItem("token", newToken);
    localStorage.setItem("username", newUsername);
    localStorage.setItem("role", newRole);
    
    setToken(newToken);
    setUsername(newUsername);
    setRole(newRole);
    setIsSetup(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    
    setToken(null);
    setUsername("");
    setRole("");
    setAuthMode('login');
  };

  // 1. Stage: Startup loader
  if (!booted) {
    return <StartupSplash onReady={() => setBooted(true)} />;
  }

  // 2. Stage: Setup check in progress
  if (isSetup === null) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: '#0b0c10',
        color: '#9ca3af'
      }}>
        <div className="spinner"></div>
      </div>
    );
  }

  // If user is logged in, show workspace shell directly
  if (token) {
    return (
      <AppShell 
        username={username}
        role={role}
        onLogout={handleLogout}
      />
    );
  }

  // Render Signup or Login based on active authMode tab state
  if (authMode === 'signup') {
    return <SetupWizard onSetupSuccess={handleAuthSuccess} onToggleLogin={() => setAuthMode('login')} />;
  }

  // Default: Show Login Form
  return <LoginForm onLoginSuccess={handleAuthSuccess} onToggleSetup={() => setAuthMode('signup')} />;
}

export default App;
