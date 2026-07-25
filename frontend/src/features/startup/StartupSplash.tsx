import React, { useEffect, useState } from 'react';
import { ShieldCheck, Database, FileText, Cpu, AlertTriangle } from 'lucide-react';

interface StartupStage {
  status: 'ok' | 'failed' | 'checking';
  details: string;
}

interface StartupStatus {
  ready: boolean;
  stages: {
    licensing: StartupStage;
    database: StartupStage;
    knowledge: StartupStage;
    ollama: StartupStage;
  };
}

interface StartupSplashProps {
  onReady: () => void;
}

export const StartupSplash: React.FC<StartupSplashProps> = ({ onReady }) => {
  const [status, setStatus] = useState<StartupStatus>({
    ready: false,
    stages: {
      licensing: { status: 'checking', details: 'Checking signature...' },
      database: { status: 'checking', details: 'Connecting to DuckDB...' },
      knowledge: { status: 'checking', details: 'Checking ChromaDB...' },
      ollama: { status: 'checking', details: 'Checking local Qwen 3 model...' }
    }
  });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: any;

    const pollStatus = async () => {
      try {
        const response = await fetch('http://localhost:8000/startup/status');
        if (!response.ok) throw new Error("Backend server error");
        
        const data = (await response.json()) as StartupStatus;
        setStatus(data);
        setErrorMsg(null);

        if (data.ready) {
          clearInterval(intervalId);
          // Wait 1 second for visual satisfaction before navigating
          setTimeout(() => {
            onReady();
          }, 1000);
        }
      } catch (err) {
        setErrorMsg("Failed to connect to CLARIUS API sidecar. Ensure backend is running.");
        setStatus((prev) => ({
          ...prev,
          stages: {
            licensing: { status: 'failed', details: 'Connection lost' },
            database: { status: 'failed', details: 'Connection lost' },
            knowledge: { status: 'failed', details: 'Connection lost' },
            ollama: { status: 'failed', details: 'Connection lost' }
          }
        }));
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 1500);

    return () => clearInterval(intervalId);
  }, [onReady]);

  const renderStageRow = (title: string, stage: StartupStage, Icon: React.ComponentType<any>) => {
    let statusText = 'Checking';
    
    if (stage.status === 'ok') {
      statusText = 'Connected';
    } else if (stage.status === 'failed') {
      statusText = 'Offline';
    }

    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        backgroundColor: '#0d131f',
        border: '1px solid #1e293b',
        borderRadius: '6px',
        marginBottom: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon size={20} style={{ color: stage.status === 'ok' ? '#3b82f6' : '#94a3b8' }} />
          <div style={{ textAlign: 'left' }}>
            <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{title}</div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{stage.details}</div>
          </div>
        </div>
        <div style={{
          fontSize: '12px',
          fontWeight: 600,
          color: stage.status === 'ok' ? '#10b981' : stage.status === 'failed' ? '#ef4444' : '#f59e0b'
        }}>
          {statusText}
        </div>
      </div>
    );
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      width: '100vw',
      backgroundColor: '#090d16',
      padding: '20px',
      boxSizing: 'border-box'
    }}>
      <div style={{ width: '100%', maxWidth: '440px', textAlign: 'center' }}>
        <h1 style={{ color: '#f8fafc', fontWeight: 800, margin: '0 0 4px 0', fontSize: '24px', letterSpacing: '1px' }}>
          CLARIUS
        </h1>
        <p style={{ color: '#94a3b8', marginBottom: '24px', fontSize: '13px' }}>
          Booting Privacy-Centric Business Intelligence
        </p>

        {errorMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            backgroundColor: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '6px',
            padding: '10px 14px',
            color: '#ef4444',
            marginBottom: '16px',
            fontSize: '13px',
            textAlign: 'left'
          }}>
            <AlertTriangle size={18} style={{ flexShrink: 0 }} />
            <div>{errorMsg}</div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {renderStageRow("Offline Licensing", status.stages.licensing, ShieldCheck)}
          {renderStageRow("DuckDB CDM Tables", status.stages.database, Database)}
          {renderStageRow("ChromaDB Knowledge", status.stages.knowledge, FileText)}
          {renderStageRow("Ollama Local LLM", status.stages.ollama, Cpu)}
        </div>

        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'center' }}>
          <div className="spinner"></div>
        </div>
      </div>
    </div>
  );
};
