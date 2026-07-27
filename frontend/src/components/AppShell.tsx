import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, LayoutDashboard, Database, Settings, LogOut, 
  User, Activity, RefreshCw, Layers, UploadCloud, FileText, Send, ArrowRight,
  TrendingUp, Cpu, Compass, FileSpreadsheet, Users, Building2, GitFork, History, Award, BookOpen,
  ChevronLeft, ChevronRight, MoreVertical, Eye, Pencil
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { ColumnsMapper } from '../features/sources/ColumnsMapper';

interface AppShellProps {
  username: string;
  role: string;
  onLogout: () => void;
}

interface ChatMessage {
  sender: 'user' | 'clarius';
  text: string;
  timestamp: Date;
  type?: 'text' | 'sql_result' | 'rag_result';
  sql?: string;
  tableData?: {
    columns: string[];
    rows: any[];
  };
  chartOptions?: any;
  ragDocs?: any[];
}

export const AppShell: React.FC<AppShellProps> = ({ username, role, onLogout }) => {
  const [activeMenu, setActiveMenu] = useState<'assistant' | 'dashboards' | 'sources' | 'documents' | 'settings' | 'insights' | 'analytics' | 'reports' | 'businessdata' | 'usersroles' | 'organization' | 'branches' | 'integrations' | 'synclogs' | 'license' | 'auditlogs'>('assistant');
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Preview tables catalog states (Dashboard)
  const [activePreviewTable, setActivePreviewTable] = useState<string | null>(null);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Kebab menu item lists & active indices
  const [activeKebabDoc, setActiveKebabDoc] = useState<number | null>(null);
  const [activeKebabSource, setActiveKebabSource] = useState<number | null>(null);
  const [docList, setDocList] = useState<{name: string, type: string, size: string, status: string, details?: string}[]>([]);
  const [sourceFilesList, setSourceFilesList] = useState<{name: string, type: string, size: string, status: string, details?: string}[]>([]);
  const [matrixPermissions, setMatrixPermissions] = useState([
    { role: 'Owner / Admin', permissions: [true, true, true, true, true, true] },
    { role: 'Manager', permissions: [true, true, true, true, false, false] },
    { role: 'Analyst', permissions: [true, false, true, false, false, false] },
    { role: 'Staff', permissions: [true, false, false, false, false, false] },
    { role: 'Sales Executive', permissions: [true, false, false, false, false, false] }
  ]);
  const [viewingFileDetail, setViewingFileDetail] = useState<{name: string, type: string, size: string, details: string, columns?: string[], data?: any[]} | null>(null);

  const getRolePriority = (roleName: string): number => {
    const r = roleName.toLowerCase();
    if (r.includes('owner') || r.includes('admin')) return 4;
    if (r.includes('manager')) return 3;
    if (r.includes('analyst')) return 2;
    if (r.includes('staff')) return 1;
    if (r.includes('sales')) return 0;
    return 0;
  };
  
  // Settings tab states
  const [settingsSubTab, setSettingsSubTab] = useState<'licensing' | 'users' | 'llm' | 'audit'>('licensing');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState('analyst');
  const [userStatus, setUserStatus] = useState<string | null>(null);
  const [licenseText, setLicenseText] = useState('');
  const [licStatus, setLicStatus] = useState<string | null>(null);
  
  // Local LLM config
  const [ollamaHost, setOllamaHost] = useState(localStorage.getItem('ollama_host') || 'http://localhost:11434');
  const [ollamaModel, setOllamaModel] = useState(localStorage.getItem('ollama_model') || 'qwen3:4b-instruct');
  const [llmStatus, setLlmStatus] = useState<string | null>(null);

  // Unified Chat / AI Assistant States
  const [queryText, setQueryText] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [activeStage, setActiveStage] = useState<string>('none');

  // Document upload / OCR Ingest states
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('policy');
  const [docTitle, setDocTitle] = useState('');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Dashboards states
  const [dashboards, setDashboards] = useState<any[]>([]);

  // Audit logs state
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Sync state
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success'>('idle');
  const [syncTime, setSyncTime] = useState<string>('Today, 10:32 AM');

  // ERP integration connection states
  const [connectedErps, setConnectedErps] = useState<Record<string, boolean>>({
    TallyPrime: false,
    Odoo: false,
    ERPNext: false,
    BUSY: false,
    Marg: false,
    Zoho: false
  });
  const [configuringErp, setConfiguringErp] = useState<string | null>(null);
  const [erpServerUrl, setErpServerUrl] = useState('');
  const [erpCompanyName, setErpCompanyName] = useState('');
  const [erpUsername, setErpUsername] = useState('');
  const [erpPassword, setErpPassword] = useState('');
  const [erpApiKey, setErpApiKey] = useState('');
  const [erpOrgId, setErpOrgId] = useState('');

  // Inline Semantic Search Console states (for Knowledge base)
  const [localRagQuery, setLocalRagQuery] = useState('');
  const [localRagLoading, setLocalRagLoading] = useState(false);
  const [localRagResults, setLocalRagResults] = useState<any[]>([]);
  const [localRagError, setLocalRagError] = useState<string | null>(null);

  // Trigger sync simulation
  const handleSyncNow = () => {
    setSyncStatus('syncing');
    setTimeout(() => {
      setSyncStatus('success');
      setSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      setTimeout(() => setSyncStatus('idle'), 3000);
    }, 2000);
  };
  const handleTogglePermission = (roleIdx: number, permIdx: number, targetRole: string) => {
    const currentUserPriority = getRolePriority(role);
    const targetUserPriority = getRolePriority(targetRole);
    
    if (currentUserPriority <= targetUserPriority) {
      alert(`Access Denied: As a ${role}, you are unauthorized to modify permissions for the equal or higher priority role "${targetRole}".`);
      return;
    }
    
    setMatrixPermissions(prev => {
      const updated = [...prev];
      const targetPermissions = [...updated[roleIdx].permissions];
      targetPermissions[permIdx] = !targetPermissions[permIdx];
      updated[roleIdx] = {
        ...updated[roleIdx],
        permissions: targetPermissions
      };
      return updated;
    });
  };

  const handleViewTableDetails = async (tableName: string) => {
    try {
      const res = await fetch(`http://localhost:8000/data-sources/preview/${tableName}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setViewingFileDetail({
          name: tableName,
          type: 'DuckDB Table Schema',
          size: `${data.data ? data.data.length : 0} Rows Mapped`,
          details: '',
          columns: data.columns || [],
          data: data.data || []
        });
      } else {
        alert(`Table "${tableName}" has no active relation or records in the database.`);
      }
    } catch (err) {
      console.error("Failed to load table details", err);
    }
  };

  const handlePreviewTable = async (tableName: string) => {
    setPreviewLoading(true);
    setActivePreviewTable(tableName);
    setPreviewCols([]);
    setPreviewData([]);
    try {
      const res = await fetch(`http://localhost:8000/data-sources/preview/${tableName}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPreviewCols(data.columns || []);
        setPreviewData(data.data || []);
      }
    } catch (err) {
      console.error("Failed to load table preview", err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleLocalRagSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localRagQuery.trim()) return;

    setLocalRagLoading(true);
    setLocalRagError(null);
    setLocalRagResults([]);

    try {
      const res = await fetch(`http://localhost:8000/documents/query?q=${encodeURIComponent(localRagQuery)}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLocalRagResults(data.results || []);
      } else {
        throw new Error();
      }
    } catch (err) {
      setLocalRagError("Failed to query knowledge base.");
    } finally {
      setLocalRagLoading(false);
    }
  };

  const handleSaveErpConnection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!configuringErp) return;
    
    setConnectedErps(prev => ({
      ...prev,
      [configuringErp]: true
    }));
    setConfiguringErp(null);
    setErpServerUrl('');
    setErpCompanyName('');
    setErpUsername('');
    setErpPassword('');
    setErpApiKey('');
    setErpOrgId('');
  };

  // Fetch dashboards catalog on mount
  useEffect(() => {
    const fetchDashboards = async () => {
      try {
        const res = await fetch('http://localhost:8000/dashboards', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) {
          const data = await res.json();
          setDashboards(data);
        }
      } catch (err) {
        console.error("Failed to load dashboards catalog", err);
      }
    };
    fetchDashboards();
  }, [activeMenu]);

  // Load Audit logs
  const fetchAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const res = await fetch('http://localhost:8000/auth/audit', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data);
      }
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    if (activeMenu === 'settings' && settingsSubTab === 'audit') {
      fetchAuditLogs();
    }
  }, [activeMenu, settingsSubTab]);

  // Unified Query Submit (routes automatically or queries semantic RAG & SQL side-by-side/sequentially)
  const handleUnifiedQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim()) return;

    const userMsg: ChatMessage = {
      sender: 'user',
      text: queryText,
      timestamp: new Date()
    };

    setChatHistory(prev => [...prev, userMsg]);
    const currentQuery = queryText;
    setQueryText('');
    setChatLoading(true);
    setActiveStage('schema_discovery');

    // Try SQL query translation first (using SSE analytics stream)
    const eventSource = new EventSource(`http://localhost:8000/analytics/stream?q=${encodeURIComponent(currentQuery)}`);
    let completed = false;

    eventSource.addEventListener('stage', (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data);
        setActiveStage(payload.stage);
      } catch (err) {
        console.error("Failed to parse stage SSE payload", err);
      }
    });

    eventSource.addEventListener('completed', (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data);
        completed = true;
        eventSource.close();
        setChatLoading(false);
        setActiveStage('none');

        // Execute UI Navigation action if returned
        if (payload.ui_action && payload.ui_action.startsWith("navigate_")) {
          const menu = payload.ui_action.replace("navigate_", "");
          let targetMenu = menu;
          if (menu === "inventory") targetMenu = "businessdata";
          else if (menu === "dashboard") targetMenu = "dashboards";
          setActiveMenu(targetMenu);
        }

        // Check if chart options exist
        const options = payload.chart_spec ? JSON.parse(payload.chart_spec) : null;

        const responseMsg: ChatMessage = {
          sender: 'clarius',
          text: payload.explanation || "Query completed successfully.",
          timestamp: new Date(),
          type: 'sql_result',
          sql: payload.generated_sql,
          tableData: {
            columns: payload.columns || [],
            rows: payload.results || []
          },
          chartOptions: options
        };

        setChatHistory(prev => [...prev, responseMsg]);
      } catch (err) {
        console.error("Failed to parse completed SSE payload", err);
        eventSource.close();
        setChatLoading(false);
        setActiveStage('none');
      }
    });

    eventSource.addEventListener('error', async () => {
      eventSource.close();
      if (completed) return;

      // Fallback: Query documents knowledge base (RAG search) if SQL translation fails or finds no table structure
      try {
        setActiveStage('knowledge_retrieval');
        const res = await fetch(`http://localhost:8000/documents/query?q=${encodeURIComponent(currentQuery)}`, {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        
        if (res.ok) {
          const data = await res.json();
          const docs = data.results || [];
          
          if (docs.length > 0) {
            const bestContent = docs[0].content || "";
            const responseMsg: ChatMessage = {
              sender: 'clarius',
              text: `Here is what I found in your documents knowledge base regarding your request:\n\n${bestContent.slice(0, 300)}...`,
              timestamp: new Date(),
              type: 'rag_result',
              ragDocs: docs
            };
            setChatHistory(prev => [...prev, responseMsg]);
          } else {
            const responseMsg: ChatMessage = {
              sender: 'clarius',
              text: "I couldn't find any relevant structured data or document references matching your query.",
              timestamp: new Date()
            };
            setChatHistory(prev => [...prev, responseMsg]);
          }
        } else {
          throw new Error();
        }
      } catch (err) {
        const responseMsg: ChatMessage = {
          sender: 'clarius',
          text: "I encountered an issue connecting to local server intelligence services. Please verify that Ollama is online.",
          timestamp: new Date()
        };
        setChatHistory(prev => [...prev, responseMsg]);
      } finally {
        setChatLoading(false);
        setActiveStage('none');
      }
    });
  };

  // Handle document upload
  const handleDocUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docFile) return;

    setUploadStatus("Uploading & executing local OCR pipelines...");
    
    const formData = new FormData();
    formData.append("file", docFile);
    formData.append("doc_type", docType);
    if (docTitle) formData.append("title", docTitle);

    try {
      const res = await fetch('http://localhost:8000/documents/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData
      });

      if (!res.ok) throw new Error("Upload failed");
      
      setUploadStatus("Ingest success! Document OCR text extracted and indexed into knowledge base.");
      setDocList(prev => [
        ...prev,
        {
          name: docTitle || docFile.name,
          type: docType.toUpperCase(),
          size: (docFile.size / 1024).toFixed(1) + ' KB',
          status: 'Indexed',
          details: `Ingested document: ${docTitle || docFile.name}. Parsed type: ${docType}. Content extracted in the background via local OCR processor.`
        }
      ]);
      setDocFile(null);
      setDocTitle('');
    } catch (err) {
      setUploadStatus("Failed to extract text from document.");
    }
  };

  // Create workspace user
  const handleUserCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername || !newPassword) return;

    setUserStatus("Creating local user profile...");
    try {
      const res = await fetch('http://localhost:8000/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ username: newUsername, password: newPassword, role: newUserRole })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to create user");
      }
      setUserStatus("User workspace created successfully!");
      setNewUsername('');
      setNewPassword('');
    } catch (err: any) {
      setUserStatus(`Error: ${err.message}`);
    }
  };

  // Import Offline License
  const handleLicenseImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!licenseText) return;

    setLicStatus("Verifying license key signature...");
    try {
      const res = await fetch('http://localhost:8000/upgrade/license', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ license_key: licenseText })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "License signature verification failed");
      }

      setLicStatus("License imported successfully! Edition features updated.");
      setLicenseText('');
    } catch (err: any) {
      setLicStatus(`Error: ${err.message}`);
    }
  };

  // Save local LLM Settings
  const handleLlmSave = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem('ollama_host', ollamaHost);
    localStorage.setItem('ollama_model', ollamaModel);
    setLlmStatus("LLM Integration parameters saved.");
    setTimeout(() => setLlmStatus(null), 3000);
  };

  // Check role-based capabilities (RBAC)
  const isOwnerOrAdmin = role === 'owner' || role === 'admin';

  // Render unified AI Chat Assistant
  const renderChatAssistant = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', border: '1px solid #1e293b', borderRadius: '8px', backgroundColor: '#0c1220', overflow: 'hidden' }}>
        
        {/* Chat area header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #1e293b', backgroundColor: 'rgba(15, 23, 42, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <MessageSquare size={18} style={{ color: '#3b82f6' }} />
            <div>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>Ask CLARIUS Assistant</div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>Standalone Offline Model: {ollamaModel}</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
            <span style={{ fontSize: '12px', color: '#10b981' }}>Inference Active</span>
          </div>
        </div>

        {/* Messaging Area */}
        <div style={{ flexGrow: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {chatHistory.length === 0 ? (
            <div style={{ margin: 'auto', maxWidth: '500px', textAlign: 'center', padding: '40px 20px' }}>
              <Cpu size={40} style={{ color: '#3b82f6', marginBottom: '16px', opacity: 0.8 }} />
              <h3 style={{ color: '#f8fafc', margin: '0 0 8px 0', fontSize: '16px', fontWeight: 600 }}>Welcome to CLARIUS</h3>
              <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 24px 0', lineHeight: 1.5 }}>
                Query your local databases and uploaded documents in natural language. Queries are processed entirely offline inside your secure server.
              </p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px', textAlign: 'left' }}>
                <button className="btn btn-secondary" onClick={() => setQueryText("What were our sales transactions details?")} style={{ justifyContent: 'flex-start', padding: '10px 14px' }}>
                  <ArrowRight size={14} style={{ color: '#3b82f6' }} />
                  <span>"What were our sales transactions details?"</span>
                </button>
                <button className="btn btn-secondary" onClick={() => setQueryText("Identify inventory items below reorder point.")} style={{ justifyContent: 'flex-start', padding: '10px 14px' }}>
                  <ArrowRight size={14} style={{ color: '#3b82f6' }} />
                  <span>"Identify inventory items below reorder point."</span>
                </button>
                <button className="btn btn-secondary" onClick={() => setQueryText("What does our purchase policy specify?")} style={{ justifyContent: 'flex-start', padding: '10px 14px' }}>
                  <ArrowRight size={14} style={{ color: '#3b82f6' }} />
                  <span>"What does our purchase policy specify?"</span>
                </button>
              </div>
            </div>
          ) : (
            chatHistory.map((msg, idx) => (
              <div key={idx} style={{ 
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                <div style={{ 
                  padding: '12px 16px', 
                  borderRadius: '8px', 
                  backgroundColor: msg.sender === 'user' ? '#3b82f6' : '#1e293b', 
                  color: '#ffffff',
                  fontSize: '13px',
                  lineHeight: '1.5',
                  boxShadow: 'var(--shadow)'
                }}>
                  {msg.text}
                </div>

                {/* Show SQL results */}
                {msg.type === 'sql_result' && (
                  <div className="card" style={{ padding: '16px', backgroundColor: '#0d131f', border: '1px solid #1e293b', marginTop: '4px' }}>
                    
                    {/* Render EChart if chart options are available */}
                    {msg.chartOptions && (
                      <div style={{ marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '16px' }}>
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', marginBottom: '10px' }}>Visual Trend Output</div>
                        <ReactECharts option={msg.chartOptions} style={{ height: '240px' }} theme="dark" />
                      </div>
                    )}

                    {msg.tableData && msg.tableData.rows.length > 0 && (() => {
                      const tbl = msg.tableData;
                      return (
                        <div style={{ overflowX: 'auto', marginBottom: '12px' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
                            <thead>
                              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                                {tbl.columns.map((col, cIdx) => (
                                  <th key={cIdx} style={{ padding: '8px 6px', color: '#f8fafc' }}>{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {tbl.rows.slice(0, 5).map((row, rIdx) => (
                                <tr key={rIdx} style={{ borderBottom: '1px solid #1e293b' }}>
                                  {tbl.columns.map((col, cIdx) => (
                                    <td key={cIdx} style={{ padding: '8px 6px', color: '#94a3b8' }}>{row[col]?.toString() || ''}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {tbl.rows.length > 5 && (
                            <div style={{ fontSize: '10px', color: '#94a3b8', padding: '6px', textAlign: 'center' }}>
                              Showing 5 of {tbl.rows.length} rows. Export to review full dataset.
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {/* Generated SQL snippet */}
                    {msg.sql && (
                      <details style={{ marginTop: '8px' }}>
                        <summary style={{ cursor: 'pointer', fontSize: '11px', color: '#3b82f6', outline: 'none' }}>
                          View Executed SQL Statement
                        </summary>
                        <pre style={{ margin: '8px 0 0 0', padding: '10px', backgroundColor: '#090d16', borderRadius: '4px', fontSize: '11px', color: '#94a3b8', overflowX: 'auto', fontFamily: 'var(--mono)' }}>
                          {msg.sql}
                        </pre>
                      </details>
                    )}
                  </div>
                )}

                {/* Show RAG reference citations */}
                {msg.type === 'rag_result' && msg.ragDocs && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#f8fafc' }}>Knowledge Source Citations:</div>
                    {msg.ragDocs.map((doc, dIdx) => (
                      <div key={dIdx} style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600, color: '#3b82f6' }}>{doc.title || "Policy Document"}</span>
                          <span style={{ fontSize: '10px', color: '#94a3b8' }}>Match: {Number(doc.distance || 0).toFixed(4)}</span>
                        </div>
                        <div style={{ color: '#94a3b8', lineHeight: 1.4 }}>{doc.content}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}

          {chatLoading && (
            <div style={{ alignSelf: 'flex-start', display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '80%' }}>
              <div style={{ padding: '12px 16px', borderRadius: '8px', backgroundColor: '#1e293b', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="spinner" style={{ width: '12px', height: '12px' }}></span>
                <span style={{ fontSize: '13px', color: '#94a3b8' }}>Thinking... ({activeStage.replace('_', ' ')})</span>
              </div>
              <div style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '11px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div>• Schema Mapping Check: <span style={{ color: '#10b981' }}>OK</span></div>
                  <div>• secure SQL compiler: <span style={{ color: activeStage === 'schema_discovery' ? '#f59e0b' : '#10b981' }}>{activeStage === 'schema_discovery' ? 'Processing...' : 'OK'}</span></div>
                  <div>• DB Execution Engine: <span style={{ color: activeStage === 'sql_generation' ? '#f59e0b' : activeStage === 'schema_discovery' ? '#94a3b8' : '#10b981' }}>{activeStage === 'sql_generation' ? 'Executing query...' : activeStage === 'schema_discovery' ? 'Pending' : 'OK'}</span></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <form onSubmit={handleUnifiedQuery} style={{ padding: '16px 20px', borderTop: '1px solid #1e293b', backgroundColor: 'rgba(15, 23, 42, 0.4)', display: 'flex', gap: '10px' }}>
          <input 
            type="text" 
            className="input-field"
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="Ask CLARIUS anything about your business data, documents, or performance..."
            disabled={chatLoading}
          />
          <button type="submit" className="btn btn-primary" disabled={chatLoading}>
            <Send size={14} />
          </button>
        </form>

      </div>
    );
  };

  // Render business overview Dashboard
  const renderDashboard = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Business Intelligence Dashboard</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Real-time Key Performance Indicators calculated from connected database schemas.</p>
        </div>

        {dashboards.length === 0 ? (
          <div style={{ padding: '60px 20px', textAlign: 'center', border: '1px dashed #1e293b', borderRadius: '8px', backgroundColor: '#0d131f' }}>
            <Activity size={32} style={{ color: '#94a3b8', marginBottom: '12px' }} />
            <h3 style={{ color: '#f8fafc', margin: '0 0 6px 0', fontSize: '15px' }}>No active business metrics</h3>
            <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 20px 0' }}>
              Connect your local ERP systems or upload CSV/Excel files to populate KPI indicators.
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
              <button className="btn btn-primary" onClick={() => setActiveMenu('sources')}>Connect Data Source</button>
              <button className="btn btn-secondary" onClick={() => setActiveMenu('assistant')}>Ask CLARIUS</button>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* KPI grid */}
            <div className="grid-3">
              <div className="card">
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', marginBottom: '8px' }}>Ingested Transactions</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>{dashboards.length} Tables</div>
                <div style={{ fontSize: '11px', color: '#10b981', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <TrendingUp size={12} />
                  <span>Schema connected correctly</span>
                </div>
              </div>
              <div className="card">
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', marginBottom: '8px' }}>Secure Storage</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>Local SQLite/DuckDB</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>100% on-premises containment</div>
              </div>
              <div className="card">
                <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', marginBottom: '8px' }}>Data synchronization</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>Active Sync</div>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>Last sync: {syncTime}</div>
              </div>
            </div>

            {/* List of active tables */}
            <div className="card">
              <div className="card-title">Registered Database Schemas</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Schema Name</th>
                      <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Type</th>
                      <th style={{ padding: '10px 8px', color: '#f8fafc', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboards.map((dash: any, idx: number) => {
                      const name = typeof dash === 'object' && dash !== null ? dash.name : String(dash);
                      const desc = typeof dash === 'object' && dash !== null ? (dash.description || 'Dashboard Template') : 'DuckDB Relation Table';
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                          <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>{name}</td>
                          <td style={{ padding: '10px 8px', color: '#94a3b8' }}>{desc}</td>
                          <td style={{ padding: '10px 8px', textAlign: 'right', display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                            <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => handlePreviewTable(name)}>
                              Preview
                            </button>
                            <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => handleViewTableDetails(name)}>
                              View
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Active Preview Table Rows */}
            {activePreviewTable && (
              <div className="card" style={{ borderLeft: '3px solid #3b82f6' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div className="card-title" style={{ margin: 0, textTransform: 'capitalize', fontSize: '14px' }}>
                    Preview: {activePreviewTable.replace(/_/g, ' ')} (Top 5 Records)
                  </div>
                  <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => setActivePreviewTable(null)}>
                    Close Preview
                  </button>
                </div>
                {previewLoading ? (
                  <div style={{ color: '#3b82f6', fontSize: '13px' }}>Loading rows...</div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #1e293b' }}>
                          {previewCols.map((col) => (
                            <th key={col} style={{ padding: '8px 6px', color: '#f8fafc', fontWeight: 600 }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.length === 0 ? (
                          <tr>
                            <td colSpan={previewCols.length || 1} style={{ padding: '12px 6px', textAlign: 'center', color: '#94a3b8' }}>
                              No records stored in this table.
                            </td>
                          </tr>
                        ) : (
                          previewData.map((row, rIdx) => (
                            <tr key={rIdx} style={{ borderBottom: '1px solid #1e293b' }}>
                              {previewCols.map((col) => (
                                <td key={col} style={{ padding: '8px 6px', color: '#94a3b8' }}>{String(row[col] ?? '')}</td>
                              ))}
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

          </div>
        )}
      </div>
    );
  };

  // Render Data Sources configuration
  const renderDataSources = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Connected Business Data Sources</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Integrate your local ERP platforms, import documents, or load file sheets.</p>
        </div>

        <div className="grid-2">
          {/* ERP Connectors */}
          <div className="card">
            <div className="card-title">
              <span>ERP & Accounting Connectors</span>
              <span className="badge badge-success" style={{ textTransform: 'capitalize' }}>Plugin Active</span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '10px' }}>
              {['TallyPrime', 'Odoo ERP', 'ERPNext', 'BUSY', 'Marg ERP', 'Zoho Books'].map((erpKey) => {
                const isConnected = connectedErps[erpKey];
                return (
                  <div key={erpKey} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', backgroundColor: isConnected ? 'rgba(16, 185, 129, 0.02)' : 'rgba(255, 255, 255, 0.01)', borderRadius: '6px', border: '1px solid #1e293b', opacity: isConnected ? 1 : 0.7 }}>
                    <div>
                      <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{erpKey} Connection</div>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>{isConnected ? `Last Sync: ${syncTime}` : 'Offline system disconnected'}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
                      <span className={`badge ${isConnected ? 'badge-success' : 'badge-failed'}`}>{isConnected ? 'Connected' : 'Disconnected'}</span>
                      {isConnected ? (
                        <>
                          <button className="btn btn-secondary" onClick={handleSyncNow} style={{ padding: '4px 8px' }}>
                            {syncStatus === 'syncing' ? <RefreshCw className="spinner" size={12} /> : <RefreshCw size={12} />}
                          </button>
                          <button className="btn btn-secondary" onClick={() => setConnectedErps(prev => ({ ...prev, [erpKey]: false }))} style={{ padding: '4px 8px', fontSize: '10px', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                            Disconnect
                          </button>
                        </>
                      ) : (
                        <button className="btn btn-primary" onClick={() => setConfiguringErp(erpKey)} style={{ padding: '4px 10px', fontSize: '11px' }}>
                          Connect
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Document Ingestion & OCR */}
          <div className="card">
            <div className="card-title">Extract Text & Documents Knowledge (OCR)</div>
            <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 16px 0' }}>
              Upload local policies, scanned manuals, delivery notes, or Challans to embed in semantic search.
            </p>

            <form onSubmit={handleDocUpload} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Document Category</label>
                <select 
                  className="input-field" 
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  <option value="policy">Company Policy / Manual</option>
                  <option value="invoice">Invoice / Purchase Bill</option>
                  <option value="challan">Delivery Challan</option>
                  <option value="sop">Operational SOP</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Document Title</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="e.g. Sales Invoices 2026"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                />
              </div>

              <div style={{ border: '1px dashed #1e293b', borderRadius: '6px', padding: '16px', textAlign: 'center', backgroundColor: 'rgba(255, 255, 255, 0.01)' }}>
                <UploadCloud size={24} style={{ color: '#94a3b8', marginBottom: '8px' }} />
                <input 
                  type="file" 
                  id="doc-file-input"
                  style={{ display: 'none' }}
                  onChange={(e) => setDocFile(e.target.files ? e.target.files[0] : null)}
                />
                <label htmlFor="doc-file-input" style={{ cursor: 'pointer', color: '#3b82f6', fontSize: '13px', display: 'block' }}>
                  {docFile ? docFile.name : "Select local PDF or scanned document"}
                </label>
              </div>

              <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                Import & Extract Text
              </button>
            </form>

            {uploadStatus && (
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#3b82f6', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Activity size={12} className="spinner" />
                <span>{uploadStatus}</span>
              </div>
            )}
          </div>
        </div>

        {/* File Ingestion columns mapper */}
        <div className="card">
          <div className="card-title">CSV & Spreadsheet Schema Mapper</div>
          <ColumnsMapper onIngestSuccess={(fileName, format, size) => {
            setSourceFilesList(prev => [
              ...prev,
              {
                name: fileName,
                type: format,
                size: size,
                status: 'Mapped',
                details: `Source sheet: ${fileName} mapped successfully into active DuckDB schema catalog as a structured relation.`
              }
            ]);
          }} />
        </div>

        {/* Connected Business Data Sources Files List */}
        <div className="card">
          <div className="card-title">Connected Business Data Files</div>
          {sourceFilesList.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
              No custom CSV/Excel/JSON spreadsheets mapped yet. Use the mapper above to ingest files.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {sourceFilesList.map((fileItem, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', position: 'relative' }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{fileItem.name}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Format: {fileItem.type} | Size: {fileItem.size} | Status: <span style={{ color: '#10b981' }}>{fileItem.status}</span></div>
                  </div>
                  <div>
                    <button className="btn btn-secondary" style={{ padding: '4px' }} onClick={() => setActiveKebabSource(activeKebabSource === idx ? null : idx)}>
                      <MoreVertical size={14} />
                    </button>

                    {activeKebabSource === idx && (
                      <div style={{ position: 'absolute', right: '12px', top: '40px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', zIndex: 10, display: 'flex', flexDirection: 'column', padding: '4px', gap: '2px', boxShadow: 'var(--shadow)' }}>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px', gap: '6px', border: 'none', display: 'flex', alignItems: 'center' }} onClick={() => { setViewingFileDetail({ name: fileItem.name, type: fileItem.type, size: fileItem.size, details: fileItem.details || `Schema mapped into active DuckDB relation. Columns catalog matches mapped target entity mappings.` }); setActiveKebabSource(null); }}>
                          <Eye size={12} style={{ color: '#3b82f6' }} />
                          <span>View Data</span>
                        </button>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px', gap: '6px', border: 'none', display: 'flex', alignItems: 'center' }} onClick={() => { alert(`Editing schema details for ${fileItem.name}`); setActiveKebabSource(null); }}>
                          <Pencil size={12} style={{ color: '#f59e0b' }} />
                          <span>Edit Schema</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render documents RAG search
  const renderDocuments = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Business Knowledge base</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Browse and search documents ingested into the offline vector knowledge base.</p>
        </div>
        
        {/* Inline Semantic Search Form */}
        <div className="card">
          <div className="card-title">Search Ingested Knowledge Base</div>
          <form onSubmit={handleLocalRagSearch} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <input 
              type="text" 
              className="input-field" 
              placeholder="Search concepts, policies, manuals, or bills..."
              value={localRagQuery}
              onChange={(e) => setLocalRagQuery(e.target.value)}
              disabled={localRagLoading}
            />
            <button type="submit" className="btn btn-primary" disabled={localRagLoading}>
              {localRagLoading ? 'Searching...' : 'Search'}
            </button>
          </form>

          {localRagError && <div style={{ color: '#ef4444', fontSize: '13px', marginBottom: '12px' }}>{localRagError}</div>}

          {localRagResults.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {localRagResults.map((doc, idx) => (
                <div key={idx} style={{ padding: '12px 14px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: '#3b82f6', fontSize: '13px' }}>{doc.title || "Policy Document"}</span>
                    <span style={{ fontSize: '10px', color: '#94a3b8' }}>Relevance Score: {Number(doc.distance || 0).toFixed(4)}</span>
                  </div>
                  <p style={{ margin: 0, color: '#94a3b8', fontSize: '12px', lineHeight: 1.4 }}>{doc.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">Indexed Knowledge Base Documents</div>
          {docList.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
              No custom PDF/SOP policy manuals indexed yet. Upload documents using the OCR tool in Data Sources.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {docList.map((doc, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', position: 'relative' }}>
                  <div>
                    <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{doc.name}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Type: {doc.type} | Size: {doc.size} | Status: <span style={{ color: '#10b981' }}>{doc.status}</span></div>
                  </div>
                  <div>
                    <button className="btn btn-secondary" style={{ padding: '4px' }} onClick={() => setActiveKebabDoc(activeKebabDoc === idx ? null : idx)}>
                      <MoreVertical size={14} />
                    </button>

                    {activeKebabDoc === idx && (
                      <div style={{ position: 'absolute', right: '12px', top: '40px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', zIndex: 10, display: 'flex', flexDirection: 'column', padding: '4px', gap: '2px', boxShadow: 'var(--shadow)' }}>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px', gap: '6px', border: 'none', display: 'flex', alignItems: 'center' }} onClick={() => { setViewingFileDetail({ name: doc.name, type: doc.type, size: doc.size, details: doc.details || "Raw text content extracted via local OCR engine and stored in local vector embeddings database." }); setActiveKebabDoc(null); }}>
                          <Eye size={12} style={{ color: '#3b82f6' }} />
                          <span>View Doc</span>
                        </button>
                        <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px', gap: '6px', border: 'none', display: 'flex', alignItems: 'center' }} onClick={() => { alert(`Editing index tags for ${doc.name}`); setActiveKebabDoc(null); }}>
                          <Pencil size={12} style={{ color: '#f59e0b' }} />
                          <span>Edit Index</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ padding: '30px 20px', textAlign: 'center', border: '1px dashed #1e293b', borderRadius: '8px', backgroundColor: '#0d131f' }}>
          <FileText size={32} style={{ color: '#94a3b8', marginBottom: '12px' }} />
          <h3 style={{ color: '#f8fafc', margin: '0 0 6px 0', fontSize: '15px' }}>Knowledge Store Active</h3>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0' }}>
            All documents uploaded through the **Data Sources** view are structured automatically. Ask the AI assistant to search or query these documents.
          </p>
        </div>
      </div>
    );
  };

  // Render settings content
  const renderSettingsContent = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>System Settings & Administration</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Configure licensing, local workspaces, local LLM properties, and access logs.</p>
        </div>

        <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #1e293b', paddingBottom: '10px' }}>
          <button 
            className={`btn ${settingsSubTab === 'licensing' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('licensing')}
          >
            Offline Licensing
          </button>
          <button 
            className={`btn ${settingsSubTab === 'users' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('users')}
          >
            User Profiles
          </button>
          <button 
            className={`btn ${settingsSubTab === 'llm' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('llm')}
          >
            LLM Integration
          </button>
          <button 
            className={`btn ${settingsSubTab === 'audit' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('audit')}
          >
            System Audit logs
          </button>
        </div>

        {settingsSubTab === 'licensing' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card">
              <div className="card-title">Active Licensing Properties</div>
              <div style={{ fontSize: '13px', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>Product Edition: <strong style={{ color: '#3b82f6' }}>CLARIUS Offline Basic</strong></div>
                <div>Licensed User Profiles: <strong>5 Max</strong></div>
                <div>Licensed Branches: <strong>1 Branch Node</strong></div>
                <div>Operational Mode: <strong>Standalone Local Node</strong></div>
              </div>
            </div>

            {isOwnerOrAdmin && (
              <div className="card">
                <div className="card-title">Upload Offline license File</div>
                <form onSubmit={handleLicenseImport} style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '500px' }}>
                  <textarea 
                    className="input-field" 
                    rows={4}
                    value={licenseText}
                    onChange={(e) => setLicenseText(e.target.value)}
                    placeholder="Paste CLARIUS-.lic base64 license payload block here..."
                    required
                  />
                  <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                    Verify License Signature
                  </button>
                </form>
                {licStatus && (
                  <div style={{ marginTop: '12px', fontSize: '13px', color: '#3b82f6' }}>
                    {licStatus}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {settingsSubTab === 'users' && (
          <div className="card">
            <div className="card-title">Create Workspace Profile</div>
            {isOwnerOrAdmin ? (
              <form onSubmit={handleUserCreate} style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '380px' }}>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Username</label>
                  <input 
                    type="text" 
                    className="input-field"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="e.g. analyst_john"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Password</label>
                  <input 
                    type="password" 
                    className="input-field"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Workspace Role</label>
                  <select 
                    className="input-field"
                    value={newUserRole}
                    onChange={(e) => setNewUserRole(e.target.value)}
                  >
                    <option value="admin">Admin</option>
                    <option value="manager">Manager</option>
                    <option value="analyst">Analyst</option>
                    <option value="staff">Staff</option>
                  </select>
                </div>
                <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start', marginTop: '6px' }}>
                  Register Profile
                </button>
              </form>
            ) : (
              <p style={{ color: '#ef4444', fontSize: '13px' }}>Only System Owners and Admins possess permissions to manage workspace profiles.</p>
            )}
            {userStatus && (
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#3b82f6' }}>
                {userStatus}
              </div>
            )}
          </div>
        )}

        {settingsSubTab === 'llm' && (
          <div className="card">
            <div className="card-title">Local LLM Orchestration Integration</div>
            <form onSubmit={handleLlmSave} style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '400px' }}>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Ollama Host Address</label>
                <input 
                  type="text" 
                  className="input-field"
                  value={ollamaHost}
                  onChange={(e) => setOllamaHost(e.target.value)}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Active LLM model</label>
                <input 
                  type="text" 
                  className="input-field"
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start', marginTop: '6px' }}>
                Apply Parameters
              </button>
            </form>
            {llmStatus && (
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#3b82f6' }}>
                {llmStatus}
              </div>
            )}
          </div>
        )}

        {settingsSubTab === 'audit' && (
          <div className="card">
            <div className="card-title">Access Audit history</div>
            {auditLoading ? (
              <div style={{ color: '#3b82f6', fontSize: '13px' }}>Loading historical events...</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>Timestamp</th>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>User ID</th>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>Event</th>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>Resource</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ padding: '12px 8px', textAlign: 'center', color: '#94a3b8' }}>No access operations logged.</td>
                      </tr>
                    ) : (
                      auditLogs.map((log: any, idx: number) => (
                        <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                          <td style={{ padding: '8px', color: '#94a3b8' }}>{new Date(log.timestamp).toLocaleString()}</td>
                          <td style={{ padding: '8px', color: '#94a3b8' }}>{log.user_id || "System"}</td>
                          <td style={{ padding: '8px', color: '#3b82f6' }}>{log.action}</td>
                          <td style={{ padding: '8px', color: '#94a3b8' }}>{log.target_resource || "None"}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Render Insights
  const renderInsights = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Business Insights & Anomalies</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>AI-generated performance alerts, stock level warnings, and transaction pattern changes.</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="card" style={{ borderLeft: '4px solid #ef4444' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong style={{ color: '#f8fafc', fontSize: '14px' }}>Inventory Shortage Risk</strong>
              <span className="badge badge-failed">Critical Priority</span>
            </div>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '13px' }}>
              8 high-velocity inventory items have fallen below safety reorder points. Estimated stockout in 4 days if reorder purchase is not dispatched.
            </p>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #f59e0b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong style={{ color: '#f8fafc', fontSize: '14px' }}>Vendor Cost Escalation</strong>
              <span className="badge badge-pending">Medium Priority</span>
            </div>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '13px' }}>
              Supplier cost rate for item category "Raw Sheets" increased by 14.8% over the past 30 days compared to historical company averages.
            </p>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #10b981' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <strong style={{ color: '#f8fafc', fontSize: '14px' }}>Sales Recovery Trend</strong>
              <span className="badge badge-success">Opportunity</span>
            </div>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '13px' }}>
              Customer segment "Northern Wholesale Distributors" showed a 22% increase in sales order frequency over the last 14 days.
            </p>
          </div>
        </div>
      </div>
    );
  };

  // Render Analytics
  const renderAnalytics = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Multidimensional Analytics Console</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Deep dive into sales channels, inventory turnover rates, and operating margins.</p>
        </div>

        <div className="grid-3">
          {['Sales Performance', 'Inventory Velocity', 'Purchase Costing', 'Financial Ratios', 'Branch Outlets', 'Custom Dimensions'].map((mod) => (
            <div key={mod} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '10px', minHeight: '120px' }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>{mod}</div>
              <p style={{ margin: 0, color: '#94a3b8', fontSize: '12px' }}>Analyze transactional variables, trends, and seasonal changes dynamically.</p>
              <button className="btn btn-secondary" style={{ marginTop: 'auto', alignSelf: 'flex-start', fontSize: '11px', padding: '4px 10px' }} onClick={() => setActiveMenu('assistant')}>
                Query via AI
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render Reports
  const renderReports = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Saved & Generated Reports</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Export or review compiled business intelligence reports. Default download format: Microsoft Excel.</p>
        </div>

        <div className="card">
          <div className="card-title">Available Ledger Summaries</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Report Title</th>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Frequency</th>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Generated On</th>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Format</th>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>Monthly Transactional Ledger</td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>Monthly</td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>Today, 08:00 AM</td>
                  <td style={{ padding: '10px 8px', color: '#3b82f6' }}>XLSX / Excel</td>
                  <td style={{ padding: '10px 8px' }}>
                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }}>Download</button>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>Safety Stock Exception Log</td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>Weekly</td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>2 days ago</td>
                  <td style={{ padding: '10px 8px', color: '#3b82f6' }}>XLSX / Excel</td>
                  <td style={{ padding: '10px 8px' }}>
                    <button className="btn btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }}>Download</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // Render Business Data DB explorer
  const renderBusinessData = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Business Data Explorer</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Direct catalog visibility into SQLite / DuckDB relation schemas populated locally.</p>
        </div>

        <div className="card">
          <div className="card-title">Registered Tables Catalog</div>
          {dashboards.length === 0 ? (
            <div style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px', color: '#94a3b8', textAlign: 'center' }}>
              No relation schemas synced or configured yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {dashboards.map((dash: any, idx: number) => {
                const name = typeof dash === 'object' && dash !== null ? dash.name : String(dash);
                return (
                  <div key={idx} style={{ padding: '12px 14px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong style={{ color: '#f8fafc', fontSize: '13px' }}>{name}</strong>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Type: DuckDB Tabular Entity</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => handlePreviewTable(name)}>
                        Preview
                      </button>
                      <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => handleViewTableDetails(name)}>
                        View
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Render Preview Data Block inline if table selected */}
        {activePreviewTable && (
          <div className="card" style={{ borderLeft: '3px solid #3b82f6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div className="card-title" style={{ margin: 0, textTransform: 'capitalize', fontSize: '14px' }}>
                Preview Data: {activePreviewTable.replace(/_/g, ' ')} (Top 5 Records)
              </div>
              <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => setActivePreviewTable(null)}>
                Close Preview
              </button>
            </div>
            {previewLoading ? (
              <div style={{ color: '#3b82f6', fontSize: '13px' }}>Loading rows...</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e293b' }}>
                      {previewCols.map((col) => (
                        <th key={col} style={{ padding: '8px 6px', color: '#f8fafc', fontWeight: 600 }}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.length === 0 ? (
                      <tr>
                        <td colSpan={previewCols.length || 1} style={{ padding: '12px 6px', textAlign: 'center', color: '#94a3b8' }}>
                          No records stored in this table.
                        </td>
                      </tr>
                    ) : (
                      previewData.map((row, rIdx) => (
                        <tr key={rIdx} style={{ borderBottom: '1px solid #1e293b' }}>
                          {previewCols.map((col) => (
                            <td key={col} style={{ padding: '8px 6px', color: '#94a3b8' }}>{String(row[col] ?? '')}</td>
                          ))}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Render Users & Roles
  const renderUsersRoles = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Users & Permissions Management</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Assign workspace operational authorization roles to team profiles.</p>
        </div>

        <div className="card">
          <div className="card-title">Active Members Registry</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Username</th>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Role Profile</th>
                  <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Scope Permissions</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>admin</td>
                  <td style={{ padding: '10px 8px', color: '#3b82f6' }}>admin / Owner</td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>Full System Access & License Keys</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>analyst_user</td>
                  <td style={{ padding: '10px 8px', color: '#10b981' }}>Analyst</td>
                  <td style={{ padding: '10px 8px', color: '#94a3b8' }}>Read-only Schema Query & Reports Export</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Permission Matrix Table */}
        <div className="card">
          <div className="card-title">Operational Access Matrix</div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 16px 0' }}>Role-based feature access authorization definitions mapped across functional components.</p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b', color: '#f8fafc' }}>
                  <th style={{ padding: '10px 8px' }}>Role</th>
                  <th style={{ padding: '10px 8px', textAlign: 'center' }}>Read Data</th>
                  <th style={{ padding: '10px 8px', textAlign: 'center' }}>Sync ERP</th>
                  <th style={{ padding: '10px 8px', textAlign: 'center' }}>File Ingest</th>
                  <th style={{ padding: '10px 8px', textAlign: 'center' }}>OCR Docs</th>
                  <th style={{ padding: '10px 8px', textAlign: 'center' }}>Edit Config</th>
                  <th style={{ padding: '10px 8px', textAlign: 'center' }}>RBAC Setup</th>
                </tr>
              </thead>
              <tbody>
                {matrixPermissions.map((row, idx) => {
                  const isEditable = getRolePriority(role) > getRolePriority(row.role);
                  return (
                    <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '10px 8px', fontWeight: 600, color: '#f8fafc' }}>{row.role}</td>
                      {row.permissions.map((perm, pIdx) => (
                        <td key={pIdx} style={{ padding: '10px 8px', textAlign: 'center' }}>
                          <span 
                            className={`badge ${perm ? 'badge-success' : 'badge-failed'}`}
                            style={{ 
                              cursor: isEditable ? 'pointer' : 'not-allowed', 
                              opacity: isEditable ? 1 : 0.6 
                            }}
                            title={isEditable ? "Click to toggle permission value" : `Locked: You cannot modify permissions for equal or higher priority role "${row.role}"`}
                            onClick={() => handleTogglePermission(idx, pIdx, row.role)}
                          >
                            {perm ? 'Yes' : 'No'}
                          </span>
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Hierarchy Graph Mapping Card */}
        <div className="card">
          <div className="card-title">Corporate Scope Hierarchy Tree</div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 20px 0' }}>Visual permission data propagation flow mapping from organization node down to team profiles.</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px', justifyContent: 'space-between', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', padding: '20px', borderRadius: '8px', flexWrap: 'wrap' }}>
            <div style={{ padding: '10px 14px', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid #3b82f6', borderRadius: '6px', textAlign: 'center', minWidth: '130px' }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>Organization</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Corporate context</div>
            </div>
            <ArrowRight size={16} style={{ color: '#94a3b8' }} />
            <div style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', textAlign: 'center', minWidth: '130px' }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>Branches</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Local office servers</div>
            </div>
            <ArrowRight size={16} style={{ color: '#94a3b8' }} />
            <div style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', textAlign: 'center', minWidth: '130px' }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>Departments</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Operational partitions</div>
            </div>
            <ArrowRight size={16} style={{ color: '#94a3b8' }} />
            <div style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', textAlign: 'center', minWidth: '130px' }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>Teams / Groups</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Access permissions</div>
            </div>
            <ArrowRight size={16} style={{ color: '#94a3b8' }} />
            <div style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', textAlign: 'center', minWidth: '130px' }}>
              <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>User Member</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Individual limits</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render Organization
  const renderOrganization = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Organization Hierarchy Settings</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Configure company branches, operational teams, and structural hierarchy parameters.</p>
        </div>

        <div className="card">
          <div className="card-title">ABC Manufacturing Corporate Node</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: '#94a3b8' }}>
            <div>Headquarters: <strong>Mumbai Industrial Zone</strong></div>
            <div>Associated Branch Nodes: <strong>3 Active Nodes</strong></div>
            <div>Connected Departments: <strong>Purchases, Sales, Logistics, Inventory</strong></div>
          </div>
        </div>
      </div>
    );
  };

  // Render Branches
  const renderBranches = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Branch Node Distribution</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Monitor standalone office server nodes connected in local area network (LAN).</p>
        </div>

        <div className="card">
          <div className="card-title">Registered Branch Nodes</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ padding: '12px 14px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ color: '#f8fafc', fontSize: '13px' }}>Mumbai Headquarters</strong>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>IP: 192.168.1.50</div>
              </div>
              <span className="badge badge-success">Online (LAN Master)</span>
            </div>
            <div style={{ padding: '12px 14px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ color: '#f8fafc', fontSize: '13px' }}>Pune Warehouse Outlet</strong>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>IP: 192.168.1.88</div>
              </div>
              <span className="badge badge-success">Online (LAN Node)</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Integration configurations state
  const [activeConfigPlugin, setActiveConfigPlugin] = useState<string | null>(null);
  const [pluginConfigs, setPluginConfigs] = useState<Record<string, Record<string, string>>>({
    Tally: { serverUrl: 'http://localhost:9000', syncPeriod: '12 Hours', port: '9000' },
    Chroma: { host: 'localhost', dbPath: './data/chroma', model: 'sentence-transformers' },
    OCR: { cores: '4', maxQueue: '50', allowedTypes: 'PDF, PNG, JPG' }
  });

  // Render Integrations
  const renderIntegrations = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>System Integrations & API Plugins</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Manage server ports, local workspace folders, and worker allocations for each adapter plugin.</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          
          {/* TallyPrime Card */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div>
                <strong style={{ color: '#f8fafc', fontSize: '14px' }}>TallyPrime Accounting Adapter</strong>
                <div style={{ fontSize: '11px', color: '#10b981' }}>Active Plugin Node</div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ fontSize: '11px', padding: '4px 10px' }}
                onClick={() => setActiveConfigPlugin(activeConfigPlugin === 'Tally' ? null : 'Tally')}
              >
                Configure
              </button>
            </div>
            <p style={{ margin: '0 0 10px 0', color: '#94a3b8', fontSize: '13px' }}>
              Maps local Tally accounting ledgers and voucher XML payloads to the DuckDB relational schema database.
            </p>
            {activeConfigPlugin === 'Tally' && (
              <div style={{ padding: '12px', borderTop: '1px solid #1e293b', marginTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Server URL Endpoint</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={pluginConfigs.Tally.serverUrl}
                    onChange={(e) => setPluginConfigs({ ...pluginConfigs, Tally: { ...pluginConfigs.Tally, serverUrl: e.target.value } })}
                    placeholder="http://localhost:9000"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Sync Frequency Period</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={pluginConfigs.Tally.syncPeriod}
                    onChange={(e) => setPluginConfigs({ ...pluginConfigs, Tally: { ...pluginConfigs.Tally, syncPeriod: e.target.value } })}
                    placeholder="e.g. 12 Hours"
                  />
                </div>
              </div>
            )}
          </div>

          {/* ChromaDB Card */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div>
                <strong style={{ color: '#f8fafc', fontSize: '14px' }}>ChromaDB Vector Embedding Engine</strong>
                <div style={{ fontSize: '11px', color: '#10b981' }}>Active Plugin Node</div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ fontSize: '11px', padding: '4px 10px' }}
                onClick={() => setActiveConfigPlugin(activeConfigPlugin === 'Chroma' ? null : 'Chroma')}
              >
                Configure
              </button>
            </div>
            <p style={{ margin: '0 0 10px 0', color: '#94a3b8', fontSize: '13px' }}>
              Stores vector embeddings generated from uploaded policy docs, invoices, manuals, and custom knowledge.
            </p>
            {activeConfigPlugin === 'Chroma' && (
              <div style={{ padding: '12px', borderTop: '1px solid #1e293b', marginTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Local Vector DB Path</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={pluginConfigs.Chroma.dbPath}
                    onChange={(e) => setPluginConfigs({ ...pluginConfigs, Chroma: { ...pluginConfigs.Chroma, dbPath: e.target.value } })}
                    placeholder="./data/chromadb"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Active Model Target</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={pluginConfigs.Chroma.model}
                    onChange={(e) => setPluginConfigs({ ...pluginConfigs, Chroma: { ...pluginConfigs.Chroma, model: e.target.value } })}
                    placeholder="sentence-transformers"
                  />
                </div>
              </div>
            )}
          </div>

          {/* OCR Processor Card */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div>
                <strong style={{ color: '#f8fafc', fontSize: '14px' }}>Local OCR Extraction Processor</strong>
                <div style={{ fontSize: '11px', color: '#10b981' }}>Active Plugin Node</div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ fontSize: '11px', padding: '4px 10px' }}
                onClick={() => setActiveConfigPlugin(activeConfigPlugin === 'OCR' ? null : 'OCR')}
              >
                Configure
              </button>
            </div>
            <p style={{ margin: '0 0 10px 0', color: '#94a3b8', fontSize: '13px' }}>
              Extracts text layers from scanned invoices, Challans, and PDF bills using local Tesseract bindings.
            </p>
            {activeConfigPlugin === 'OCR' && (
              <div style={{ padding: '12px', borderTop: '1px solid #1e293b', marginTop: '10px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>CPU Allocation Cores</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={pluginConfigs.OCR.cores}
                    onChange={(e) => setPluginConfigs({ ...pluginConfigs, OCR: { ...pluginConfigs.OCR, cores: e.target.value } })}
                    placeholder="4 Cores"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Allowed File Types</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    value={pluginConfigs.OCR.allowedTypes}
                    onChange={(e) => setPluginConfigs({ ...pluginConfigs, OCR: { ...pluginConfigs.OCR, allowedTypes: e.target.value } })}
                    placeholder="PDF, PNG, JPG"
                  />
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    );
  };

  // Render Sync logs
  const renderSyncLogs = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>Synchronization logs & Ingestion History</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Audit log records tracking pipeline updates from TallyPrime and local spreadsheets.</p>
        </div>

        <div className="card">
          <div className="card-title">Sync Logs History</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', fontFamily: 'var(--mono)', color: '#94a3b8' }}>
            <div>[{syncTime}] INFO: Synced TallyPrime ledger accounts successfully. (2,432 records ingested)</div>
            <div>[Today, 09:00 AM] INFO: Ingested file mapping 'Sales Transactions' into DuckDB. (1,280 rows)</div>
            <div>[Yesterday, 04:30 PM] INFO: Document OCR complete. Embedded 4 policy documents into ChromaDB.</div>
          </div>
        </div>
      </div>
    );
  };

  // Render License status
  const renderLicense = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ color: '#f8fafc', margin: 0, fontSize: '18px' }}>CLARIUS Offline License</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Manage features, nodes limit, and activation terms on this local instance.</p>
        </div>

        <div className="card">
          <div className="card-title">Active Licensing Profile</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#94a3b8' }}>
            <div>Edition: <strong style={{ color: '#3b82f6' }}>CLARIUS Copilot (Offline Enterprise Edition)</strong></div>
            <div>Organization: <strong>ABC Manufacturing Ltd</strong></div>
            <div>Licensed Users: <strong>12 / 25 Max Profiles</strong></div>
            <div>Branch Node Limit: <strong>3 / 5 Active Nodes</strong></div>
            <div>License Status: <span className="badge badge-success">Active & Verified</span></div>
            <div>Valid Until: <strong>31 December 2027</strong></div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div 
        className="sidebar" 
        style={{ 
          backgroundColor: '#0d131f', 
          width: isCollapsed ? '70px' : '240px', 
          padding: isCollapsed ? '16px 8px' : '16px', 
          transition: 'width 0.2s, padding 0.2s',
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          position: 'sticky',
          top: 0,
          overflowY: 'auto'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: isCollapsed ? 'center' : 'space-between', marginBottom: '24px', padding: '0 8px' }}>
          {!isCollapsed && (
            <div className="sidebar-brand" style={{ margin: 0, padding: 0 }}>
              <Layers size={18} style={{ color: '#3b82f6' }} />
              <span>CLARIUS</span>
            </div>
          )}
          {isCollapsed && <Layers size={18} style={{ color: '#3b82f6' }} />}
          
          <button 
            className="btn btn-secondary" 
            style={{ padding: '4px', border: 'none', backgroundColor: 'transparent' }} 
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? <ChevronRight size={14} style={{ color: '#94a3b8' }} /> : <ChevronLeft size={14} style={{ color: '#94a3b8' }} />}
          </button>
        </div>

        {/* Workspace Group */}
        {!isCollapsed && (
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600, padding: '0 8px 8px 8px', letterSpacing: '0.5px' }}>
            Workspace
          </div>
        )}
        {isCollapsed && <div style={{ borderBottom: '1px solid #1e293b', marginBottom: '8px' }} />}
        <ul className="sidebar-menu" style={{ marginBottom: '14px' }}>
          <li className={`sidebar-item ${activeMenu === 'assistant' ? 'active' : ''}`} onClick={() => setActiveMenu('assistant')} title="AI Assistant">
            <MessageSquare size={14} />
            {!isCollapsed && <span>AI Assistant</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'dashboards' ? 'active' : ''}`} onClick={() => setActiveMenu('dashboards')} title="Dashboard">
            <LayoutDashboard size={14} />
            {!isCollapsed && <span>Dashboard</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'insights' ? 'active' : ''}`} onClick={() => setActiveMenu('insights')} title="Insights">
            <TrendingUp size={14} />
            {!isCollapsed && <span>Insights</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'analytics' ? 'active' : ''}`} onClick={() => setActiveMenu('analytics')} title="Analytics">
            <Compass size={14} />
            {!isCollapsed && <span>Analytics</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'reports' ? 'active' : ''}`} onClick={() => setActiveMenu('reports')} title="Reports">
            <FileSpreadsheet size={14} />
            {!isCollapsed && <span>Reports</span>}
          </li>
        </ul>

        {/* Data Group */}
        {!isCollapsed && (
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600, padding: '0 8px 8px 8px', letterSpacing: '0.5px' }}>
            Data
          </div>
        )}
        {isCollapsed && <div style={{ borderBottom: '1px solid #1e293b', marginBottom: '8px' }} />}
        <ul className="sidebar-menu" style={{ marginBottom: '14px' }}>
          <li className={`sidebar-item ${activeMenu === 'sources' ? 'active' : ''}`} onClick={() => setActiveMenu('sources')} title="Data Sources">
            <Database size={14} />
            {!isCollapsed && <span>Data Sources</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'businessdata' ? 'active' : ''}`} onClick={() => setActiveMenu('businessdata')} title="Business Data">
            <Layers size={14} />
            {!isCollapsed && <span>Business Data</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'documents' ? 'active' : ''}`} onClick={() => setActiveMenu('documents')} title="Business Knowledge">
            <BookOpen size={14} />
            {!isCollapsed && <span>Business Knowledge</span>}
          </li>
        </ul>

        {/* Administration Group */}
        {!isCollapsed && (
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600, padding: '0 8px 8px 8px', letterSpacing: '0.5px' }}>
            Administration
          </div>
        )}
        {isCollapsed && <div style={{ borderBottom: '1px solid #1e293b', marginBottom: '8px' }} />}
        <ul className="sidebar-menu" style={{ marginBottom: '14px' }}>
          <li className={`sidebar-item ${activeMenu === 'usersroles' ? 'active' : ''}`} onClick={() => setActiveMenu('usersroles')} title="Users & Roles">
            <Users size={14} />
            {!isCollapsed && <span>Users & Roles</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'organization' ? 'active' : ''}`} onClick={() => setActiveMenu('organization')} title="Organization">
            <Building2 size={14} />
            {!isCollapsed && <span>Organization</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'branches' ? 'active' : ''}`} onClick={() => setActiveMenu('branches')} title="Branches">
            <GitFork size={14} />
            {!isCollapsed && <span>Branches</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'settings' ? 'active' : ''}`} onClick={() => setActiveMenu('settings')} title="Settings">
            <Settings size={14} />
            {!isCollapsed && <span>Settings</span>}
          </li>
        </ul>

        {/* System Group */}
        {!isCollapsed && (
          <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600, padding: '0 8px 8px 8px', letterSpacing: '0.5px' }}>
            System
          </div>
        )}
        {isCollapsed && <div style={{ borderBottom: '1px solid #1e293b', marginBottom: '8px' }} />}
        <ul className="sidebar-menu" style={{ marginBottom: '14px' }}>
          <li className={`sidebar-item ${activeMenu === 'integrations' ? 'active' : ''}`} onClick={() => setActiveMenu('integrations')} title="Integrations">
            <Cpu size={14} />
            {!isCollapsed && <span>Integrations</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'synclogs' ? 'active' : ''}`} onClick={() => setActiveMenu('synclogs')} title="Sync & Activity">
            <History size={14} />
            {!isCollapsed && <span>Sync & Activity</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'license' ? 'active' : ''}`} onClick={() => setActiveMenu('license')} title="License">
            <Award size={14} />
            {!isCollapsed && <span>License</span>}
          </li>
        </ul>

        {/* Sidebar user footer */}
        <div className="sidebar-footer" style={{ marginTop: 'auto', borderTop: '1px solid #1e293b', paddingTop: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: isCollapsed ? '0' : '10px', marginBottom: '12px', justifyContent: isCollapsed ? 'center' : 'flex-start' }}>
            <div style={{ padding: '6px', backgroundColor: 'rgba(59, 130, 246, 0.1)', borderRadius: '4px' }}>
              <User size={14} style={{ color: '#3b82f6' }} />
            </div>
            {!isCollapsed && (
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc' }}>{username}</div>
                <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'capitalize' }}>{role}</div>
              </div>
            )}
          </div>
          <button className="btn btn-secondary" style={{ width: '100%', gap: '8px', padding: '6px 12px', display: 'flex', justifyContent: isCollapsed ? 'center' : 'flex-start' }} onClick={onLogout}>
            <LogOut size={12} />
            {!isCollapsed && <span>Sign Out</span>}
          </button>
        </div>
      </div>

      {/* Main viewport */}
      <div className="workspace">
        <div className="header">
          <div style={{ fontSize: '13px', fontWeight: 500, color: '#f8fafc' }}>
            Workspace / <span style={{ color: '#3b82f6', textTransform: 'capitalize' }}>{activeMenu === 'assistant' ? 'AI Assistant' : activeMenu}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-success">Standalone Local Node</span>
          </div>
        </div>

        <div className="content-viewport">
          {activeMenu === 'assistant' && renderChatAssistant()}
          {activeMenu === 'dashboards' && renderDashboard()}
          {activeMenu === 'insights' && renderInsights()}
          {activeMenu === 'analytics' && renderAnalytics()}
          {activeMenu === 'reports' && renderReports()}
          {activeMenu === 'sources' && renderDataSources()}
          {activeMenu === 'businessdata' && renderBusinessData()}
          {activeMenu === 'documents' && renderDocuments()}
          {activeMenu === 'usersroles' && renderUsersRoles()}
          {activeMenu === 'organization' && renderOrganization()}
          {activeMenu === 'branches' && renderBranches()}
          {activeMenu === 'settings' && renderSettingsContent()}
          {activeMenu === 'integrations' && renderIntegrations()}
          {activeMenu === 'synclogs' && renderSyncLogs()}
          {activeMenu === 'license' && renderLicense()}
        </div>
      </div>

      {/* ERP Connection Setup Modal */}
      {configuringErp && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '400px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div className="card-title" style={{ fontSize: '14px' }}>Connect to {configuringErp}</div>
            
            <form onSubmit={handleSaveErpConnection} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Server URL Endpoint</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder={configuringErp === 'TallyPrime' ? 'http://localhost:9000' : 'https://api.erp.local'}
                  value={erpServerUrl}
                  onChange={(e) => setErpServerUrl(e.target.value)}
                  required
                />
              </div>

              {configuringErp === 'TallyPrime' && (
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Company Name</label>
                  <input 
                    type="text" 
                    className="input-field" 
                    placeholder="e.g. ABC Trading Co"
                    value={erpCompanyName}
                    onChange={(e) => setErpCompanyName(e.target.value)}
                    required
                  />
                </div>
              )}

              {(configuringErp === 'Odoo ERP' || configuringErp === 'BUSY') && (
                <>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Database Name / Company Code</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={erpCompanyName}
                      onChange={(e) => setErpCompanyName(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>User ID / Username</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={erpUsername}
                      onChange={(e) => setErpUsername(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Access Password</label>
                    <input 
                      type="password" 
                      className="input-field" 
                      value={erpPassword}
                      onChange={(e) => setErpPassword(e.target.value)}
                      required
                    />
                  </div>
                </>
              )}

              {configuringErp === 'ERPNext' && (
                <>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>API Key</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={erpApiKey}
                      onChange={(e) => setErpApiKey(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>API Secret</label>
                    <input 
                      type="password" 
                      className="input-field" 
                      value={erpPassword}
                      onChange={(e) => setErpPassword(e.target.value)}
                      required
                    />
                  </div>
                </>
              )}

              {configuringErp === 'Marg ERP' && (
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Marg Client API Key</label>
                  <input 
                    type="password" 
                    className="input-field" 
                    value={erpApiKey}
                    onChange={(e) => setErpApiKey(e.target.value)}
                    required
                  />
                </div>
              )}

              {configuringErp === 'Zoho Books' && (
                <>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Client ID</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={erpApiKey}
                      onChange={(e) => setErpApiKey(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Client Secret</label>
                    <input 
                      type="password" 
                      className="input-field" 
                      value={erpPassword}
                      onChange={(e) => setErpPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Organization ID</label>
                    <input 
                      type="text" 
                      className="input-field" 
                      value={erpOrgId}
                      onChange={(e) => setErpOrgId(e.target.value)}
                      required
                    />
                  </div>
                </>
              )}

              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setConfiguringErp(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save & Sync Connection</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* File/Doc Detail Viewer Modal Dialog */}
      {viewingFileDetail && (
        <div className="modal-backdrop">
          <div 
            className="card" 
            style={{ 
              width: viewingFileDetail.columns ? '800px' : '550px', 
              maxWidth: '95%', 
              zIndex: 110, 
              position: 'relative', 
              borderLeft: '4px solid #3b82f6',
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexShrink: 0 }}>
              <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '15px' }}>File Details: {viewingFileDetail.name}</h3>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '2px 8px', fontSize: '11px' }} 
                onClick={() => setViewingFileDetail(null)}
              >
                Close
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', overflowY: 'auto', flexGrow: 1 }}>
              <div style={{ flexShrink: 0 }}><strong style={{ color: '#f8fafc' }}>File Format / Type:</strong> <span style={{ color: '#94a3b8' }}>{viewingFileDetail.type}</span></div>
              <div style={{ flexShrink: 0 }}><strong style={{ color: '#f8fafc' }}>File Size Capacity:</strong> <span style={{ color: '#94a3b8' }}>{viewingFileDetail.size}</span></div>
              
              <div style={{ borderTop: '1px solid #1e293b', paddingTop: '10px', marginTop: '5px', display: 'flex', flexDirection: 'column', flexGrow: 1, minHeight: 0 }}>
                {viewingFileDetail.columns && viewingFileDetail.data ? (
                  <>
                    <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '6px', flexShrink: 0 }}>Table Rows & Columns Grid:</strong>
                    <div style={{ overflowX: 'auto', overflowY: 'auto', flexGrow: 1, border: '1px solid #1e293b', borderRadius: '6px' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                        <thead style={{ position: 'sticky', top: 0, backgroundColor: '#0f172a', zIndex: 1 }}>
                          <tr style={{ borderBottom: '1px solid #1e293b' }}>
                            {viewingFileDetail.columns.map((col) => (
                              <th key={col} style={{ padding: '8px 6px', color: '#f8fafc', fontWeight: 600 }}>{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {viewingFileDetail.data.length === 0 ? (
                            <tr>
                              <td colSpan={viewingFileDetail.columns.length} style={{ padding: '16px', textAlign: 'center', color: '#94a3b8' }}>
                                No records stored in this table.
                              </td>
                            </tr>
                          ) : (
                            viewingFileDetail.data.map((row, rIdx) => (
                              <tr key={rIdx} style={{ borderBottom: '1px solid #1e293b' }}>
                                {viewingFileDetail.columns?.map((col) => (
                                  <td key={col} style={{ padding: '8px 6px', color: '#94a3b8' }}>{String(row[col] ?? '')}</td>
                                ))}
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <>
                    <strong style={{ color: '#f8fafc', display: 'block', marginBottom: '6px' }}>Parsed Content Details:</strong>
                    <div style={{ padding: '12px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', overflowY: 'auto', whiteSpace: 'pre-wrap', fontFamily: 'var(--mono)', fontSize: '12px', flexGrow: 1 }}>
                      {viewingFileDetail.details}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
