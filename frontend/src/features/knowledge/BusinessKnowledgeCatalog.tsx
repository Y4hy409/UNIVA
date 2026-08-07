import React, { useState, useEffect } from 'react';
import { 
  BookOpen, Search, Folder, FileText, RefreshCw, 
  Sparkles, Eye, X
} from 'lucide-react';
import { apiFetch } from '../../config/api';

export const BusinessKnowledgeCatalog: React.FC = () => {
  const [collections, setCollections] = useState<any[]>([]);
  const [explorerTree, setExplorerTree] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);

  // Selected document modal state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docDetails, setDocDetails] = useState<any | null>(null);
  const [docTab, setDocTab] = useState<'preview' | 'ocr' | 'ai_metadata' | 'chunks'>('ai_metadata');
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    fetchKnowledgeData();
  }, []);

  const fetchKnowledgeData = async () => {
    setLoading(true);
    try {
      const [colRes, treeRes, docsRes] = await Promise.all([
        apiFetch('/documents/collections'),
        apiFetch('/documents/explorer'),
        apiFetch('/documents')
      ]);

      if (colRes.ok) setCollections(await colRes.json());
      if (treeRes.ok) setExplorerTree(await treeRes.json());
      if (docsRes.ok) setDocuments(await docsRes.json());
    } catch (err) {
      console.error('Failed to fetch knowledge catalog metadata', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    try {
      const res = await apiFetch(`/documents/query?q=${encodeURIComponent(searchQuery)}&limit=5`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.results) {
          setSearchResults(data.results);
        }
      }
    } catch (err) {
      console.error('Search failed', err);
    }
  };

  const handleOpenDocDetails = async (docId: string) => {
    setSelectedDocId(docId);
    setDetailsLoading(true);
    try {
      const res = await apiFetch(`/documents/${docId}/details`);
      if (res.ok) {
        setDocDetails(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch document details', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-amber-400 to-emerald-400 bg-clip-text text-transparent">
            Enterprise Knowledge Catalog
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Offline RAG vector store, OCR entity extraction, and knowledge collection indexing.
          </p>
        </div>
        <button
          onClick={fetchKnowledgeData}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm transition font-medium border border-slate-700"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh Knowledge
        </button>
      </div>

      {/* Semantic + Keyword Hybrid Search */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex items-center gap-3 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-3 shadow-lg">
          <Search className="w-5 h-5 text-amber-400" />
          <input
            type="text"
            placeholder="Search document knowledge, extracted entities, policies, invoices, SOPs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent text-sm text-slate-100 placeholder-slate-500 w-full focus:outline-none"
          />
          <button
            type="submit"
            className="px-5 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg text-xs transition"
          >
            Hybrid Search
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-3">
            <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider">Semantic Match Results</h3>
            <div className="divide-y divide-slate-800">
              {searchResults.map((res, i) => (
                <div key={i} className="py-3 space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-semibold text-slate-200">{res.title}</span>
                    <span className="text-emerald-400 font-mono text-[10px]">Distance: {res.distance?.toFixed(3)}</span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">{res.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </form>

      {/* Knowledge Collections Cards */}
      <div>
        <h2 className="text-xl font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-amber-400" /> Knowledge Collections ({collections.length})
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {collections.map((col) => (
            <div
              key={col.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-amber-500/50 rounded-xl p-5 transition shadow-lg backdrop-blur-sm"
            >
              <div className="flex justify-between items-start">
                <div className="p-3 bg-amber-950/60 text-amber-400 rounded-lg border border-amber-800/40">
                  <BookOpen className="w-6 h-6" />
                </div>
                <span className="px-2.5 py-1 text-xs rounded-full font-bold bg-amber-950 text-amber-400 border border-amber-800">
                  {col.count} Documents
                </span>
              </div>

              <div className="mt-4">
                <h3 className="text-lg font-bold text-slate-100 truncate">{col.name}</h3>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2">{col.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Document Explorer (Tree Folder Browser) & Recent Documents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Explorer Tree */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <Folder className="w-5 h-5 text-emerald-400" /> Folder Explorer
          </h3>

          <div className="space-y-3 text-xs">
            {explorerTree.map((folder, i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-center justify-between p-2 bg-slate-950/60 rounded-lg text-slate-300 font-semibold border border-slate-800/60">
                  <span className="flex items-center gap-2">
                    <Folder className="w-4 h-4 text-amber-400" /> {folder.name}
                  </span>
                  <span className="text-slate-500 text-[10px]">{folder.count} items</span>
                </div>
                {folder.items && folder.items.length > 0 && (
                  <div className="pl-4 space-y-1">
                    {folder.items.map((doc: any) => (
                      <div
                        key={doc.id}
                        onClick={() => handleOpenDocDetails(doc.id)}
                        className="flex items-center justify-between p-1.5 hover:bg-slate-800/60 rounded text-slate-400 hover:text-slate-200 cursor-pointer transition"
                      >
                        <span className="flex items-center gap-2 truncate">
                          <FileText className="w-3.5 h-3.5 text-cyan-400" /> {doc.name}
                        </span>
                        <Eye className="w-3.5 h-3.5 text-slate-500 hover:text-amber-400" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Document Metadata List Table */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
            <FileText className="w-5 h-5 text-cyan-400" /> Indexed Knowledge Documents ({documents.length})
          </h3>

          <div className="overflow-x-auto border border-slate-800 rounded-xl">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950 text-slate-400 border-b border-slate-800">
                  <th className="p-3">Title</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Indexed Status</th>
                  <th className="p-3">Created</th>
                  <th className="p-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/40 transition">
                    <td className="p-3 font-semibold text-slate-200 truncate max-w-[180px]">{doc.title}</td>
                    <td className="p-3 font-mono text-amber-400">{doc.doc_type?.toUpperCase()}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                        Vectorized
                      </span>
                    </td>
                    <td className="p-3 text-slate-400 font-mono text-[11px]">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3">
                      <button
                        onClick={() => handleOpenDocDetails(doc.id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-200 rounded transition text-[11px] font-medium"
                      >
                        Inspect Metadata
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Document Details & AI Extracted Metadata Modal */}
      {selectedDocId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
            {/* Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
              <div>
                <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-3">
                  <FileText className="w-6 h-6 text-amber-400" /> {docDetails?.name || 'Document Inspector'}
                </h2>
                <p className="text-xs text-slate-400 font-mono mt-0.5">Doc ID: {selectedDocId}</p>
              </div>
              <button
                onClick={() => setSelectedDocId(null)}
                className="p-2 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Tabs */}
            <div className="flex border-b border-slate-800 px-6 bg-slate-950/30 text-xs font-semibold text-slate-400">
              {(['ai_metadata', 'preview', 'ocr'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDocTab(tab)}
                  className={`py-3.5 px-4 uppercase tracking-wider transition border-b-2 ${
                    docTab === tab
                      ? 'border-amber-400 text-amber-400'
                      : 'border-transparent hover:text-slate-200'
                  }`}
                >
                  {tab === 'ai_metadata' ? 'AI Extracted Metadata' : tab}
                </button>
              ))}
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {detailsLoading ? (
                <div className="p-8 text-center text-slate-400 text-sm">Loading document intelligence metadata...</div>
              ) : (
                <>
                  {docTab === 'ai_metadata' && docDetails?.ai_extracted && (
                    <div className="space-y-6">
                      <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                        <span className="text-xs text-amber-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                          <Sparkles className="w-4 h-4" /> AI Document Executive Summary
                        </span>
                        <p className="text-sm text-slate-200">{docDetails.ai_extracted.summary}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                          <span className="text-slate-500 font-semibold block">Extracted Entities & People</span>
                          <div className="flex flex-wrap gap-1.5">
                            {docDetails.ai_extracted.people?.map((p: string, i: number) => (
                              <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-slate-200">{p}</span>
                            ))}
                          </div>
                        </div>

                        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                          <span className="text-slate-500 font-semibold block">Organizations & Companies</span>
                          <div className="flex flex-wrap gap-1.5">
                            {docDetails.ai_extracted.companies?.map((c: string, i: number) => (
                              <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-cyan-400">{c}</span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4 text-xs">
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
                          <span className="text-slate-500 block">Invoice Reference</span>
                          <span className="text-amber-400 font-mono font-bold">{docDetails.ai_extracted.invoice_number}</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
                          <span className="text-slate-500 block">Purchase Order</span>
                          <span className="text-cyan-400 font-mono font-bold">{docDetails.ai_extracted.purchase_order}</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
                          <span className="text-slate-500 block">Extraction Confidence</span>
                          <span className="text-emerald-400 font-bold">{Math.round(docDetails.ai_extracted.confidence * 100)}%</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {docTab === 'preview' && (
                    <div className="p-8 text-center bg-slate-950 border border-slate-800 rounded-xl text-slate-400 text-xs">
                      PDF Document Previewer rendered dynamically from vector store persistence.
                    </div>
                  )}

                  {docTab === 'ocr' && (
                    <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-slate-300 space-y-2">
                      <span className="text-emerald-400 block">// Raw OCR Text Buffer</span>
                      <p>INVOICE #INV-2026-0891 - UNIVA Platform Licensing and Enterprise Support Contract...</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
