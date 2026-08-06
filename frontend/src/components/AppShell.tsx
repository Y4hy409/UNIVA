import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, LayoutDashboard, Database, Settings, LogOut, 
  User, Activity, RefreshCw, Layers, UploadCloud, FileText, Send, ArrowRight,
  TrendingUp, Cpu, Compass, FileSpreadsheet, Users, Building2, GitFork, History, Award, BookOpen,
  ChevronLeft, ChevronRight, MoreVertical, Eye, Pencil
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { ColumnsMapper } from '../features/sources/ColumnsMapper';
import { RoleManagement } from '../features/identity/RoleManagement';
import { UserManagement } from '../features/identity/UserManagement';
import { BranchManagement } from '../features/identity/BranchManagement';
import { DepartmentManagement } from '../features/identity/DepartmentManagement';
import { getApiUrl, apiFetch } from '../config/api';

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
  const [activeMenu, setActiveMenu] = useState<'assistant' | 'dashboards' | 'sources' | 'documents' | 'settings' | 'insights' | 'analytics' | 'reports' | 'businessdata' | 'usersroles' | 'users' | 'roles' | 'organization' | 'departments' | 'branches' | 'integrations' | 'synclogs' | 'license' | 'auditlogs'>('assistant');
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
  const [tablesCatalog, setTablesCatalog] = useState<{name: string, type: string, size: string, status: string, details?: string}[]>([]);
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
  const [settingsSubTab, setSettingsSubTab] = useState<'system_config' | 'llm' | 'integrations' | 'users_access' | 'license' | 'audit' | 'health'>('system_config');
  const [systemConfig, setSystemConfig] = useState({
    general: { appName: 'CLARIUS / UNIVA', timezone: 'UTC' },
    ui: { theme: 'dark', sidebarCollapsed: false },
    workspace: { folderFlags: {} }
  });
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [systemConfigStatus, setSystemConfigStatus] = useState<string | null>(null);
  const [permissionsList, setPermissionsList] = useState<{id: string, name: string}[]>([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState('analyst');
  const [appRoles, setAppRoles] = useState<{id: string, name: string}[]>([]);
  const [userStatus, setUserStatus] = useState<string | null>(null);
  const [licenseText, setLicenseText] = useState('');
  const [licStatus, setLicStatus] = useState<string | null>(null);
  const [parentRole, setParentRole] = useState('admin');
  const [childRole, setChildRole] = useState('manager');
  const [scopeUser, setScopeUser] = useState('');
  const [scopeType, setScopeType] = useState('branch');
  const [scopeValue, setScopeValue] = useState('');
  const [hierarchyStatus, setHierarchyStatus] = useState<string | null>(null);
  const [scopeStatus, setScopeStatus] = useState<string | null>(null);
  
  // Local LLM config
  const [ollamaHost, setOllamaHost] = useState(localStorage.getItem('ollama_host') || 'http://localhost:11434');
  const [ollamaModel, setOllamaModel] = useState(localStorage.getItem('ollama_model') || 'qwen3:4b-instruct');
  const [llmStatus, setLlmStatus] = useState<string | null>(null);

  // Unified Chat / AI Assistant States
  const [queryText, setQueryText] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [activeStage, setActiveStage] = useState<string>('none');
  const [conversationId, setConversationId] = useState<string>(() => crypto.randomUUID());

  const handleNewChat = () => {
    const newId = crypto.randomUUID();
    setConversationId(newId);
    setChatHistory([]);
    setActiveStage('none');
  };

  // Document upload / OCR Ingest states
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('policy');
  const [docTitle, setDocTitle] = useState('');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Global License Required Prompt Modal states
  const [showLicenseModal, setShowLicenseModal] = useState(false);
  const [modalLicenseText, setModalLicenseText] = useState('');
  const [modalLicStatus, setModalLicStatus] = useState<string | null>(null);
  const [modalLicLoading, setModalLicLoading] = useState(false);

  // Dashboards states
  const [dashboards, setDashboards] = useState<any[]>([]);

  // Audit logs state
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Sync state
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success'>('idle');
  const [syncTime, setSyncTime] = useState<string>('Today, 10:32 AM');

  // Dynamic licensing, users, and insights states
  const [licenseProperties, setLicenseProperties] = useState({
    edition: 'Loading...',
    max_users: 0,
    max_branches: 0
  });
  const [registeredUsers, setRegisteredUsers] = useState<{username: string, role: string}[]>([]);
  const [businessInsights, setBusinessInsights] = useState<{title: string, priority: string, message: string, type: string}[]>([]);
  const [insightsLoading, setInsightsLoading] = useState(false);

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

  const fetchSystemConfig = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/settings', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSystemConfig(data);
      }
    } catch (err) {
      console.error("Failed to load settings", err);
    }
  };

  const handleSaveSystemConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSystemConfigStatus("Updating configuration parameters...");
    try {
      const res = await fetch('http://localhost:8000/admin/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(systemConfig)
      });
      if (res.ok) {
        setSystemConfigStatus("Configuration saved successfully.");
      } else {
        throw new Error("Failed to save settings");
      }
    } catch (err: any) {
      setSystemConfigStatus(`Error: ${err.message}`);
    }
  };

  const fetchSystemHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await fetch('http://localhost:8000/admin/system/health', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      console.error("Failed to fetch system health", err);
    } finally {
      setHealthLoading(false);
    }
  };

  const fetchRbacMatrix = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/rbac/matrix', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.matrix) setMatrixPermissions(data.matrix);
        if (data.permissions) setPermissionsList(data.permissions);
      }
    } catch (err) {
      console.error("Failed to fetch RBAC matrix", err);
    }
  };

  const handleAddHierarchy = async (e: React.FormEvent) => {
    e.preventDefault();
    setHierarchyStatus("Updating hierarchy...");
    try {
      const res = await fetch('http://localhost:8000/admin/rbac/hierarchy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ parent_role_id: parentRole, child_role_id: childRole })
      });
      if (res.ok) {
        setHierarchyStatus("Role hierarchy updated successfully!");
        fetchRbacMatrix();
      } else {
        const data = await res.json();
        throw new Error(data.detail || "Failed to update hierarchy");
      }
    } catch (err: any) {
      setHierarchyStatus(`Error: ${err.message}`);
    }
  };

  const handleAssignScope = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scopeUser || !scopeValue) return;
    setScopeStatus("Assigning scope...");
    try {
      const res = await fetch('http://localhost:8000/admin/rbac/user-scope', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ user_id: scopeUser, scope_type: scopeType, scope_value: scopeValue })
      });
      if (res.ok) {
        setScopeStatus("User scope assigned successfully!");
        setScopeValue('');
      } else {
        const data = await res.json();
        throw new Error(data.detail || "Failed to assign scope");
      }
    } catch (err: any) {
      setScopeStatus(`Error: ${err.message}`);
    }
  };

  const handleUserRoleChange = async (username: string, roleId: string) => {
    try {
      const res = await fetch('http://localhost:8000/admin/rbac/user-role', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ user_id: username, role_id: roleId })
      });
      if (res.ok) {
        fetchRegisteredUsers();
      } else {
        alert("Failed to update user role");
      }
    } catch (err) {
      console.error(err);
    }
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

  const fetchRegisteredUsers = async () => {
    try {
      const res = await fetch('http://localhost:8000/auth/users', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRegisteredUsers(data);
      }
    } catch (err) {
      console.error("Failed to fetch users", err);
    }
  };

  const fetchBusinessInsights = async () => {
    setInsightsLoading(true);
    try {
      const res = await fetch('http://localhost:8000/analytics/insights', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setBusinessInsights(data.insights || []);
      }
    } catch (err) {
      console.error("Failed to fetch insights", err);
    } finally {
      setInsightsLoading(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await fetch('http://localhost:8000/documents', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDocList(data.map((doc: any) => ({
          name: doc.title,
          type: doc.doc_type.toUpperCase(),
          size: "Embedded Vector Chunk",
          status: "Indexed",
          details: `Ingested document: ${doc.title}. Parsed type: ${doc.doc_type}.`
        })));
      }
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  const fetchTables = async () => {
    try {
      const res = await fetch('http://localhost:8000/data-sources/tables', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSourceFilesList(data);
        setTablesCatalog(data);
      }
    } catch (err) {
      console.error("Failed to load tables", err);
    }
  };

  useEffect(() => {
    const fetchLicenseProps = async () => {
      try {
        const res = await fetch('http://localhost:8000/licensing/properties', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (res.ok) {
          const data = await res.json();
          setLicenseProperties(data);
        }
      } catch (err) {
        console.error("Failed to fetch license properties", err);
      }
    };

    const fetchAppRoles = async () => {
      try {
        const res = await fetch('http://localhost:8000/auth/roles');
        if (res.ok) {
          const data = await res.json();
          setAppRoles(data);
        }
      } catch (err) {
        console.error("Failed to fetch roles", err);
      }
    };

    fetchLicenseProps();
    fetchRegisteredUsers();
    fetchDocuments();
    fetchTables();
    fetchAppRoles();
  }, []);

  useEffect(() => {
    if (activeMenu === 'insights') {
      fetchBusinessInsights();
    } else if (activeMenu === 'sources' || activeMenu === 'businessdata') {
      fetchTables();
    } else if (activeMenu === 'documents') {
      fetchDocuments();
    }
  }, [activeMenu]);

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
    fetchTables();
    fetchDocuments();
  }, [activeMenu]);

  // Load Audit logs
  const fetchAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const res = await fetch('http://localhost:8000/audit', {
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

  useEffect(() => {
    if (activeMenu === 'settings') {
      if (settingsSubTab === 'system_config') {
        fetchSystemConfig();
      } else if (settingsSubTab === 'users_access') {
        fetchRbacMatrix();
        fetchRegisteredUsers();
      } else if (settingsSubTab === 'health') {
        fetchSystemHealth();
      }
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
    const eventSource = new EventSource(getApiUrl(`/analytics/stream?q=${encodeURIComponent(currentQuery)}&conversation_id=${encodeURIComponent(conversationId)}`));
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
        const res = await apiFetch(`/documents/query?q=${encodeURIComponent(currentQuery)}`);
        
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
      const res = await apiFetch('/documents/upload', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        if (res.status === 402) {
          setShowLicenseModal(true);
          setUploadStatus("License key required to process document OCR.");
          return;
        }
        throw new Error("Upload failed");
      }
      
      setUploadStatus("Ingest success! Document OCR text extracted and indexed into knowledge base.");
      setDocFile(null);
      setDocTitle('');
      fetchDocuments();
    } catch (err) {
      setUploadStatus("Failed to extract text from document.");
    }
  };

  const handleModalLicenseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalLicenseText.trim()) return;

    setModalLicLoading(true);
    setModalLicStatus("Verifying & activating license key...");

    try {
      const res = await apiFetch('/upgrade/license', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: modalLicenseText.trim() })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "License verification failed.");
      }

      setModalLicStatus("License activated successfully! Capabilities unlocked.");
      setModalLicenseText('');
      setTimeout(() => {
        setShowLicenseModal(false);
        setModalLicStatus(null);
        const fetchLicenseProps = async () => {
          try {
            const r = await fetch('http://localhost:8000/licensing/properties', {
              headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
            });
            if (r.ok) setLicenseProperties(await r.json());
          } catch (err) {}
        };
        fetchLicenseProps();
      }, 1500);
    } catch (err: any) {
      setModalLicStatus(`Error: ${err.message || 'Invalid license key'}`);
    } finally {
      setModalLicLoading(false);
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
      fetchRegisteredUsers();
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button 
              className="btn btn-secondary" 
              style={{ fontSize: '12px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '6px' }}
              onClick={handleNewChat}
              title="Start New Chat Session"
            >
              <span>+ New Chat</span>
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }}></span>
              <span style={{ fontSize: '12px', color: '#10b981' }}>Inference Active</span>
            </div>
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
                {msg.type === 'rag_result' && msg.ragDocs && (() => {
                  const uniqueDocs: any[] = [];
                  const seenKeys = new Set<string>();
                  msg.ragDocs.forEach((doc) => {
                    const key = `${doc.title || ''}::${(doc.content || '').trim()}`;
                    if (!seenKeys.has(key)) {
                      seenKeys.add(key);
                      uniqueDocs.push(doc);
                    }
                  });

                  return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 600, color: '#f8fafc' }}>Knowledge Source Citations:</div>
                      {uniqueDocs.map((doc, dIdx) => (
                        <div key={dIdx} style={{ padding: '10px 14px', backgroundColor: '#0d131f', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontWeight: 600, color: '#3b82f6' }}>{doc.title || "Policy Document"}</span>
                            <span style={{ fontSize: '10px', color: '#94a3b8' }}>Match: {Number(doc.distance || 0).toFixed(4)}</span>
                          </div>
                          <div style={{ color: '#94a3b8', lineHeight: 1.4 }}>{doc.content}</div>
                        </div>
                      ))}
                    </div>
                  );
                })()}
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
          <ColumnsMapper 
            onIngestSuccess={() => { fetchTables(); }}
            onLicenseRequired={() => setShowLicenseModal(true)} 
          />
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
          <p style={{ color: '#94a3b8', fontSize: '13px' }}>Configure licensing, role-based access controls, local LLM properties, and system diagnostics.</p>
        </div>

        <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #1e293b', paddingBottom: '10px', flexWrap: 'wrap' }}>
          <button 
            className={`btn ${settingsSubTab === 'system_config' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('system_config')}
          >
            System Configuration
          </button>
          <button 
            className={`btn ${settingsSubTab === 'llm' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('llm')}
          >
            AI & LLM
          </button>
          <button 
            className={`btn ${settingsSubTab === 'integrations' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('integrations')}
          >
            Data & Integrations
          </button>
          <button 
            className={`btn ${settingsSubTab === 'users_access' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('users_access')}
          >
            Users & Access
          </button>
          <button 
            className={`btn ${settingsSubTab === 'license' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('license')}
          >
            License Management
          </button>
          <button 
            className={`btn ${settingsSubTab === 'audit' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('audit')}
          >
            Audit & Security
          </button>
          <button 
            className={`btn ${settingsSubTab === 'health' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSettingsSubTab('health')}
          >
            System Health
          </button>
        </div>

        {/* 1. System Configuration */}
        {settingsSubTab === 'system_config' && (
          <div className="card">
            <div className="card-title">General System settings</div>
            <form onSubmit={handleSaveSystemConfig} style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '500px' }}>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Application Display Name</label>
                <input 
                  type="text" 
                  className="input-field" 
                  value={systemConfig.general?.appName || ''} 
                  onChange={(e) => setSystemConfig(prev => ({...prev, general: {...prev.general, appName: e.target.value}}))}
                  required 
                />
              </div>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Deployment Mode</label>
                <input 
                  type="text" 
                  className="input-field" 
                  value="Standalone Offline Node" 
                  disabled 
                />
              </div>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>System Timezone</label>
                <input 
                  type="text" 
                  className="input-field" 
                  value={systemConfig.general?.timezone || ''} 
                  onChange={(e) => setSystemConfig(prev => ({...prev, general: {...prev.general, timezone: e.target.value}}))}
                  required 
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                Save System Config
              </button>
            </form>
            {systemConfigStatus && (
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#3b82f6' }}>
                {systemConfigStatus}
              </div>
            )}
          </div>
        )}

        {/* 2. AI & LLM */}
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

        {/* 3. Data & Integrations */}
        {settingsSubTab === 'integrations' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {renderDataSources()}
          </div>
        )}

        {/* 4. Users & Access */}
        {settingsSubTab === 'users_access' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
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
                      {appRoles.length === 0 ? (
                        <>
                          <option value="admin">Admin</option>
                          <option value="manager">Manager</option>
                          <option value="analyst">Analyst</option>
                          <option value="staff">Staff</option>
                        </>
                      ) : (
                        appRoles.map(r => (
                          <option key={r.id} value={r.id}>{r.name}</option>
                        ))
                      )}
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

            <div className="card">
              <div className="card-title">Active Members Registry</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Username</th>
                      <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Role Profile</th>
                      <th style={{ padding: '10px 8px', color: '#f8fafc' }}>Change Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    {registeredUsers.map((u) => (
                      <tr key={u.username} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>{u.username}</td>
                        <td style={{ padding: '10px 8px', color: '#3b82f6', textTransform: 'capitalize' }}>{u.role}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <select 
                            className="input-field" 
                            style={{ padding: '2px 8px', width: '130px', fontSize: '11px' }}
                            value={u.role} 
                            disabled={!isOwnerOrAdmin}
                            onChange={(e) => handleUserRoleChange(u.username, e.target.value)}
                          >
                            {appRoles.length === 0 ? (
                              <>
                                <option value="owner">Owner</option>
                                <option value="admin">Admin</option>
                                <option value="manager">Manager</option>
                                <option value="analyst">Analyst</option>
                                <option value="staff">Staff</option>
                              </>
                            ) : (
                              appRoles.map(r => (
                                <option key={r.id} value={r.id}>{r.name}</option>
                              ))
                            )}
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Operational Access Matrix</div>
              <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 16px 0' }}>Role-based feature access authorization definitions mapped across dynamic database permissions.</p>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e293b', color: '#f8fafc' }}>
                      <th style={{ padding: '10px 8px' }}>Role</th>
                      {permissionsList.map(p => (
                        <th key={p.id} style={{ padding: '10px 8px', textAlign: 'center' }}>{p.name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {matrixPermissions.map((row, idx) => {
                      const isEditable = getRolePriority(role) > getRolePriority(row.role);
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                          <td style={{ padding: '10px 8px', fontWeight: 600, color: '#f8fafc' }}>{row.role}</td>
                          {row.permissions.map((perm, pIdx) => {
                            const pObj = permissionsList[pIdx];
                            if (!pObj) return null;
                            return (
                              <td key={pIdx} style={{ padding: '10px 8px', textAlign: 'center' }}>
                                <span 
                                  className={`badge ${perm ? 'badge-success' : 'badge-failed'}`}
                                  style={{ 
                                    opacity: isEditable ? 1 : 0.6 
                                  }}
                                >
                                  {perm ? 'Yes' : 'No'}
                                </span>
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Role Hierarchy Relationships</div>
              <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 16px 0' }}>Configure parent-child role inheritances. A child inherits permissions from its parent.</p>
              <form onSubmit={handleAddHierarchy} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Parent Role (inheritee)</label>
                  <select className="input-field" style={{ width: '180px' }} value={parentRole} onChange={(e) => setParentRole(e.target.value)}>
                    {appRoles.length === 0 ? (
                      <>
                        <option value="owner">Owner</option>
                        <option value="admin">Admin</option>
                        <option value="manager">Manager</option>
                        <option value="analyst">Analyst</option>
                        <option value="staff">Staff</option>
                      </>
                    ) : (
                      appRoles.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))
                    )}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Child Role (inherits permissions)</label>
                  <select className="input-field" style={{ width: '180px' }} value={childRole} onChange={(e) => setChildRole(e.target.value)}>
                    {appRoles.length === 0 ? (
                      <>
                        <option value="owner">Owner</option>
                        <option value="admin">Admin</option>
                        <option value="manager">Manager</option>
                        <option value="analyst">Analyst</option>
                        <option value="staff">Staff</option>
                      </>
                    ) : (
                      appRoles.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))
                    )}
                  </select>
                </div>
                <button type="submit" className="btn btn-primary">Add Hierarchy Link</button>
              </form>
              {hierarchyStatus && (
                <div style={{ marginTop: '12px', fontSize: '12px', color: '#3b82f6' }}>{hierarchyStatus}</div>
              )}
            </div>

            <div className="card">
              <div className="card-title">Data Access Scopes</div>
              <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 16px 0' }}>Assign branch-specific context-aware access bounds to workspace user profiles.</p>
              <form onSubmit={handleAssignScope} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>User Member</label>
                  <select className="input-field" style={{ width: '180px' }} value={scopeUser} onChange={(e) => setScopeUser(e.target.value)}>
                    <option value="">Select User...</option>
                    {registeredUsers.map(u => (
                      <option key={u.username} value={u.username}>{u.username}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Scope Dimension</label>
                  <select className="input-field" style={{ width: '150px' }} value={scopeType} onChange={(e) => setScopeType(e.target.value)}>
                    <option value="branch">Branch Office</option>
                    <option value="department">Department</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', color: '#f8fafc', fontSize: '11px', marginBottom: '4px' }}>Scope Value</label>
                  <input type="text" className="input-field" style={{ width: '180px' }} placeholder="e.g. Chennai" value={scopeValue} onChange={(e) => setScopeValue(e.target.value)} />
                </div>
                <button type="submit" className="btn btn-primary">Assign Access Scope</button>
              </form>
              {scopeStatus && (
                <div style={{ marginTop: '12px', fontSize: '12px', color: '#3b82f6' }}>{scopeStatus}</div>
              )}
            </div>
          </div>
        )}

        {/* 5. License Management */}
        {settingsSubTab === 'license' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="card">
              <div className="card-title">Active Licensing Properties</div>
              <div style={{ fontSize: '13px', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>Product Edition: <strong style={{ color: '#3b82f6' }}>{licenseProperties.edition}</strong></div>
                <div>Licensed User Profiles: <strong>{licenseProperties.max_users} Max</strong></div>
                <div>Licensed Branches: <strong>{licenseProperties.max_branches} Branch Node{licenseProperties.max_branches > 1 ? 's' : ''}</strong></div>
              </div>
            </div>

            {isOwnerOrAdmin && (
              <div className="card">
                <div className="card-title">Upload Offline license File (.lic)</div>
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
                    Verify & Overwrite License
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

        {/* 6. Audit & Security */}
        {settingsSubTab === 'audit' && (
          <div className="card">
            <div className="card-title">System Activity Audit Log</div>
            {auditLoading ? (
              <div style={{ color: '#3b82f6', fontSize: '13px' }}>Loading historical events...</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #1e293b' }}>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>Timestamp</th>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>User</th>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>Action Event</th>
                      <th style={{ padding: '8px', color: '#f8fafc' }}>Target Resource</th>
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
                          <td style={{ padding: '8px', color: '#f8fafc' }}>{log.user_id || "System Setup"}</td>
                          <td style={{ padding: '8px', color: '#3b82f6', fontWeight: 600 }}>{log.action}</td>
                          <td style={{ padding: '8px', color: '#94a3b8' }}>{log.resource_type || "None"}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* 7. System Health */}
        {settingsSubTab === 'health' && (
          <div className="card">
            <div className="card-title">Service & Connection Health Metrics</div>
            {healthLoading ? (
              <div style={{ color: '#3b82f6', fontSize: '13px' }}>Checking component states...</div>
            ) : systemHealth ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '10px' }}>
                {Object.entries(systemHealth.components || {}).map(([compName, compStatus]) => {
                  let statusColor = '#ef4444';
                  if (compStatus === 'healthy' || compStatus === 'connected') statusColor = '#10b981';
                  else if (compStatus === 'warning') statusColor = '#f59e0b';
                  
                  return (
                    <div key={compName} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid #1e293b', borderRadius: '6px' }}>
                      <div style={{ fontWeight: 600, color: '#f8fafc', textTransform: 'capitalize' }}>
                        {compName.replace('_', ' ')} Service
                      </div>
                      <span className="badge" style={{ backgroundColor: `${statusColor}22`, color: statusColor, border: `1px solid ${statusColor}44`, textTransform: 'uppercase', fontSize: '10px' }}>
                        {String(compStatus)}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ color: '#94a3b8', fontSize: '13px' }}>System diagnostics unavailable.</div>
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
          {insightsLoading ? (
            <div style={{ color: '#3b82f6', fontSize: '13px', padding: '20px', textAlign: 'center' }}>Generating dynamic business alerts...</div>
          ) : businessInsights.length === 0 ? (
            <div style={{ color: '#94a3b8', fontSize: '13px', padding: '20px', textAlign: 'center' }}>No dynamic alerts or shortage risks found in current data.</div>
          ) : (
            businessInsights.map((insight, idx) => {
              let borderCol = '#3b82f6';
              let badgeClass = 'badge-success';
              const priority = insight.priority.toLowerCase();
              if (priority.includes('critical') || priority.includes('high') || priority.includes('error')) {
                borderCol = '#ef4444';
                badgeClass = 'badge-failed';
              } else if (priority.includes('medium') || priority.includes('warning') || priority.includes('pending')) {
                borderCol = '#f59e0b';
                badgeClass = 'badge-pending';
              } else if (priority.includes('opportunity') || priority.includes('success')) {
                borderCol = '#10b981';
                badgeClass = 'badge-success';
              }
              
              return (
                <div key={idx} className="card" style={{ borderLeft: `4px solid ${borderCol}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <strong style={{ color: '#f8fafc', fontSize: '14px' }}>{insight.title}</strong>
                    <span className={`badge ${badgeClass}`}>{insight.priority}</span>
                  </div>
                  <p style={{ margin: 0, color: '#94a3b8', fontSize: '13px' }}>
                    {insight.message}
                  </p>
                </div>
              );
            })
          )}
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
          {tablesCatalog.length === 0 ? (
            <div style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px', color: '#94a3b8', textAlign: 'center' }}>
              No relation schemas synced or configured yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {tablesCatalog.map((tbl: any, idx: number) => {
                const name = typeof tbl === 'object' && tbl !== null ? tbl.name : String(tbl);
                const typeStr = typeof tbl === 'object' && tbl !== null && tbl.type ? tbl.type : 'DuckDB Tabular Entity';
                const sizeStr = typeof tbl === 'object' && tbl !== null && tbl.size ? tbl.size : 'Mapped';
                return (
                  <div key={idx} style={{ padding: '12px 14px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong style={{ color: '#f8fafc', fontSize: '13px' }}>{name}</strong>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Type: {typeStr} | Size: {sizeStr}</div>
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
                {registeredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ padding: '12px 8px', color: '#94a3b8', textAlign: 'center' }}>No workspace profiles registered yet.</td>
                  </tr>
                ) : (
                  registeredUsers.map((user) => {
                    let roleColor = '#3b82f6';
                    let scopeText = 'Assigned Role Capabilities';
                    const r = user.role.toLowerCase();
                    if (r === 'owner' || r === 'admin') {
                      roleColor = '#ef4444';
                      scopeText = r === 'owner' ? 'Full System Access & License Keys' : 'Full System Access & Profile Registry Management';
                    } else if (r === 'manager') {
                      roleColor = '#f59e0b';
                      scopeText = 'Branch Management & Read-Write Schema Access';
                    } else if (r === 'analyst') {
                      roleColor = '#10b981';
                      scopeText = 'Read-only Schema Query & Reports Export';
                    } else if (r === 'staff') {
                      roleColor = '#94a3b8';
                      scopeText = 'Basic Operational Entry & System Logs Access';
                    }
                    
                    return (
                      <tr key={user.username} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '10px 8px', color: '#f8fafc', fontWeight: 500 }}>{user.username}</td>
                        <td style={{ padding: '10px 8px', color: roleColor, textTransform: 'capitalize' }}>{user.role}</td>
                        <td style={{ padding: '10px 8px', color: '#94a3b8' }}>{scopeText}</td>
                      </tr>
                    );
                  })
                )}
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
                              opacity: isEditable ? 1 : 0.6 
                            }}
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
          {auditLoading ? (
            <div style={{ color: '#3b82f6', fontSize: '13px', padding: '10px 0' }}>Loading sync logs history...</div>
          ) : auditLogs.length === 0 ? (
            <div style={{ color: '#94a3b8', fontSize: '13px', padding: '10px 0' }}>No pipeline ingestion or sync activities recorded yet.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', fontFamily: 'var(--mono)', color: '#94a3b8' }}>
              {auditLogs.map((log, idx) => (
                <div key={idx}>
                  [{log.timestamp || syncTime}] INFO: {log.action || 'System event'} - {log.resource_type || 'General'} (Resource: {log.resource_id || 'N/A'})
                </div>
              ))}
            </div>
          )}
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
          <li className={`sidebar-item ${activeMenu === 'users' || activeMenu === 'usersroles' ? 'active' : ''}`} onClick={() => setActiveMenu('users')} title="Users">
            <User size={14} />
            {!isCollapsed && <span>Users</span>}
          </li>
          <li className={`sidebar-item ${activeMenu === 'roles' ? 'active' : ''}`} onClick={() => setActiveMenu('roles')} title="Role Management">
            <Users size={14} />
            {!isCollapsed && <span>Role Management</span>}
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
          {activeMenu === 'users' && <UserManagement />}
          {activeMenu === 'roles' && <RoleManagement />}
          {activeMenu === 'organization' && renderOrganization()}
          {activeMenu === 'departments' && <DepartmentManagement />}
          {activeMenu === 'branches' && (
            <>
              {renderBranches()}
              <div style={{ marginTop: '20px' }}>
                <BranchManagement />
              </div>
            </>
          )}
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
      {/* Global License Key Required Modal */}
      {showLicenseModal && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(4px)'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '480px', backgroundColor: '#0d131f', border: '1px solid #3b82f6', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div className="card-title" style={{ margin: 0, color: '#f8fafc', fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Award size={20} style={{ color: '#3b82f6' }} />
                <span>CLARIUS License Key Required</span>
              </div>
              <button className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '12px' }} onClick={() => setShowLicenseModal(false)}>
                ✕
              </button>
            </div>

            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.4, marginBottom: '16px' }}>
              A valid <strong>CLARIUS / UNIVA</strong> offline license key (.lic) is required to execute AI queries, ingest spreadsheet files, process OCR documents, or connect ERP systems.
            </p>

            <form onSubmit={handleModalLicenseSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '6px', fontWeight: 500 }}>
                  Paste License Key Payload (.lic)
                </label>
                <textarea
                  className="input-field"
                  rows={4}
                  value={modalLicenseText}
                  onChange={(e) => setModalLicenseText(e.target.value)}
                  placeholder="Paste CLARIUS-LICENSE-v1 payload block here..."
                  style={{ fontFamily: 'var(--mono)', fontSize: '11px' }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}>
                  Or select local license file (.lic):
                </label>
                <input
                  type="file"
                  accept=".lic,.txt"
                  style={{ fontSize: '12px', color: '#94a3b8' }}
                  onChange={(e) => {
                    const selected = e.target.files?.[0];
                    if (selected) {
                      const reader = new FileReader();
                      reader.onload = (evt) => {
                        setModalLicenseText(evt.target?.result as string || '');
                      };
                      reader.readAsText(selected);
                    }
                  }}
                />
              </div>

              {modalLicStatus && (
                <div style={{
                  fontSize: '12px',
                  color: modalLicStatus.startsWith('Error') ? '#ef4444' : '#10b981',
                  backgroundColor: modalLicStatus.startsWith('Error') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${modalLicStatus.startsWith('Error') ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)'}`
                }}>
                  {modalLicStatus}
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowLicenseModal(false)}>
                  Close
                </button>
                <button type="submit" className="btn btn-primary" disabled={modalLicLoading}>
                  {modalLicLoading ? 'Verifying Key...' : 'Verify & Activate License'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
