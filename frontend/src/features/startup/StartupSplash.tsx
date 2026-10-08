import React, { useEffect, useState } from 'react';
import { Database, Cpu, AlertTriangle } from 'lucide-react';
import { apiFetch } from '../../config/api';

interface SystemSubsystem {
  status: 'checking' | 'ok' | 'degraded' | 'failed';
  details: string;
}

interface StartupStatus {
  ready: boolean;
  subsystems: {
    duckdb: SystemSubsystem;
    chromadb: SystemSubsystem;
    licensing: SystemSubsystem;
    ollama: SystemSubsystem;
  };
}

interface StartupSplashProps {
  onReady: () => void;
}

export const StartupSplash: React.FC<StartupSplashProps> = ({ onReady }) => {
  const [status, setStatus] = useState<StartupStatus>({
    ready: false,
    subsystems: {
      duckdb: { status: 'checking', details: 'Connecting to DuckDB database...' },
      chromadb: { status: 'checking', details: 'Connecting to ChromaDB vector store...' },
      licensing: { status: 'checking', details: 'Verifying offline RSA license signature...' },
      ollama: { status: 'checking', details: 'Checking local Qwen 3 model...' }
    }
  });
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: any;

    const pollStatus = async () => {
      try {
        const response = await apiFetch('/startup/status');
        if (!response.ok) throw new Error("Backend server error");
        
        const raw = await response.json();
        const subs = raw.subsystems || {
          duckdb: raw.stages?.database,
          chromadb: raw.stages?.knowledge,
          licensing: raw.stages?.licensing,
          ollama: raw.stages?.ollama,
        };

        const structuredData: StartupStatus = {
          ready: Boolean(raw.ready),
          subsystems: {
            duckdb: subs.duckdb || { status: 'ok', details: 'DuckDB columnar engine active' },
            chromadb: subs.chromadb || { status: 'ok', details: 'ChromaDB vector store active' },
            licensing: subs.licensing || { status: 'ok', details: 'Offline license verified' },
            ollama: subs.ollama || { status: 'ok', details: 'Local Ollama service active' }
          }
        };

        setStatus(structuredData);
        setErrorMsg(null);

        if (structuredData.ready) {
          clearInterval(intervalId);
          setTimeout(() => {
            onReady();
          }, 800);
        }
      } catch (err) {
        setErrorMsg("Failed to connect to CLARIUS local API backend. Ensure backend uvicorn is running.");
        setStatus((prev) => ({
          ...prev,
          subsystems: {
            duckdb: { status: 'failed', details: 'Connection lost' },
            chromadb: { status: 'failed', details: 'Connection lost' },
            licensing: { status: 'failed', details: 'Connection lost' },
            ollama: { status: 'failed', details: 'Connection lost' }
          }
        }));
      }
    };

    pollStatus();
    intervalId = setInterval(pollStatus, 1500);

    return () => clearInterval(intervalId);
  }, [onReady]);

  const renderStageRow = (title: string, stage?: SystemSubsystem, Icon?: React.ComponentType<any>) => {
    const currentStage = stage || { status: 'checking', details: 'Checking subsystem status...' };
    const IconComp = Icon || Database;
    let statusText = 'Checking';
    let statusColor = '#f59e0b';
    
    if (currentStage.status === 'ok') {
      statusText = 'Connected';
      statusColor = '#10b981';
    } else if (currentStage.status === 'degraded') {
      statusText = 'Standby';
      statusColor = '#38bdf8';
    } else if (currentStage.status === 'failed') {
      statusText = 'Offline';
      statusColor = '#ef4444';
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
          <IconComp size={20} style={{ color: currentStage.status === 'ok' ? '#38bdf8' : '#94a3b8' }} />
          <div style={{ textAlign: 'left' }}>
            <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{title}</div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>{currentStage.details}</div>
          </div>
        </div>
        <div style={{
          fontSize: '12px',
          fontWeight: 600,
          color: statusColor
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
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.25) 0%, rgba(15, 23, 42, 0.9) 100%)',
          border: '2px solid rgba(56, 189, 248, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 24px rgba(56, 189, 248, 0.4)',
          margin: '0 auto 16px auto'
        }}>
          <img 
            src="/logo.png" 
            alt="CLARIUS Logo" 
            style={{ width: '82%', height: '82%', objectFit: 'contain' }} 
          />
        </div>
        <h1 style={{ color: '#f8fafc', fontWeight: 800, margin: '0 0 4px 0', fontSize: '26px', letterSpacing: '1px' }}>
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
          {renderStageRow("DuckDB CDM Tables", status.subsystems?.duckdb, Database)}
          {renderStageRow("ChromaDB Knowledge", status.subsystems?.chromadb, Database)}
          {renderStageRow("Ollama Local LLM", status.subsystems?.ollama, Cpu)}
        </div>

        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'center' }}>
          <div className="spinner"></div>
        </div>
      </div>
    </div>
  );
};
