import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, Database, RefreshCw, Activity, TrendingUp, 
  CheckCircle, BarChart2, Eye, Table, ShieldCheck
} from 'lucide-react';
import ReactECharts from 'echarts-for-react';
import { apiFetch } from '../../config/api';

interface DynamicDashboardWorkspaceProps {
  onNavigateToSources: () => void;
  onNavigateToAssistant: () => void;
}

export const DynamicDashboardWorkspace: React.FC<DynamicDashboardWorkspaceProps> = ({
  onNavigateToSources,
  onNavigateToAssistant
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  
  // Table preview drawer state
  const [activePreviewTable, setActivePreviewTable] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewCols, setPreviewCols] = useState<string[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    fetchDashboardOverview();
  }, [selectedDataset]);

  const fetchDashboardOverview = async () => {
    setLoading(true);
    try {
      const url = selectedDataset 
        ? `/dashboards/overview?dataset=${encodeURIComponent(selectedDataset)}`
        : '/dashboards/overview';
      const res = await apiFetch(url);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (err) {
      console.error('Failed to fetch dynamic dashboard overview:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewTable = async (tableName: string) => {
    setActivePreviewTable(tableName);
    setPreviewLoading(true);
    try {
      const res = await apiFetch(`/data-sources/preview/${encodeURIComponent(tableName)}`);
      if (res.ok) {
        const tableMeta = await res.json();
        setPreviewCols(tableMeta.columns || []);
        setPreviewData(tableMeta.data || tableMeta.rows || []);
      }
    } catch (err) {
      console.error('Failed to fetch table preview:', err);
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="p-12 text-center text-slate-400 space-y-3 font-sans">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-cyan-400" />
        <p className="text-sm">Calculating dynamic business metrics from DuckDB storage...</p>
      </div>
    );
  }

  const summary = data?.summary || { total_datasets: 0, total_records: 0, average_quality_score: 100 };
  const datasets = data?.datasets || [];
  const kpis = data?.kpis || [];
  const visualizations = data?.visualizations || [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 text-slate-100 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent flex items-center gap-3">
            <LayoutDashboard className="w-8 h-8 text-emerald-400" /> Dynamic Business Intelligence Workspace
          </h1>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto">
          {datasets.length > 0 && (
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 text-xs px-3.5 py-2 rounded-xl focus:outline-none focus:border-cyan-500 font-medium shadow-sm"
            >
              <option value="">All Discovered Datasets ({summary.total_datasets})</option>
              {datasets.map((d: any) => (
                <option key={d.name} value={d.name}>{d.business_name} ({d.rows.toLocaleString()} rows)</option>
              ))}
            </select>
          )}

          <button
            onClick={fetchDashboardOverview}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Empty State */}
      {summary.total_datasets === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center space-y-5 max-w-lg mx-auto my-12 backdrop-blur-sm">
          <div className="w-16 h-16 rounded-2xl bg-emerald-950/60 border border-emerald-800/60 flex items-center justify-center mx-auto text-emerald-400 shadow-inner">
            <Activity className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-slate-100">Your Business Workspace is Ready</h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Connect local ERP systems or import CSV, Excel, or JSON datasets to automatically build dynamic KPIs, schema quality metrics, and visual analytics.
            </p>
          </div>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={onNavigateToSources}
              className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 font-bold text-xs rounded-xl shadow-lg hover:opacity-95 transition flex items-center gap-2"
            >
              <Database className="w-4 h-4" /> Connect Data Source
            </button>
            <button
              onClick={onNavigateToAssistant}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition"
            >
              Ask CLARIUS Assistant
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Summary KPIs Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur-sm">
              <div className="text-xs uppercase font-bold text-slate-400 tracking-wider">Connected Datasets</div>
              <div className="text-2xl font-bold text-slate-100 mt-2 font-mono">{summary.total_datasets}</div>
              <div className="text-[11px] text-emerald-400 mt-2 flex items-center gap-1.5 font-medium">
                <CheckCircle className="w-3.5 h-3.5" /> Registered in DuckDB
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur-sm">
              <div className="text-xs uppercase font-bold text-slate-400 tracking-wider">Total Records</div>
              <div className="text-2xl font-bold text-cyan-400 mt-2 font-mono">{summary.total_records.toLocaleString()}</div>
              <div className="text-[11px] text-slate-400 mt-2">Active business transaction rows</div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur-sm">
              <div className="text-xs uppercase font-bold text-slate-400 tracking-wider">Data Quality Score</div>
              <div className="text-2xl font-bold text-emerald-400 mt-2 font-mono">{summary.average_quality_score}%</div>
              <div className="text-[11px] text-emerald-400 mt-2 flex items-center gap-1.5 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" /> Completeness verified
              </div>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg backdrop-blur-sm">
              <div className="text-xs uppercase font-bold text-slate-400 tracking-wider">Storage & Security</div>
              <div className="text-xl font-bold text-slate-100 mt-2">DuckDB Local</div>
              <div className="text-[11px] text-slate-400 mt-2">100% Offline containment</div>
            </div>
          </div>

          {/* Dynamic Calculated KPIs Grid */}
          {kpis.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-cyan-400" /> Schema Calculated Business Metrics
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {kpis.map((kpi: any) => (
                  <div key={kpi.id} className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-lg hover:border-slate-700 transition flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{kpi.label}</span>
                        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-950 text-cyan-400 border border-slate-800">
                          {kpi.dataset}
                        </span>
                      </div>
                      <div className="text-2xl font-extrabold text-slate-100 mt-3 font-mono">
                        {kpi.value}
                      </div>
                    </div>
                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex justify-between items-center text-[11px] text-slate-500">
                      <span>Source: <code className="text-slate-400">{kpi.source_column}</code></span>
                      <span>{kpi.unit}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Dynamic Visual Analytics Grid */}
          {visualizations.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-emerald-400" /> Automated Visual Analytics
              </h2>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {visualizations.map((viz: any) => (
                  <div key={viz.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl">
                    <ReactECharts
                      option={viz.chart_options}
                      style={{ height: '320px', width: '100%' }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Discovered Datasets Table & Preview */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
              <Table className="w-5 h-5 text-blue-400" /> Discovered Datasets & Schema Health
            </h2>

            <div className="border border-slate-800 rounded-2xl overflow-hidden bg-slate-900/70 shadow-lg">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                    <th className="p-4">Dataset Name</th>
                    <th className="p-4">Records</th>
                    <th className="p-4">Columns</th>
                    <th className="p-4">Quality Score</th>
                    <th className="p-4">Health</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {datasets.map((d: any) => (
                    <tr key={d.name} className="hover:bg-slate-800/40 transition">
                      <td className="p-4 font-bold text-slate-100 flex items-center gap-2">
                        <Database className="w-4 h-4 text-cyan-400" /> {d.business_name}
                      </td>
                      <td className="p-4 font-mono text-slate-200 font-semibold">{d.rows.toLocaleString()}</td>
                      <td className="p-4 font-mono text-slate-400">{d.columns}</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                          {d.quality_score}%
                        </span>
                      </td>
                      <td className="p-4 text-emerald-400 font-medium">{d.health}</td>
                      <td className="p-4 text-right">
                        <button
                          onClick={() => handlePreviewTable(d.name)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 transition flex items-center gap-1.5 ml-auto"
                        >
                          <Eye className="w-3.5 h-3.5 text-cyan-400" /> View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Table Preview Drawer */}
          {activePreviewTable && (
            <div className="bg-slate-900/90 border border-blue-900/60 rounded-2xl p-6 shadow-2xl space-y-4">
              <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Table className="w-4 h-4 text-blue-400" /> View Dataset: <span className="text-cyan-400 font-mono">{activePreviewTable}</span>
                </h3>
                <button
                  onClick={() => setActivePreviewTable(null)}
                  className="text-xs text-slate-400 hover:text-slate-200 px-2 py-1 bg-slate-800 rounded-lg"
                >
                  Close View
                </button>
              </div>

              {previewLoading ? (
                <div className="py-6 text-center text-xs text-cyan-400 animate-pulse">Loading preview rows...</div>
              ) : previewData.length === 0 ? (
                <div className="py-6 text-center text-xs text-slate-500">No records stored in this table.</div>
              ) : (
                <div className="overflow-x-auto border border-slate-800 rounded-xl">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        {previewCols.map((col) => (
                          <th key={col} className="p-3 font-mono">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 bg-slate-950/40">
                      {previewData.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40">
                          {previewCols.map((col) => (
                            <td key={col} className="p-3 font-mono text-slate-300 truncate max-w-[200px]">
                              {String(row[col] ?? '')}
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
        </div>
      )}
    </div>
  );
};
