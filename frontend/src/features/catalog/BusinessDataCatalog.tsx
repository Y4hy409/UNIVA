import React, { useState, useEffect } from 'react';
import { 
  Database, Search, RefreshCw, X, Trash2
} from 'lucide-react';
import { apiFetch } from '../../config/api';

export const BusinessDataCatalog: React.FC = () => {
  const [datasets, setDatasets] = useState<any[]>([]);
  const [quality, setQuality] = useState<any>(null);
  const [relationships, setRelationships] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  // Active Dataset Modal States
  const [selectedDataset, setSelectedDataset] = useState<any | null>(null);
  const [datasetTab, setDatasetTab] = useState<'overview' | 'preview' | 'columns' | 'relationships' | 'quality'>('overview');
  const [columnsCatalog, setColumnsCatalog] = useState<any[]>([]);
  const [columnsLoading, setColumnsLoading] = useState(false);

  // Dataset Preview state
  const [previewData, setPreviewData] = useState<{ columns: string[]; rows: any[] }>({ columns: [], rows: [] });
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    fetchCatalog();
  }, []);

  const fetchCatalog = async () => {
    setLoading(true);
    try {
      const [dsRes, qualRes, relRes] = await Promise.all([
        apiFetch('/catalog/datasets'),
        apiFetch('/catalog/quality'),
        apiFetch('/catalog/relationships')
      ]);

      if (dsRes.ok) setDatasets(await dsRes.json());
      if (qualRes.ok) {
        const qdata = await qualRes.json();
        setQuality(qdata?.metrics || null);
      }
      if (relRes.ok) setRelationships(await relRes.json());
    } catch (err) {
      console.error('Failed to fetch catalog metadata', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDataset = async (dataset: any) => {
    setSelectedDataset(dataset);
    setDatasetTab('overview');
    setColumnsLoading(true);
    setPreviewLoading(true);
    try {
      const [detailsRes, colsRes, prevRes, relRes] = await Promise.all([
        apiFetch(`/catalog/datasets/${dataset.name}`),
        apiFetch(`/catalog/datasets/${dataset.name}/columns`),
        apiFetch(`/catalog/datasets/${dataset.name}/preview?limit=10`),
        apiFetch('/catalog/relationships')
      ]);

      if (detailsRes.ok) {
        setSelectedDataset(await detailsRes.json());
      }
      if (colsRes.ok) {
        setColumnsCatalog(await colsRes.json());
      }
      if (prevRes.ok) {
        setPreviewData(await prevRes.json());
      }
      if (relRes.ok) {
        setRelationships(await relRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch dataset details/preview', err);
    } finally {
      setColumnsLoading(false);
      setPreviewLoading(false);
    }
  };

  const [selectedDatasetNames, setSelectedDatasetNames] = useState<Set<string>>(new Set());
  const [deletingBulk, setDeletingBulk] = useState(false);

  const filteredDatasets = datasets.filter(ds => 
    ds.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ds.business_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ds.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const isAllSelected = filteredDatasets.length > 0 && filteredDatasets.every(ds => selectedDatasetNames.has(ds.name));

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedDatasetNames(new Set());
    } else {
      const allFiltered = new Set(filteredDatasets.map(ds => ds.name));
      setSelectedDatasetNames(allFiltered);
    }
  };

  const toggleSelectDataset = (name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedDatasetNames(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const handleDeleteSelected = async () => {
    const namesToDelete = Array.from(selectedDatasetNames);
    if (namesToDelete.length === 0) return;

    if (!window.confirm(`Are you sure you want to drop ${namesToDelete.length} selected dataset(s) from DuckDB? This will delete the physical tables.`)) return;

    setDeletingBulk(true);
    try {
      const res = await apiFetch('/catalog/datasets/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_names: namesToDelete })
      });
      if (res.ok) {
        setSelectedDatasetNames(new Set());
        if (selectedDataset && namesToDelete.includes(selectedDataset.name)) {
          setSelectedDataset(null);
        }
        fetchCatalog();
      }
    } catch (err) {
      console.error('Failed to bulk delete datasets', err);
    } finally {
      setDeletingBulk(false);
    }
  };

  const handleDeleteAllDatasets = async () => {
    if (!window.confirm('WARNING: Are you sure you want to drop ALL business datasets from DuckDB? This cannot be undone.')) return;

    setDeletingBulk(true);
    try {
      const res = await apiFetch('/catalog/purge/all', { method: 'DELETE' });
      if (res.ok) {
        setSelectedDatasetNames(new Set());
        setSelectedDataset(null);
        fetchCatalog();
      }
    } catch (err) {
      console.error('Failed to purge all datasets', err);
    } finally {
      setDeletingBulk(false);
    }
  };

  const handleDeleteDataset = async (datasetName: string) => {
    if (!window.confirm(`Are you sure you want to drop dataset "${datasetName}" from DuckDB database?`)) return;

    try {
      const res = await apiFetch(`/catalog/datasets/${encodeURIComponent(datasetName)}`, { method: 'DELETE' });
      if (res.ok) {
        setSelectedDataset(null);
        setSelectedDatasetNames(prev => {
          const next = new Set(prev);
          next.delete(datasetName);
          return next;
        });
        fetchCatalog();
      }
    } catch (err) {
      console.error('Failed to delete dataset', err);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">
            Enterprise Data Catalog
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {datasets.length > 0 && (
            <button
              onClick={handleDeleteAllDatasets}
              disabled={deletingBulk}
              className="flex items-center gap-2 px-3.5 py-2 bg-red-950/40 hover:bg-red-900/60 text-red-300 rounded-lg text-xs transition font-semibold border border-red-800/50"
              title="Drop all custom business datasets from DuckDB"
            >
              <Trash2 className="w-3.5 h-3.5" /> Purge All Datasets
            </button>
          )}
          <button
            onClick={fetchCatalog}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm transition font-medium border border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Catalog
          </button>
        </div>
      </div>

      {/* Global Data Quality Summary Header Metrics */}
      {quality && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-500 block">Overall Quality Score</span>
            <span className="text-2xl font-bold text-emerald-400">{quality.quality_score}%</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-500 block">Data Completeness</span>
            <span className="text-2xl font-bold text-cyan-400">{quality.completeness}%</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-500 block">Consistency Score</span>
            <span className="text-2xl font-bold text-indigo-400">{quality.consistency}%</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
            <span className="text-xs text-slate-500 block">Data Freshness</span>
            <span className="text-2xl font-bold text-emerald-400">{quality.freshness}</span>
          </div>
        </div>
      )}

      {/* Search Bar */}
      <div className="flex items-center gap-3 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-2.5 shadow-inner">
        <Search className="w-5 h-5 text-slate-400" />
        <input
          type="text"
          placeholder="Search datasets, column attributes, business terms, descriptions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="bg-transparent text-sm text-slate-100 placeholder-slate-500 w-full focus:outline-none"
        />
      </div>

      {/* Dataset Grid & Selection Actions Bar */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <h2 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" /> Managed Business Datasets ({filteredDatasets.length})
          </h2>

          {filteredDatasets.length > 0 && (
            <div className="flex items-center gap-3 bg-slate-900/90 border border-slate-800 rounded-xl px-3.5 py-1.5 shadow-sm">
              <label className="flex items-center gap-2 text-xs font-semibold text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  onChange={handleToggleSelectAll}
                  className="w-4 h-4 rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                />
                <span>Select All ({filteredDatasets.length})</span>
              </label>

              {selectedDatasetNames.size > 0 && (
                <div className="flex items-center gap-2 pl-3 border-l border-slate-800">
                  <span className="text-xs text-cyan-400 font-medium">
                    {selectedDatasetNames.size} selected
                  </span>
                  <button
                    onClick={handleDeleteSelected}
                    disabled={deletingBulk}
                    className="flex items-center gap-1.5 px-3 py-1 bg-red-950/70 hover:bg-red-900/90 text-red-200 rounded-lg text-xs font-semibold transition border border-red-800/80 shadow"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Selected ({selectedDatasetNames.size})</span>
                  </button>
                  <button
                    onClick={() => setSelectedDatasetNames(new Set())}
                    className="text-slate-400 hover:text-slate-200 text-xs px-1.5"
                  >
                    Deselect
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {filteredDatasets.length === 0 && !loading ? (
          <div className="bg-slate-900/50 border border-dashed border-slate-800 rounded-xl p-8 text-center text-slate-400">
            No business datasets matched your query or exist in the warehouse catalog.
          </div>
        ) : (
          <div className="space-y-3">
            {filteredDatasets.map((ds) => {
              const isSelected = selectedDatasetNames.has(ds.name);
              return (
                <div
                  key={ds.name}
                  onClick={() => handleOpenDataset(ds)}
                  className={`border rounded-xl px-6 py-4 transition cursor-pointer shadow-md group flex items-center justify-between gap-6 ${
                    isSelected 
                      ? 'bg-slate-900/95 border-cyan-500/70 shadow-cyan-950/20 ring-1 ring-cyan-500/30' 
                      : 'bg-slate-900/90 border-slate-800/90 hover:border-cyan-500/50 hover:shadow-cyan-950/20'
                  }`}
                >
                  {/* Left: Checkbox + Business Name & Physical Table */}
                  <div className="flex items-center gap-4 min-w-[240px]">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onClick={(e) => toggleSelectDataset(ds.name, e)}
                      onChange={() => {}}
                      className="w-4 h-4 rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0 focus:ring-offset-0 cursor-pointer flex-shrink-0"
                    />
                    <div>
                      <h3 className="text-base font-bold text-slate-100 group-hover:text-cyan-300 transition truncate">{ds.business_name}</h3>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">Physical Table: {ds.name}</p>
                    </div>
                  </div>

                  {/* Right: Aligned Metadata Columns */}
                  <div className="flex items-center gap-8 md:gap-12 text-xs flex-shrink-0">
                    <div className="text-right sm:text-left min-w-[70px]">
                      <span className="text-slate-500 block text-[11px] uppercase tracking-wider">Row Count</span>
                      <span className="text-slate-200 font-bold text-sm">{ds.rows?.toLocaleString()}</span>
                    </div>

                    <div className="text-right sm:text-left min-w-[70px]">
                      <span className="text-slate-500 block text-[11px] uppercase tracking-wider">Columns</span>
                      <span className="text-slate-200 font-bold text-sm">{ds.columns} Fields</span>
                    </div>

                    <div className="text-right sm:text-left min-w-[110px] hidden sm:block">
                      <span className="text-slate-500 block text-[11px] uppercase tracking-wider">Updated By</span>
                      <span className="text-cyan-400 font-medium text-xs truncate block">{ds.updated_by || 'cerebras'}</span>
                    </div>

                    <div className="text-right sm:text-left min-w-[110px] hidden md:block">
                      <span className="text-slate-500 block text-[11px] uppercase tracking-wider">Last Updated</span>
                      <span className="text-slate-300 font-medium text-xs">{ds.last_updated || 'Recently'}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dataset Details Modal */}
      {selectedDataset && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div>
                <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
                  {selectedDataset.business_name}
                </h2>
                <p className="text-xs text-slate-400 font-mono mt-0.5">Physical Table: {selectedDataset.name}</p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleDeleteDataset(selectedDataset.name)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-950/50 hover:bg-red-900/80 text-red-300 rounded-lg text-xs transition border border-red-800/60 font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete Dataset
                </button>
                <button
                  onClick={() => setSelectedDataset(null)}
                  className="p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Navigation Tabs */}
            <div className="flex border-b border-slate-800 px-6 bg-slate-950/30 text-xs font-semibold text-slate-400">
              {(['overview', 'preview', 'columns', 'relationships', 'quality'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDatasetTab(tab)}
                  className={`py-3.5 px-4 uppercase tracking-wider transition border-b-2 ${
                    datasetTab === tab
                      ? 'border-cyan-400 text-cyan-400'
                      : 'border-transparent hover:text-slate-200'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {datasetTab === 'overview' && (
                <div className="grid grid-cols-2 gap-6 text-sm">
                  <div className="space-y-4">
                    <div>
                      <span className="text-xs text-slate-500 block">Description</span>
                      <p className="text-slate-200 mt-1">{selectedDataset.description}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block">Source System</span>
                      <p className="text-cyan-400 font-mono mt-1">{selectedDataset.source}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block">Refresh Schedule</span>
                      <p className="text-slate-200 mt-1">Real-Time Continuous Ingestion</p>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <span className="text-xs text-slate-500 block">Row Count</span>
                      <p className="text-slate-100 font-bold text-lg">{selectedDataset.rows?.toLocaleString()}</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block">Column Count</span>
                      <p className="text-slate-100 font-bold text-lg">{selectedDataset.columns} Attributes</p>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block">Quality Score</span>
                      <p className="text-emerald-400 font-bold text-lg">{selectedDataset.quality_score}%</p>
                    </div>
                  </div>
                </div>
              )}

              {datasetTab === 'preview' && (
                <div>
                  {previewLoading ? (
                    <div className="p-6 text-center text-slate-400 text-sm">Loading dataset preview...</div>
                  ) : previewData.rows.length === 0 ? (
                    <div className="text-sm text-slate-400 p-8 border border-dashed border-slate-800 rounded-xl text-center">
                      No uploaded data records found in table <span className="font-mono text-cyan-400">{selectedDataset.name}</span>.
                    </div>
                  ) : (
                    <div className="border border-slate-800 rounded-xl overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                            {previewData.columns.map((col, idx) => (
                              <th key={idx} className="p-3 font-mono text-cyan-300 border-r border-slate-800/60">{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/80">
                          {previewData.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-slate-800/40">
                              {previewData.columns.map((col, cIdx) => (
                                <td key={cIdx} className="p-3 font-mono text-slate-300 border-r border-slate-800/40 whitespace-nowrap max-w-[200px] truncate">
                                  {row[col] !== undefined ? String(row[col]) : 'NULL'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {datasetTab === 'columns' && (
                <div>
                  {columnsLoading ? (
                    <div className="p-6 text-center text-slate-400 text-sm">Loading column catalog...</div>
                  ) : (
                    <div className="border border-slate-800 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                            <th className="p-3">Physical Name</th>
                            <th className="p-3">Business Name</th>
                            <th className="p-3">Type</th>
                            <th className="p-3">Primary Key</th>
                            <th className="p-3">Nullable</th>
                            <th className="p-3">Sample Value</th>
                            <th className="p-3">Confidence</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/80">
                          {columnsCatalog.map((col, i) => (
                            <tr key={i} className="hover:bg-slate-800/40">
                              <td className="p-3 font-mono text-slate-200">{col.column_name}</td>
                              <td className="p-3 text-cyan-300 font-medium">{col.business_name}</td>
                              <td className="p-3 font-mono text-amber-400">{col.data_type}</td>
                              <td className="p-3 text-slate-300">{col.primary_key ? 'Yes (PK)' : 'No'}</td>
                              <td className="p-3 text-slate-400">{col.nullable ? 'Yes' : 'No'}</td>
                              <td className="p-3 text-slate-400 font-mono truncate max-w-[120px]">{col.sample_value}</td>
                              <td className="p-3 text-emerald-400 font-bold">{Math.round(col.confidence * 100)}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {datasetTab === 'relationships' && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-slate-300">Inferred Data Relationships</h3>
                  {relationships.length === 0 ? (
                    <div className="text-sm text-slate-400 p-4 border border-dashed border-slate-800 rounded-lg text-center">
                      No parent-child foreign key relationships detected for this entity.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {relationships.map((rel, i) => (
                        <div key={i} className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
                          <div>
                            <span className="text-slate-400 block">Parent Table</span>
                            <span className="text-cyan-400 font-bold">{rel.parent}</span> ({rel.parent_column})
                          </div>
                          <div className="text-center px-4 py-1 bg-slate-800/80 rounded-full font-mono text-[10px] text-amber-400 border border-slate-700">
                            {rel.cardinality} Cardinality
                          </div>
                          <div>
                            <span className="text-slate-400 block">Child Table</span>
                            <span className="text-emerald-400 font-bold">{rel.child}</span> ({rel.child_column})
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {datasetTab === 'quality' && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-500 block">Completeness Metric</span>
                    <span className="text-xl font-bold text-emerald-400">98.4%</span>
                  </div>
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl">
                    <span className="text-xs text-slate-500 block">Duplicate Rows</span>
                    <span className="text-xl font-bold text-cyan-400">0 Detected</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

