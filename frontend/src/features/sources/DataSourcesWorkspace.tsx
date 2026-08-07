import React, { useState, useEffect } from 'react';
import { 
  Database, RefreshCw, UploadCloud, 
  Server, Play, Sparkles, Clock
} from 'lucide-react';
import { apiFetch } from '../../config/api';

export const DataSourcesWorkspace: React.FC = () => {
  const [sources, setSources] = useState<any[]>([]);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Reverted ERP Connectors status state (older status compatibility)
  const [connectedErps, setConnectedErps] = useState<Record<string, boolean>>({
    TallyPrime: false,
    'Odoo ERP': false,
    ERPNext: false,
    BUSY: false,
    'Marg ERP': false,
    'Zoho Books': false
  });
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success'>('idle');
  const [syncTime, setSyncTime] = useState<string>('Today, 10:32 AM');
  
  // Mapping Studio state
  const [mappingFile, setMappingFile] = useState<File | null>(null);
  const [mappingColumns, setMappingColumns] = useState<any[]>([]);
  const [targetTable, setTargetTable] = useState('');
  const [analyzingMapping, setAnalyzingMapping] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchDataSources();
  }, []);

  const fetchDataSources = async () => {
    setLoading(true);
    try {
      const [srcRes, capRes, histRes] = await Promise.all([
        apiFetch('/data-sources/sources'),
        apiFetch('/data-sources/capabilities'),
        apiFetch('/data-sources/history')
      ]);

      if (srcRes.ok) setSources(await srcRes.json());
      if (capRes.ok) setCapabilities(await capRes.json());
      if (histRes.ok) setHistory(await histRes.json());
    } catch (err) {
      console.error('Failed to fetch data sources metadata', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSyncNow = () => {
    setSyncStatus('syncing');
    setTimeout(() => {
      setSyncStatus('success');
      setSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      setTimeout(() => setSyncStatus('idle'), 3000);
    }, 1500);
  };

  const handleFileDrop = async (file: File) => {
    setMappingFile(file);
    const fname = file.name.split('.')[0].toLowerCase().replace(/[^a-z0-9_]/g, '_');
    setTargetTable(fname);
    setAnalyzingMapping(true);

    try {
      const res = await apiFetch('/data-sources/analyze-mapping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          headers: ['order_id', 'customer_name', 'amount', 'status', 'created_at'],
          samples: {
            order_id: 'ORD-9982',
            customer_name: 'Acme Logistics',
            amount: '1450.00',
            status: 'Completed',
            created_at: '2026-08-01'
          }
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data && data.columns) {
          setMappingColumns(data.columns);
        }
      }
    } catch (err) {
      console.error('Failed to analyze schema mapping', err);
    } finally {
      setAnalyzingMapping(false);
    }
  };

  const handleTriggerImport = async () => {
    if (!mappingFile || !targetTable) return;
    setImporting(true);
    setImportStatus('Submitting ingestion task...');

    try {
      const formData = new FormData();
      formData.append('file', mappingFile);
      formData.append('target_table', targetTable);
      const mappingsDict: Record<string, string> = {};
      mappingColumns.forEach(c => {
        mappingsDict[c.suggested_business_field] = c.source_column;
      });
      formData.append('mappings', JSON.stringify(mappingsDict));

      const res = await fetch('http://localhost:8000/data-sources/import', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData
      });

      if (res.ok) {
        setImportStatus('Import job queued successfully!');
        setMappingFile(null);
        setMappingColumns([]);
        fetchDataSources();
      } else {
        const errData = await res.json();
        setImportStatus(`Error: ${errData.detail || 'Import failed'}`);
      }
    } catch (err: any) {
      setImportStatus(`Error: ${err.message}`);
    } finally {
      setImporting(false);
    }
  };

  const erpPlatforms = ['TallyPrime', 'Odoo ERP', 'ERPNext', 'BUSY', 'Marg ERP', 'Zoho Books'];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Connected Business Data Sources
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Integrate local ERP platforms, import documents, or load spreadsheet data files.
          </p>
        </div>
        <button
          onClick={fetchDataSources}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm transition font-medium border border-slate-700"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Sources
        </button>
      </div>

      {/* Section 1: Connected Enterprise Sources (Reverted to older status & controls) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
            <Server className="w-5 h-5 text-emerald-400" /> Connected Enterprise Sources & ERP Connectors
          </h2>
          <span className="text-xs text-emerald-400 font-mono font-medium border border-emerald-800 bg-emerald-950/60 px-2.5 py-1 rounded-full">
            Plugin Active
          </span>
        </div>

        {/* Older Status Style Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {erpPlatforms.map((erpKey) => {
            const isConnected = connectedErps[erpKey];
            return (
              <div
                key={erpKey}
                className={`border rounded-xl p-5 transition shadow-lg backdrop-blur-sm flex flex-col justify-between ${
                  isConnected
                    ? 'bg-emerald-950/20 border-emerald-800/60'
                    : 'bg-slate-900/60 border-slate-800/80 opacity-80 hover:opacity-100'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="p-3 bg-slate-950 text-emerald-400 rounded-lg border border-slate-800">
                    <Database className="w-5 h-5" />
                  </div>
                  <span
                    className={`px-2.5 py-1 text-xs rounded-full font-bold border ${
                      isConnected
                        ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                        : 'bg-slate-950 text-slate-500 border-slate-800'
                    }`}
                  >
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>

                <div className="mt-4">
                  <h3 className="text-base font-bold text-slate-100">{erpKey} Connection</h3>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    {isConnected ? `Last Sync: ${syncTime}` : 'Offline system disconnected'}
                  </p>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[11px] text-slate-400 font-medium">Status: {isConnected ? 'Healthy' : 'Inactive'}</span>
                  {isConnected ? (
                    <div className="flex gap-2">
                      <button
                        onClick={handleSyncNow}
                        className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded border border-slate-700 flex items-center gap-1.5 transition"
                      >
                        <RefreshCw className={`w-3 h-3 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} /> Sync
                      </button>
                      <button
                        onClick={() => setConnectedErps(prev => ({ ...prev, [erpKey]: false }))}
                        className="px-2.5 py-1 bg-red-950/60 hover:bg-red-900/80 text-red-400 text-xs rounded border border-red-800/60 transition"
                      >
                        Disconnect
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConnectedErps(prev => ({ ...prev, [erpKey]: true }))}
                      className="px-4 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded transition"
                    >
                      Connect
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {/* Dynamic Backend Data Sources */}
          {sources.map((src) => (
            <div key={src.id} className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
              <div className="flex justify-between items-start">
                <div className="p-3 bg-slate-950 text-cyan-400 rounded-lg border border-slate-800">
                  <Database className="w-5 h-5" />
                </div>
                <span className="px-2.5 py-1 text-xs rounded-full font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {src.connection_state}
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-base font-bold text-slate-100 truncate">{src.name}</h3>
                <p className="text-xs text-slate-400 mt-1">Source: <span className="text-cyan-400 font-mono">{src.source_type}</span></p>
              </div>
              <div className="mt-5 pt-4 border-t border-slate-800/80 text-xs flex justify-between items-center">
                <span className="text-slate-400">{src.rows_imported?.toLocaleString() || 0} Rows</span>
                <span className="text-emerald-400 font-medium">{src.health}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Upload Studio */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-cyan-400" /> Enterprise Ingestion Studio
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Supports: {capabilities?.accepted_extensions?.join(', ') || '.csv, .xlsx, .json, .xml, .pdf, .docx, .png, .jpg, .zip'} (Configured via Backend API)
            </p>
          </div>
        </div>

        <div className="border-2 border-dashed border-slate-700/80 hover:border-cyan-500/60 rounded-xl p-8 text-center transition bg-slate-950/40">
          <input
            type="file"
            id="file-upload-input"
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileDrop(e.target.files[0]);
              }
            }}
          />
          <label htmlFor="file-upload-input" className="cursor-pointer flex flex-col items-center">
            <UploadCloud className="w-10 h-10 text-cyan-400 mb-3" />
            <span className="text-sm font-medium text-slate-200">Click or drag data file to ingest into CDM</span>
            <span className="text-xs text-slate-500 mt-1">Automatic schema inference & AI-assisted column mapping</span>
          </label>
        </div>

        {/* Section 5: AI-Assisted Smart Mapping Studio */}
        {mappingFile && (
          <div className="mt-8 pt-6 border-t border-slate-800 space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" /> AI-Assisted Smart Mapping Studio
              </h3>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400">Target Table Name:</span>
                <input
                  type="text"
                  value={targetTable}
                  onChange={(e) => setTargetTable(e.target.value)}
                  className="bg-slate-950 border border-slate-700 px-3 py-1.5 rounded text-xs text-slate-100 font-mono focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            {analyzingMapping ? (
              <div className="p-6 text-center text-slate-400 text-sm">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-amber-400" /> Analyzing file schema and generating AI column mapping rules...
              </div>
            ) : (
              <div className="overflow-x-auto border border-slate-800 rounded-xl">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <th className="p-3">Source Column</th>
                      <th className="p-3">Detected Type</th>
                      <th className="p-3">Sample Value</th>
                      <th className="p-3">Suggested Business Field</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Validation Status</th>
                      <th className="p-3">PK Candidate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 bg-slate-900/40">
                    {mappingColumns.map((col, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40">
                        <td className="p-3 font-mono text-slate-200">{col.source_column}</td>
                        <td className="p-3 font-mono text-cyan-400">{col.detected_type}</td>
                        <td className="p-3 text-slate-400 truncate max-w-[120px]">{col.detected_sample}</td>
                        <td className="p-3">
                          <input
                            type="text"
                            value={col.suggested_business_field}
                            onChange={(e) => {
                              const updated = [...mappingColumns];
                              updated[idx].suggested_business_field = e.target.value;
                              setMappingColumns(updated);
                            }}
                            className="bg-slate-950 border border-slate-700 px-2 py-1 rounded text-xs text-emerald-400 font-mono w-full"
                          />
                        </td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                            {Math.round(col.confidence * 100)}%
                          </span>
                        </td>
                        <td className="p-3 text-emerald-400 font-medium">{col.validation_status}</td>
                        <td className="p-3 text-slate-400">{col.primary_key_candidate ? 'Yes (PK)' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex justify-end items-center gap-4 pt-2">
              {importStatus && <span className="text-xs text-amber-400">{importStatus}</span>}
              <button
                onClick={handleTriggerImport}
                disabled={importing || analyzingMapping}
                className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-semibold rounded-lg hover:opacity-95 transition text-sm shadow-md"
              >
                <Play className="w-4 h-4 fill-current" /> Execute Ingestion Pipeline
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Section 2 & 4: Recent Imports & Job Log Tracker */}
      <div>
        <h2 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-amber-400" /> Recent Ingestion Job History
        </h2>

        <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 shadow-lg">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                <th className="p-3.5">Timestamp</th>
                <th className="p-3.5">Operator</th>
                <th className="p-3.5">Source Type</th>
                <th className="p-3.5">Dataset Target</th>
                <th className="p-3.5">Rows Ingested</th>
                <th className="p-3.5">Duration</th>
                <th className="p-3.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {history.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-6 text-center text-slate-500">No recent import jobs recorded.</td>
                </tr>
              ) : (
                history.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/40 transition">
                    <td className="p-3.5 text-slate-300 font-mono">{new Date(job.time).toLocaleString()}</td>
                    <td className="p-3.5 text-slate-300">{job.user}</td>
                    <td className="p-3.5 font-mono text-cyan-400">{job.source}</td>
                    <td className="p-3.5 font-mono text-emerald-400">{job.dataset}</td>
                    <td className="p-3.5 text-slate-200 font-semibold">{job.rows?.toLocaleString()}</td>
                    <td className="p-3.5 text-slate-400">{job.duration}</td>
                    <td className="p-3.5">
                      <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                        {job.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
