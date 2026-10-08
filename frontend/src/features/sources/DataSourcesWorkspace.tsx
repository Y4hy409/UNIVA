import React, { useState, useEffect } from 'react';
import { 
  RefreshCw, UploadCloud, 
  Play, Sparkles, Clock, Eye, X, FolderUp, FileText, CheckCircle2, AlertCircle, Layers
} from 'lucide-react';
import { apiFetch } from '../../config/api';

interface BatchFileItem {
  file: File;
  name: string;
  path: string;
  size: string;
  targetTable: string;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  error?: string;
  rows?: number;
  columns?: number;
}

export const DataSourcesWorkspace: React.FC = () => {
  const [capabilities, setCapabilities] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Ingestion Mode: 'file' | 'folder'
  const [uploadMode, setUploadMode] = useState<'file' | 'folder'>('file');

  // Single File Mapping Studio state
  const [mappingFile, setMappingFile] = useState<File | null>(null);
  const [mappingColumns, setMappingColumns] = useState<any[]>([]);
  const [targetTable, setTargetTable] = useState('');
  const [analyzingMapping, setAnalyzingMapping] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  // Folder Batch Upload state
  const [folderFiles, setFolderFiles] = useState<BatchFileItem[]>([]);
  const [batchImporting, setBatchImporting] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; message: string } | null>(null);

  // Table Preview Modal state
  const [previewTable, setPreviewTable] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<{ columns: string[]; rows: any[] }>({ columns: [], rows: [] });
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    fetchDataSources();
  }, []);

  const fetchDataSources = async () => {
    setLoading(true);
    try {
      const [capRes, histRes] = await Promise.all([
        apiFetch('/data-sources/capabilities'),
        apiFetch('/data-sources/history')
      ]);

      if (capRes.ok) setCapabilities(await capRes.json());
      if (histRes.ok) setHistory(await histRes.json());
    } catch (err) {
      console.error('Failed to fetch data sources metadata', err);
    } finally {
      setLoading(false);
    }
  };

  const formatLocalTimestamp = (timeStr: any): string => {
    if (!timeStr) return 'Just now';
    try {
      let date: Date;
      if (typeof timeStr === 'string') {
        if (!timeStr.endsWith('Z') && !timeStr.includes('+') && !(timeStr.length > 10 && timeStr.substring(10).includes('-'))) {
          date = new Date(timeStr + 'Z');
        } else {
          date = new Date(timeStr);
        }
      } else {
        date = new Date(timeStr);
      }
      if (isNaN(date.getTime())) {
        date = new Date(timeStr);
      }
      if (isNaN(date.getTime())) {
        return String(timeStr);
      }
      return date.toLocaleString();
    } catch {
      return String(timeStr);
    }
  };

  const handlePreviewTable = async (tableName: string) => {
    if (!tableName) return;
    setPreviewTable(tableName);
    setPreviewLoading(true);
    try {
      const res = await apiFetch(`/data-sources/preview/${encodeURIComponent(tableName)}`);
      if (res.ok) {
        const data = await res.json();
        setPreviewData({ columns: data.columns || [], rows: data.data || [] });
      }
    } catch (err) {
      console.error('Failed to fetch table preview', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  const sanitizeTableName = (filename: string): string => {
    const stem = filename.split('.')[0] || 'dataset';
    const clean = stem.toLowerCase().replace(/[^a-z0-9_]/g, '_').replace(/^_+|_+$/g, '');
    return clean || 'dataset';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const parseLocalFile = async (file: File) => {
    try {
      const text = await file.text();
      let cols: any[] = [];

      if (file.name.endsWith('.json')) {
        const parsed = JSON.parse(text);
        const records = Array.isArray(parsed) ? parsed : [parsed];
        if (records.length > 0 && typeof records[0] === 'object') {
          const keys = Object.keys(records[0]);
          cols = keys.map((key) => {
            const val = records[0][key];
            const isNum = typeof val === 'number';
            const kClean = key.toLowerCase().replace(/[^a-z0-9_]/g, '_');
            const excludePk = ['date', 'time', 'created', 'updated', 'phone', 'fax', 'mobile', 'email', 'address', 'status', 'type', 'name', 'amount', 'price', 'qty', 'count', 'desc', 'comment', 'note'].some(ex => kClean.includes(ex));
            const tokens = kClean.split('_');
            const hasPkToken = tokens.includes('id') || tokens.includes('pk') || tokens.includes('sku') || tokens.includes('uuid') || tokens.includes('key') || kClean.endsWith('_id') || kClean.endsWith('_pk') || kClean.endsWith('_key') || kClean.endsWith('_no') || kClean.endsWith('_num') || kClean.endsWith('_code') || ['id', 'pk', 'uuid', 'sku', 'invoice_no', 'order_no', 'txn_no', 'transaction_id', 'receipt_no'].includes(kClean);
            const isPk = hasPkToken && !excludePk;
            return {
              source_column: key,
              detected_type: isNum ? 'DOUBLE' : 'VARCHAR',
              detected_sample: String(val ?? 'N/A'),
              suggested_business_field: key,
              confidence: isPk ? 0.99 : 0.95,
              validation_status: 'Automatically Validated',
              primary_key_candidate: isPk
            };
          });
        }
      } else {
        const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
        if (lines.length > 0) {
          const splitLine = (l: string) => {
            const result: string[] = [];
            let current = '';
            let inQuotes = false;
            for (let i = 0; i < l.length; i++) {
              const char = l[i];
              if (char === '"') inQuotes = !inQuotes;
              else if (char === ',' && !inQuotes) {
                result.push(current.trim().replace(/^["']|["']$/g, ''));
                current = '';
              } else {
                current += char;
              }
            }
            result.push(current.trim().replace(/^["']|["']$/g, ''));
            return result;
          };

          const headers = splitLine(lines[0]);
          const sampleValues = lines.length > 1 ? splitLine(lines[1]) : [];

          cols = headers
            .filter(col => col && col.trim() !== '')
            .map((col, idx) => {
              const val = sampleValues[idx] || 'N/A';
              const isNum = !isNaN(Number(val)) && val !== '';
              const cClean = col.toLowerCase().replace(/[^a-z0-9_]/g, '_');
              const excludePk = ['date', 'time', 'created', 'updated', 'phone', 'fax', 'mobile', 'email', 'address', 'status', 'type', 'name', 'amount', 'price', 'qty', 'count', 'desc', 'comment', 'note'].some(ex => cClean.includes(ex));
              const tokens = cClean.split('_');
              const hasPkToken = tokens.includes('id') || tokens.includes('pk') || tokens.includes('sku') || tokens.includes('uuid') || tokens.includes('key') || cClean.endsWith('_id') || cClean.endsWith('_pk') || cClean.endsWith('_key') || cClean.endsWith('_no') || cClean.endsWith('_num') || cClean.endsWith('_code') || ['id', 'pk', 'uuid', 'sku', 'invoice_no', 'order_no', 'txn_no', 'transaction_id', 'receipt_no'].includes(cClean);
              const isPk = hasPkToken && !excludePk;
              return {
                source_column: col,
                detected_type: isNum ? (val.includes('.') ? 'DOUBLE' : 'BIGINT') : 'VARCHAR',
                detected_sample: val,
                suggested_business_field: col,
                confidence: isPk ? 0.99 : 0.95,
                validation_status: 'Automatically Validated',
                primary_key_candidate: isPk
              };
            });
        }
      }

      return cols;
    } catch (err) {
      console.warn('Local file parsing warning:', err);
      return [];
    }
  };

  const handleSingleFileSelect = async (file: File) => {
    setMappingFile(file);
    const fname = sanitizeTableName(file.name);
    setTargetTable(fname);
    setAnalyzingMapping(true);
    setImportStatus(null);

    const localCols = await parseLocalFile(file);
    if (localCols.length > 0) {
      setMappingColumns(localCols);
    }

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiFetch('/data-sources/analyze', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        if (data.mapped_fields && data.mapped_fields.length > 0) {
          setMappingColumns(data.mapped_fields);
        }
      }
    } catch (err) {
      console.warn('Backend schema analysis fallback to local client parser', err);
    } finally {
      setAnalyzingMapping(false);
    }
  };

  const handleFolderFilesSelected = (filesList: FileList | File[]) => {
    const acceptedExts = ['.csv', '.xlsx', '.xls', '.json', '.xml'];
    const validItems: BatchFileItem[] = [];

    Array.from(filesList).forEach((file) => {
      const name = file.name;
      const lowerName = name.toLowerCase();
      const isAccepted = acceptedExts.some(ext => lowerName.endsWith(ext));
      // Ignore hidden files and system artifacts
      if (isAccepted && !name.startsWith('.') && !name.startsWith('~$')) {
        const relativePath = (file as any).webkitRelativePath || file.name;
        validItems.push({
          file,
          name: file.name,
          path: relativePath,
          size: formatFileSize(file.size),
          targetTable: sanitizeTableName(file.name),
          status: 'pending'
        });
      }
    });

    setFolderFiles(validItems);
  };

  const handleExecuteBatchImport = async () => {
    if (folderFiles.length === 0) return;
    setBatchImporting(true);
    setBatchProgress({ current: 0, total: folderFiles.length, message: 'Starting folder batch import...' });

    const updated = [...folderFiles];

    for (let i = 0; i < folderFiles.length; i++) {
      const item = folderFiles[i];
      updated[i].status = 'uploading';
      setFolderFiles([...updated]);
      setBatchProgress({
        current: i + 1,
        total: folderFiles.length,
        message: `Ingesting ${item.name} into table '${item.targetTable}'...`
      });

      try {
        const formData = new FormData();
        formData.append('file', item.file);
        formData.append('target_table', item.targetTable);
        formData.append('mappings', JSON.stringify([]));

        const res = await apiFetch('/data-sources/upload', {
          method: 'POST',
          body: formData
        });

        if (res.ok) {
          updated[i].status = 'completed';
        } else {
          const err = await res.json();
          updated[i].status = 'failed';
          updated[i].error = err.detail || 'Import failed';
        }
      } catch (err: any) {
        updated[i].status = 'failed';
        updated[i].error = err.message || 'Network error';
      }

      setFolderFiles([...updated]);
    }

    setBatchImporting(false);
    setBatchProgress({
      current: folderFiles.length,
      total: folderFiles.length,
      message: `Completed importing ${folderFiles.length} files into DuckDB.`
    });
    fetchDataSources();
  };

  const handleTriggerSingleImport = async () => {
    if (!mappingFile || !targetTable.trim()) return;

    setImporting(true);
    setImportStatus('Uploading data file and creating DuckDB table...');

    try {
      const formData = new FormData();
      formData.append('file', mappingFile);
      formData.append('target_table', targetTable.trim());
      formData.append('mappings', JSON.stringify(mappingColumns));

      const res = await apiFetch('/data-sources/upload', {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setImportStatus(`Success! Job #${data.job_id} initiated. Dataset loaded into DuckDB.`);
        setTimeout(() => {
          setMappingFile(null);
          setImportStatus(null);
          fetchDataSources();
        }, 1500);
      } else {
        const err = await res.json();
        setImportStatus(`Error: ${err.detail || 'Import failed'}`);
      }
    } catch (err: any) {
      setImportStatus(`Import Error: ${err.message || 'Server error'}`);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Connected Business Data Sources
          </h1>
        </div>
        <button
          onClick={fetchDataSources}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm transition font-medium border border-slate-700"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Sources
        </button>
      </div>

      {/* SECTION 1: Enterprise Ingestion Studio */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-cyan-400" /> Enterprise Ingestion Studio
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Supports: {capabilities?.accepted_extensions?.join(', ') || '.csv, .xlsx, .xls, .json, .xml, .pdf, .docx, .png, .jpg, .zip'}
            </p>
          </div>

          {/* Mode Switcher: Single File vs Entire Folder */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 self-start sm:self-auto">
            <button
              onClick={() => { setUploadMode('file'); }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 ${
                uploadMode === 'file'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" /> Single File
            </button>
            <button
              onClick={() => { setUploadMode('folder'); }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-2 ${
                uploadMode === 'folder'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FolderUp className="w-3.5 h-3.5" /> Entire Folder
            </button>
          </div>
        </div>

        {/* Drop Zone: Single File Mode */}
        {uploadMode === 'file' && (
          <div className="border-2 border-dashed border-slate-700/80 hover:border-cyan-500/60 rounded-xl p-8 text-center transition bg-slate-950/40">
            <input
              type="file"
              id="single-file-upload-input"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleSingleFileSelect(e.target.files[0]);
                }
              }}
            />
            <label htmlFor="single-file-upload-input" className="cursor-pointer flex flex-col items-center">
              <UploadCloud className="w-10 h-10 text-cyan-400 mb-3" />
              <span className="text-sm font-medium text-slate-200">Click or drag file to ingest into CDM</span>
              <span className="text-xs text-slate-500 mt-1">Automatic schema inference & AI-assisted column mapping</span>
            </label>
          </div>
        )}

        {/* Drop Zone: Entire Folder Mode */}
        {uploadMode === 'folder' && (
          <div className="space-y-4">
            <div className="border-2 border-dashed border-cyan-800/60 hover:border-cyan-400/80 rounded-xl p-8 text-center transition bg-cyan-950/10">
              <input
                type="file"
                id="folder-upload-input"
                className="hidden"
                // @ts-expect-error webkitdirectory is non-standard but widely supported in all modern browsers
                webkitdirectory=""
                directory=""
                multiple
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFolderFilesSelected(e.target.files);
                  }
                }}
              />
              <label htmlFor="folder-upload-input" className="cursor-pointer flex flex-col items-center">
                <FolderUp className="w-12 h-12 text-cyan-400 mb-3" />
                <span className="text-sm font-semibold text-slate-200">Select or Drag Entire Data Folder</span>
                <span className="text-xs text-slate-400 mt-1">
                  Recursively imports all CSV, Excel (.xlsx/.xls), JSON, and XML files into independent DuckDB tables
                </span>
              </label>
            </div>

            {/* Folder Ingestion Queue Table */}
            {folderFiles.length > 0 && (
              <div className="space-y-4 pt-2">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950/80 border border-slate-800 p-4 rounded-xl">
                  <div className="flex items-center gap-3">
                    <Layers className="w-5 h-5 text-emerald-400" />
                    <div>
                      <span className="text-sm font-bold text-slate-100">{folderFiles.length} Compatible Files Detected</span>
                      <span className="text-xs text-slate-400 block">Ready to import directly into DuckDB tables</span>
                    </div>
                  </div>
                  <button
                    onClick={handleExecuteBatchImport}
                    disabled={batchImporting}
                    className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold rounded-lg hover:opacity-95 transition text-xs shadow-md disabled:opacity-50"
                  >
                    <Play className={`w-3.5 h-3.5 fill-current ${batchImporting ? 'animate-spin' : ''}`} />
                    {batchImporting ? 'Importing Folder Files...' : 'Import All Folder Files'}
                  </button>
                </div>

                {batchProgress && (
                  <div className="p-3 bg-slate-950 border border-cyan-800/60 rounded-xl text-xs flex items-center justify-between text-cyan-300">
                    <span>{batchProgress.message}</span>
                    <span className="font-mono font-bold">{batchProgress.current} / {batchProgress.total}</span>
                  </div>
                )}

                <div className="overflow-x-auto border border-slate-800 rounded-xl max-h-72 overflow-y-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
                        <th className="p-3">File Name</th>
                        <th className="p-3">Folder Path</th>
                        <th className="p-3">Size</th>
                        <th className="p-3">Target Table Name (DuckDB)</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 bg-slate-900/40">
                      {folderFiles.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40">
                          <td className="p-3 font-medium text-slate-200">{item.name}</td>
                          <td className="p-3 text-slate-400 font-mono truncate max-w-[200px]">{item.path}</td>
                          <td className="p-3 text-slate-400">{item.size}</td>
                          <td className="p-3">
                            <input
                              type="text"
                              value={item.targetTable}
                              disabled={batchImporting}
                              onChange={(e) => {
                                const updated = [...folderFiles];
                                updated[idx].targetTable = sanitizeTableName(e.target.value);
                                setFolderFiles(updated);
                              }}
                              className="bg-slate-950 border border-slate-700 px-2.5 py-1 rounded text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500 w-full max-w-[200px]"
                            />
                          </td>
                          <td className="p-3">
                            {item.status === 'pending' && (
                              <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                                Ready
                              </span>
                            )}
                            {item.status === 'uploading' && (
                              <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1 w-fit">
                                <RefreshCw className="w-3 h-3 animate-spin" /> Ingesting
                              </span>
                            )}
                            {item.status === 'completed' && (
                              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1 w-fit">
                                <CheckCircle2 className="w-3 h-3" /> Ingested
                              </span>
                            )}
                            {item.status === 'failed' && (
                              <span className="px-2 py-0.5 rounded text-[10px] bg-red-950 text-red-400 border border-red-800 flex items-center gap-1 w-fit" title={item.error}>
                                <AlertCircle className="w-3 h-3" /> Error
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* AI-Assisted Smart Mapping Studio for Single File */}
        {uploadMode === 'file' && mappingFile && (
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
                onClick={handleTriggerSingleImport}
                disabled={importing || analyzingMapping}
                className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-semibold rounded-lg hover:opacity-95 transition text-sm shadow-md"
              >
                <Play className="w-4 h-4 fill-current" /> Execute Ingestion Pipeline
              </button>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 2: Recent Ingestion Job History (With View Button) */}
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
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {history.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-slate-500">No recent import jobs recorded.</td>
                </tr>
              ) : (
                history.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/40 transition">
                    <td className="p-3.5 text-slate-300 font-mono">{formatLocalTimestamp(job.time)}</td>
                    <td className="p-3.5 text-slate-300">{job.user}</td>
                    <td className="p-3.5 font-mono text-cyan-400">{job.source}</td>
                    <td className="p-3.5 font-mono text-emerald-400">{job.dataset}</td>
                    <td className="p-3.5">
                      <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                        {job.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        onClick={() => handlePreviewTable(job.dataset)}
                        className="px-3 py-1 bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 rounded border border-cyan-800/60 text-xs font-medium inline-flex items-center gap-1.5 transition"
                      >
                        <Eye className="w-3.5 h-3.5" /> View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Table View Drawer / Modal */}
      {previewTable && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <Eye className="w-5 h-5 text-cyan-400" /> View Dataset: <span className="font-mono text-emerald-400">{previewTable}</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">All records stored in DuckDB table ({previewData.rows.length} rows)</p>
              </div>
              <button
                onClick={() => setPreviewTable(null)}
                className="p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {previewLoading ? (
                <div className="p-8 text-center text-slate-400 text-sm">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-400" /> Loading dataset records from DuckDB...
                </div>
              ) : previewData.columns.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm">
                  No records stored in this table.
                </div>
              ) : (
                <div className="overflow-x-auto border border-slate-800 rounded-xl">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-950 text-slate-300 border-b border-slate-800">
                        {previewData.columns.map((col, i) => (
                          <th key={i} className="p-3 font-mono text-cyan-400 whitespace-nowrap">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 bg-slate-900/40">
                      {previewData.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-800/40">
                          {previewData.columns.map((col, cIdx) => (
                            <td key={cIdx} className="p-3 text-slate-300 whitespace-nowrap">{String(row[col] ?? 'NULL')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
