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

  // Check setup status once startup splash loading succeeds
  useEffect(() => {
    if (!booted) return;

    const checkSetupStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/auth/status');
        if (response.ok) {
          const data = await response.json();
          setIsSetup(data.is_setup);
        }
      } catch (err) {
        console.error("Failed to fetch setup status", err);
      }
    };

    checkSetupStatus();
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

  // 3. Stage: Setup wizard for first Owner creation
  if (!isSetup) {
    return <SetupWizard onSetupSuccess={handleAuthSuccess} />;
  }

  // 4. Stage: LoginForm for returning users
  if (!token) {
    return <LoginForm onLoginSuccess={handleAuthSuccess} />;
  }

  // 5. Stage: App workspace dashboard shell
  return (
    <AppShell 
      username={username}
      role={role}
      onLogout={handleLogout}
    />
  );
}

export default App;
