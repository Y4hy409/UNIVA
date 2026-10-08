import React, { useState } from 'react';
import { Database, RefreshCw } from 'lucide-react';

export const ErpConnectorsWorkspace: React.FC = () => {
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

  // ERP Connection Modal state
  const [activeErpModal, setActiveErpModal] = useState<string | null>(null);
  const [erpFormData, setErpFormData] = useState<Record<string, string>>({});
  const [connectingErp, setConnectingErp] = useState(false);

  const erpPlatforms = ['TallyPrime', 'Odoo ERP', 'ERPNext', 'BUSY', 'Marg ERP', 'Zoho Books'];

  const handleSyncNow = () => {
    setSyncStatus('syncing');
    setTimeout(() => {
      setSyncStatus('success');
      setSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      setTimeout(() => setSyncStatus('idle'), 3000);
    }, 1500);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Connected Enterprise Sources & ERP Connectors
          </h1>
        </div>
      </div>

      {/* ERP Platform Status Cards Grid */}
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
                    onClick={() => {
                      setActiveErpModal(erpKey);
                      setErpFormData({});
                    }}
                    className="px-4 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded transition"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ERP Connection Parameters Modal */}
      {activeErpModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex justify-between items-center border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-100">{activeErpModal} Connection Parameters</h3>
                <p className="text-xs text-slate-400 mt-0.5">Enter connection parameters for local offline sync</p>
              </div>
              <button
                onClick={() => setActiveErpModal(null)}
                className="text-slate-400 hover:text-slate-200 text-lg px-2"
              >
                ✕
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setConnectingErp(true);
                setTimeout(() => {
                  setConnectedErps(prev => ({ ...prev, [activeErpModal]: true }));
                  setConnectingErp(false);
                  setActiveErpModal(null);
                }, 800);
              }}
              className="space-y-4 text-xs"
            >
              <div>
                <label className="block text-slate-300 font-medium mb-1">Server URL Endpoint / Host</label>
                <input
                  type="text"
                  required
                  placeholder="http://localhost:9000"
                  value={erpFormData.url || 'http://localhost:9000'}
                  onChange={(e) => setErpFormData({ ...erpFormData, url: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Company Name / Database Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Primary Company"
                  value={erpFormData.company || ''}
                  onChange={(e) => setErpFormData({ ...erpFormData, company: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setActiveErpModal(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={connectingErp}
                  className="px-5 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg transition"
                >
                  {connectingErp ? 'Saving Connection...' : 'Save & Connect'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
