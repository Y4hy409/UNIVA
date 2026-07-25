import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, AlertTriangle, Plus } from 'lucide-react';

interface MappingTarget {
  name: string;
  fields: string[];
}

const TARGETS: MappingTarget[] = [
  {
    name: 'Sales Transactions',
    fields: ['transaction_id', 'customer_name', 'product_name', 'quantity', 'amount', 'transaction_date']
  },
  {
    name: 'Purchase Orders',
    fields: ['invoice_id', 'supplier_name', 'item_name', 'quantity', 'cost', 'purchase_date']
  },
  {
    name: 'Inventory Items',
    fields: ['item_id', 'item_name', 'stock_level', 'reorder_point', 'unit_price']
  }
];

interface ColumnsMapperProps {
  onIngestSuccess?: (fileName: string, format: string, size: string) => void;
}

export const ColumnsMapper: React.FC<ColumnsMapperProps> = ({ onIngestSuccess }) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [file, setFile] = useState<File | null>(null);
  const [fileFormat, setFileFormat] = useState<'csv' | 'excel' | 'json' | 'xml'>('csv');
  const [targetEntity, setTargetEntity] = useState<string>('Sales Transactions');
  const [customCategory, setCustomCategory] = useState('');
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mappings, setMappings] = useState<Dict<string, string>>({});
  const [ingesting, setIngesting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Ingested Tables catalog states
  const [tablesList, setTablesList] = useState<string[]>([]);
  const [activePreview, setActivePreview] = useState<string | null>(null);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  type Dict<K extends string | number | symbol, V> = { [key in K]: V };

  const fetchTablesCatalog = async () => {
    try {
      const res = await fetch('http://localhost:8000/data-sources/tables', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTablesList(data.tables || []);
      }
    } catch (err) {
      console.error("Failed to load tables catalog", err);
    }
  };

  const handlePreviewTable = async (tableName: string) => {
    setPreviewLoading(true);
    setActivePreview(tableName);
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

  React.useEffect(() => {
    fetchTablesCatalog();
  }, []);

  // Parse CSV headers locally in browser
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files ? e.target.files[0] : null;
    if (!selectedFile) return;

    setFile(selectedFile);
    setErrorMsg(null);

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split('\n');
      if (lines.length > 0) {
        const firstLine = lines[0].trim();
        const parsedHeaders = firstLine.split(',').map((h) => h.replace(/["']/g, '').trim());
        setHeaders(parsedHeaders);
        
        // Auto-bootstrap mapping suggestions (AI simulation based on header names matching fields)
        const targetObj = TARGETS.find(t => t.name === targetEntity);
        const initialMappings: Dict<string, string> = {};
        if (targetObj) {
          targetObj.fields.forEach(field => {
            const matched = parsedHeaders.find(h => h.toLowerCase() === field.toLowerCase() || h.toLowerCase().replace(/_/g, ' ') === field.toLowerCase().replace(/_/g, ' '));
            if (matched) {
              initialMappings[field] = matched;
            }
          });
        }
        setMappings(initialMappings);
      }
    };
    reader.readAsText(selectedFile);
  };

  const handleFieldMapChange = (field: string, headerValue: string) => {
    setMappings((prev) => ({
      ...prev,
      [field]: headerValue
    }));
  };

  const executeIngest = async () => {
    if (!file) return;

    setIngesting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_table', targetEntity.toLowerCase().replace(/ /g, '_'));
    formData.append('mappings', JSON.stringify(mappings));

    try {
      const response = await fetch('http://localhost:8000/data-sources/import', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ingestion failed');
      }

      setSuccessMsg('Pipeline mappings saved! Ingestion job triggered successfully in the background.');
      setStep(3);
      fetchTablesCatalog();
      if (onIngestSuccess && file) {
        onIngestSuccess(file.name, fileFormat.toUpperCase(), (file.size / 1024).toFixed(1) + ' KB');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit pipeline job.');
    } finally {
      setIngesting(false);
    }
  };

  const handleCreateCustomType = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customCategory.trim()) return;
    TARGETS.push({
      name: customCategory,
      fields: ['id', 'name', 'details', 'created_at']
    });
    setTargetEntity(customCategory);
    setCustomCategory('');
    setShowCustomModal(false);
  };

  const selectedTarget = TARGETS.find((t) => t.name === targetEntity);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Progress steps banner */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '10px' }}>
        <div style={{ opacity: step === 1 ? 1 : 0.5, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ display: 'inline-flex', width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#3b82f6', color: '#ffffff', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '11px' }}>1</span>
          <span style={{ color: '#f8fafc', fontWeight: 600, fontSize: '13px' }}>Upload File</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', color: '#1e293b' }}><ArrowRight size={14} /></div>
        <div style={{ opacity: step === 2 ? 1 : 0.5, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ display: 'inline-flex', width: '20px', height: '20px', borderRadius: '50%', backgroundColor: step >= 2 ? '#3b82f6' : '#1e293b', color: step >= 2 ? '#ffffff' : '#94a3b8', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '11px' }}>2</span>
          <span style={{ color: '#f8fafc', fontWeight: 600, fontSize: '13px' }}>Map Columns</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', color: '#1e293b' }}><ArrowRight size={14} /></div>
        <div style={{ opacity: step === 3 ? 1 : 0.5, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ display: 'inline-flex', width: '20px', height: '20px', borderRadius: '50%', backgroundColor: step === 3 ? '#3b82f6' : '#1e293b', color: step === 3 ? '#ffffff' : '#94a3b8', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '11px' }}>3</span>
          <span style={{ color: '#f8fafc', fontWeight: 600, fontSize: '13px' }}>Confirm & Import</span>
        </div>
      </div>

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
          fontSize: '13px'
        }}>
          <AlertTriangle size={16} />
          <div>{errorMsg}</div>
        </div>
      )}

      {/* Step 1: Upload and Select Target */}
      {step === 1 && (
        <div className="card">
          <div className="card-title">1. Upload Source File</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '500px', marginTop: '10px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ color: '#f8fafc', fontWeight: 500, fontSize: '13px' }}>
                  Select Target CDM Schema Entity
                </label>
                <button className="btn btn-secondary" onClick={() => setShowCustomModal(true)} style={{ padding: '2px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Plus size={10} />
                  <span>Custom Type</span>
                </button>
              </div>
              <select 
                className="input-field"
                value={targetEntity}
                onChange={(e) => setTargetEntity(e.target.value)}
              >
                {TARGETS.map((t) => (
                  <option key={t.name} value={t.name}>{t.name}</option>
                ))}
              </select>
            </div>

             <div>
              <label style={{ display: 'block', color: '#f8fafc', fontWeight: 500, fontSize: '13px', marginBottom: '6px' }}>
                Spreadsheet File Format
              </label>
              <select 
                className="input-field"
                value={fileFormat}
                onChange={(e) => {
                  setFileFormat(e.target.value as any);
                  setFile(null);
                  setHeaders([]);
                  setMappings({});
                }}
              >
                <option value="csv">CSV Spreadsheet (.csv)</option>
                <option value="excel">Excel Sheet (.xlsx, .xls)</option>
                <option value="json">JSON Schema Document (.json)</option>
                <option value="xml">XML Document (.xml)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', color: '#f8fafc', fontWeight: 500, fontSize: '13px', marginBottom: '6px' }}>
                Select File ({fileFormat.toUpperCase()})
              </label>
              <input 
                type="file" 
                accept={
                  fileFormat === 'csv' ? '.csv' :
                  fileFormat === 'excel' ? '.xlsx, .xls' :
                  fileFormat === 'json' ? '.json' : '.xml'
                }
                onChange={handleFileChange}
                style={{ fontSize: '13px', color: '#94a3b8' }}
              />
            </div>

            <button 
              className="btn btn-primary" 
              style={{ alignSelf: 'flex-start', marginTop: '8px' }}
              disabled={!file}
              onClick={() => setStep(2)}
            >
              <span>Map Columns</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Mapping Grid */}
      {step === 2 && selectedTarget && (() => {
        return (
          <div className="card">
            <div className="card-title">2. Map File Columns to Database Schema</div>
            <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px' }}>
              Confirm AI suggested mapping suggestions or adjust mapping properties as needed.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '600px' }}>
              {selectedTarget.fields.map((field) => {
                const autoMatched = mappings[field] ? true : false;
                return (
                  <div key={field} style={{
                    display: 'grid',
                    gridTemplateColumns: '1.2fr 1fr',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 14px',
                    backgroundColor: 'rgba(255, 255, 255, 0.01)',
                    border: '1px solid #1e293b',
                    borderRadius: '6px'
                  }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{field}</span>
                        {autoMatched && (
                          <span style={{ fontSize: '9px', padding: '1px 6px', backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                            Auto suggest (High)
                          </span>
                        )}
                      </div>
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>Target CDM field</span>
                    </div>
                    <div>
                      <select 
                        className="input-field"
                        value={mappings[field] || ''}
                        onChange={(e) => handleFieldMapChange(field, e.target.value)}
                        style={{ padding: '6px 10px', fontSize: '12px' }}
                      >
                        <option value="">-- Leave Unmapped --</option>
                        {headers.map((header) => (
                          <option key={header} value={header}>{header}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                Back
              </button>
              <button className="btn btn-primary" onClick={executeIngest} disabled={ingesting}>
                {ingesting ? 'Triggering import...' : 'Submit Ingest Job'}
              </button>
            </div>
          </div>
        );
      })()}

      {/* Step 3: Success Screen */}
      {step === 3 && (
        <div className="card" style={{ textAlign: 'center', padding: '30px' }}>
          <CheckCircle2 size={40} style={{ color: '#10b981', marginBottom: '16px', display: 'inline-block' }} />
          <h3 style={{ color: '#f8fafc', margin: '0 0 6px 0', fontSize: '15px' }}>Ingest Pipeline Configured</h3>
          <p style={{ color: '#94a3b8', maxWidth: '500px', margin: '0 auto 20px auto', fontSize: '13px' }}>
            {successMsg}
          </p>
          <button className="btn btn-secondary" onClick={() => {
            setFile(null);
            setStep(1);
          }}>
            Import Another File
          </button>
        </div>
      )}

      {/* Ingested Tables catalog section */}
      <div className="card">
        <div className="card-title">Ingested CDM Tables Catalog</div>
        <p style={{ color: '#94a3b8', fontSize: '13px', marginBottom: '16px' }}>
          Browse target schema entities loaded into DuckDB database. Click preview to inspect raw records.
        </p>

        {tablesList.length === 0 ? (
          <div style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.01)', border: '1px solid #1e293b', borderRadius: '6px', fontSize: '12px', color: '#94a3b8', textAlign: 'center' }}>
            No mapped CDM tables found in current workspace context.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '12px' }}>
            {tablesList.map((tableName) => (
              <div key={tableName} style={{
                padding: '12px',
                backgroundColor: 'rgba(255, 255, 255, 0.01)',
                border: '1px solid #1e293b',
                borderRadius: '6px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#f8fafc', textTransform: 'capitalize', fontSize: '13px' }}>
                    {tableName.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'var(--mono)' }}>
                    {tableName}
                  </div>
                </div>
                <button 
                  className="btn btn-secondary" 
                  style={{ fontSize: '11px', padding: '4px 8px' }}
                  onClick={() => handlePreviewTable(tableName)}
                >
                  Preview
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Raw Table Preview panel */}
      {activePreview && (
        <div className="card" style={{ borderLeft: '3px solid #3b82f6' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div className="card-title" style={{ margin: 0, textTransform: 'capitalize', fontSize: '14px' }}>
              Preview: {activePreview.replace(/_/g, ' ')} (Top 5 Records)
            </div>
            <button 
              className="btn btn-secondary" 
              style={{ padding: '2px 8px', fontSize: '11px' }}
              onClick={() => setActivePreview(null)}
            >
              Close Preview
            </button>
          </div>

          {previewLoading ? (
            <div style={{ color: '#3b82f6', fontSize: '13px' }}>Loading table rows...</div>
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

      {/* Add Custom Type Modal Popup */}
      {showCustomModal && (
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
          <div className="card" style={{ width: '100%', maxWidth: '360px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div className="card-title">Define Custom Data Category</div>
            <form onSubmit={handleCreateCustomType} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', color: '#f8fafc', fontSize: '12px', marginBottom: '4px' }}>Category Name</label>
                <input 
                  type="text" 
                  className="input-field" 
                  placeholder="e.g. Supplier Invoices"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  required
                />
              </div>
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCustomModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Add Category</button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
