import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Search, FileText, RefreshCw, 
  Sparkles, X, Trash2, ShieldAlert, UploadCloud,
  CheckCircle2, Users, FileSpreadsheet, Shield, Compass,
  Plus, ArrowUpDown, AlertCircle, FileCheck
} from 'lucide-react';
import { apiFetch } from '../../config/api';

interface CollectionItem {
  id: string;
  name: string;
  count: number;
  icon: string;
  color?: string;
  description: string;
}

interface DocumentItem {
  id: string;
  title: string;
  doc_type: string;
  category_name?: string;
  metadata?: any;
  created_at: string;
}

export const BusinessKnowledgeCatalog: React.FC = () => {
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Filter & Search states
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [sortBy, setSortBy] = useState<'newest' | 'oldest' | 'title_asc' | 'title_desc'>('newest');

  // Selected document modal state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docDetails, setDocDetails] = useState<any | null>(null);
  const [docTab, setDocTab] = useState<'ai_metadata' | 'preview' | 'ocr'>('ai_metadata');
  const [detailsLoading, setDetailsLoading] = useState(false);

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDocType, setUploadDocType] = useState('auto');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    fetchKnowledgeData();
  }, []);

  const fetchKnowledgeData = async () => {
    setLoading(true);
    try {
      const [colRes, docsRes] = await Promise.all([
        apiFetch('/documents/collections'),
        apiFetch('/documents')
      ]);

      if (colRes.ok) setCollections(await colRes.json());
      if (docsRes.ok) setDocuments(await docsRes.json());
    } catch (err) {
      console.error('Failed to fetch knowledge catalog metadata', err);
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (text: string, type: 'success' | 'error' | 'info' = 'success') => {
    setActionMessage({ text, type });
    setTimeout(() => setActionMessage(null), 5000);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const res = await apiFetch(`/documents/query?q=${encodeURIComponent(searchQuery)}&limit=6`);
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

  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [deletingBulk, setDeletingBulk] = useState(false);

  const isAllDocsSelected = filteredDocuments.length > 0 && filteredDocuments.every(doc => selectedDocIds.has(doc.id));

  const handleToggleSelectAllDocs = () => {
    if (isAllDocsSelected) {
      setSelectedDocIds(new Set());
    } else {
      const allFiltered = new Set(filteredDocuments.map(doc => doc.id));
      setSelectedDocIds(allFiltered);
    }
  };

  const toggleSelectDoc = (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedDocIds(prev => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  };

  const handleDeleteSelectedDocs = async () => {
    const idsToDelete = Array.from(selectedDocIds);
    if (idsToDelete.length === 0) return;

    if (!window.confirm(`Are you sure you want to delete ${idsToDelete.length} selected document(s) and remove their vector embeddings from ChromaDB?`)) return;

    setDeletingBulk(true);
    try {
      const res = await apiFetch('/documents/bulk-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_ids: idsToDelete })
      });
      if (res.ok) {
        showNotification(`Deleted ${idsToDelete.length} document(s) successfully.`, 'info');
        setSelectedDocIds(new Set());
        if (selectedDocId && idsToDelete.includes(selectedDocId)) {
          setSelectedDocId(null);
        }
        fetchKnowledgeData();
      }
    } catch (err) {
      console.error('Failed to bulk delete documents', err);
      showNotification('Failed to bulk delete documents.', 'error');
    } finally {
      setDeletingBulk(false);
    }
  };

  const handlePurgeAllDocuments = async () => {
    if (!window.confirm('WARNING: Are you sure you want to delete ALL business documents and wipe all vector embeddings from ChromaDB? This cannot be undone.')) return;

    setDeletingBulk(true);
    try {
      const res = await apiFetch('/documents/purge/all', { method: 'DELETE' });
      if (res.ok) {
        showNotification('All documents and vector embeddings purged.', 'info');
        setSelectedDocIds(new Set());
        setSelectedDocId(null);
        fetchKnowledgeData();
      }
    } catch (err) {
      console.error('Failed to purge all documents', err);
      showNotification('Failed to purge all documents.', 'error');
    } finally {
      setDeletingBulk(false);
    }
  };

  const handleDeleteDocument = async (docId: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete document "${title}"?`)) return;

    try {
      const res = await apiFetch(`/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        showNotification(`Document "${title}" deleted successfully.`, 'info');
        if (selectedDocId === docId) setSelectedDocId(null);
        setSelectedDocIds(prev => {
          const next = new Set(prev);
          next.delete(docId);
          return next;
        });
        fetchKnowledgeData();
      }
    } catch (err) {
      console.error('Failed to delete document', err);
      showNotification('Failed to delete document.', 'error');
    }
  };

  const handlePurgeDuplicates = async () => {
    if (!window.confirm('Purge duplicate test documents and sample records?')) return;

    try {
      const res = await apiFetch('/documents/purge/duplicates', { method: 'DELETE' });
      if (res.ok) {
        const data = await res.json();
        showNotification(data.message || 'Duplicate test documents purged.');
        fetchKnowledgeData();
      }
    } catch (err) {
      console.error('Failed to purge duplicates', err);
    }
  };

  // Upload handlers
  const handleFileSelect = (file: File) => {
    setUploadFile(file);
    if (!uploadTitle) {
      // Auto-populate title from clean filename
      const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      setUploadTitle(cleanName);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      alert("Please select a document file to upload.");
      return;
    }

    setUploading(true);
    setUploadProgress("Extracting text and running OCR pipeline...");

    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("doc_type", uploadDocType);
    if (uploadTitle.trim()) {
      formData.append("title", uploadTitle.trim());
    }

    try {
      setTimeout(() => {
        if (uploading) setUploadProgress("Analyzing semantics & auto-categorizing document...");
      }, 800);

      const res = await apiFetch('/documents/upload', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(errData.detail || "Document upload failed");
      }

      const result = await res.json();
      const detectedInfo = result.auto_detected 
        ? `✨ Auto-detected category: "${result.category_name}"` 
        : `Categorized into: "${result.category_name}"`;

      showNotification(`"${result.title}" uploaded & indexed successfully! ${detectedInfo}`, 'success');

      // Reset form & close modal
      setUploadFile(null);
      setUploadTitle('');
      setUploadDocType('auto');
      setIsUploadModalOpen(false);
      fetchKnowledgeData();
    } catch (err: any) {
      console.error('Document upload error:', err);
      showNotification(err.message || 'Failed to upload and index document.', 'error');
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  };

  const openUploadWithCategory = (catId: string) => {
    setUploadDocType(catId);
    setIsUploadModalOpen(true);
  };

  // Helper icons mapper
  const getCategoryIcon = (iconName: string) => {
    switch (iconName) {
      case 'users': return <Users className="w-5 h-5" />;
      case 'file-spreadsheet': return <FileSpreadsheet className="w-5 h-5" />;
      case 'shield': return <Shield className="w-5 h-5" />;
      case 'book-open': return <BookOpen className="w-5 h-5" />;
      case 'file-text': return <FileText className="w-5 h-5" />;
      case 'compass': return <Compass className="w-5 h-5" />;
      default: return <BookOpen className="w-5 h-5" />;
    }
  };

  const getCategoryColor = (catId: string) => {
    switch (catId) {
      case 'hr': return { badge: 'bg-blue-950 text-blue-400 border-blue-800', border: 'hover:border-blue-500/50', icon: 'bg-blue-950/80 text-blue-400 border-blue-800/60' };
      case 'finance': return { badge: 'bg-emerald-950 text-emerald-400 border-emerald-800', border: 'hover:border-emerald-500/50', icon: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60' };
      case 'policy': return { badge: 'bg-amber-950 text-amber-400 border-amber-800', border: 'hover:border-amber-500/50', icon: 'bg-amber-950/80 text-amber-400 border-amber-800/60' };
      case 'sop': return { badge: 'bg-cyan-950 text-cyan-400 border-cyan-800', border: 'hover:border-cyan-500/50', icon: 'bg-cyan-950/80 text-cyan-400 border-cyan-800/60' };
      case 'contract': return { badge: 'bg-purple-950 text-purple-400 border-purple-800', border: 'hover:border-purple-500/50', icon: 'bg-purple-950/80 text-purple-400 border-purple-800/60' };
      case 'research': return { badge: 'bg-rose-950 text-rose-400 border-rose-800', border: 'hover:border-rose-500/50', icon: 'bg-rose-950/80 text-rose-400 border-rose-800/60' };
      default: return { badge: 'bg-slate-800 text-slate-300 border-slate-700', border: 'hover:border-slate-600', icon: 'bg-slate-800 text-slate-300 border-slate-700' };
    }
  };

  // Filter & Sort Documents
  const filteredDocuments = documents.filter((doc) => {
    if (selectedCategory === 'all') return true;
    return doc.doc_type === selectedCategory;
  }).sort((a, b) => {
    if (sortBy === 'newest') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    if (sortBy === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    if (sortBy === 'title_asc') return a.title.localeCompare(b.title);
    if (sortBy === 'title_desc') return b.title.localeCompare(a.title);
    return 0;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 text-slate-100 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
            Business Knowledge Catalog
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise document indexing, OCR extraction, and automated semantic categorization.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => {
              setUploadDocType('auto');
              setIsUploadModalOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 rounded-xl text-xs font-bold transition shadow-lg shadow-amber-500/20 active:scale-95"
          >
            <UploadCloud className="w-4 h-4" /> Upload Document / Policy
          </button>

          <button
            onClick={handlePurgeDuplicates}
            className="flex items-center gap-2 px-3.5 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-xl text-xs transition font-medium border border-slate-800"
            title="Clean up duplicate test records"
          >
            <ShieldAlert className="w-4 h-4 text-amber-500" /> Purge Duplicates
          </button>

          <button
            onClick={fetchKnowledgeData}
            className="flex items-center gap-2 px-3.5 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-200 rounded-xl text-xs transition font-medium border border-slate-800"
            title="Reload collections & document indexes"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Notification Toast */}
      {actionMessage && (
        <div className={`p-4 rounded-xl text-xs font-semibold flex items-center gap-3 border shadow-lg ${
          actionMessage.type === 'error'
            ? 'bg-rose-950/90 border-rose-800 text-rose-200'
            : actionMessage.type === 'info'
            ? 'bg-blue-950/90 border-blue-800 text-blue-200'
            : 'bg-emerald-950/90 border-emerald-800 text-emerald-200'
        }`}>
          {actionMessage.type === 'error' ? <AlertCircle className="w-5 h-5 flex-shrink-0" /> : <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* Knowledge Collections Cards (6 Canonical Categories) */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-slate-200 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-amber-400" /> Business Knowledge Collections
          </h2>
          <span className="text-xs text-slate-400 font-medium">
            Total {documents.length} Indexed Documents
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {collections.map((col) => {
            const styling = getCategoryColor(col.id);
            const isSelected = selectedCategory === col.id;

            return (
              <div
                key={col.id}
                onClick={() => setSelectedCategory(selectedCategory === col.id ? 'all' : col.id)}
                className={`bg-slate-900/80 border rounded-2xl p-5 transition shadow-lg backdrop-blur-sm cursor-pointer relative group flex flex-col justify-between ${
                  isSelected ? 'border-amber-400 ring-1 ring-amber-400/40 bg-slate-900' : 'border-slate-800 ' + styling.border
                }`}
              >
                <div>
                  <div className="flex justify-between items-start">
                    <div className={`p-3 rounded-xl border ${styling.icon}`}>
                      {getCategoryIcon(col.icon)}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-1 text-xs rounded-full font-bold border ${styling.badge}`}>
                        {col.count} {col.count === 1 ? 'Document' : 'Documents'}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4">
                    <h3 className="text-base font-bold text-slate-100 group-hover:text-amber-400 transition">
                      {col.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1.5 line-clamp-2 leading-relaxed">
                      {col.description}
                    </p>
                  </div>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium group-hover:text-slate-300 transition">
                    {isSelected ? '✓ Showing filtered items' : 'Click to filter'}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openUploadWithCategory(col.id);
                    }}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-300 rounded-lg text-[11px] font-semibold transition"
                    title={`Upload directly to ${col.name}`}
                  >
                    <Plus className="w-3.5 h-3.5" /> Upload
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Semantic + Keyword Hybrid Search */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex items-center gap-3 bg-slate-900/90 border border-slate-800 rounded-2xl px-5 py-3.5 shadow-xl focus-within:border-amber-500/60 transition">
          <Search className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <input
            type="text"
            placeholder="Search policies, invoices, technical SOPs, contracts, employee guidelines, balance sheets..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (!e.target.value.trim()) setSearchResults([]);
            }}
            className="bg-transparent text-sm text-slate-100 placeholder-slate-500 w-full focus:outline-none"
          />
          {searchQuery && (
            <button 
              type="button" 
              onClick={() => { setSearchQuery(''); setSearchResults([]); }}
              className="text-slate-500 hover:text-slate-300 text-xs px-2"
            >
              Clear
            </button>
          )}
          <button
            type="submit"
            className="px-5 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs transition shadow-md flex-shrink-0"
          >
            Hybrid Search
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="bg-slate-900/95 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center">
              <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> Semantic & Keyword Search Matches ({searchResults.length})
              </h3>
              <button
                onClick={() => setSearchResults([])}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                Close Results
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {searchResults.map((res, i) => (
                <div key={i} className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-2 hover:border-slate-700 transition">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-200 truncate max-w-[240px]">{res.title}</span>
                    <span className="text-emerald-400 font-mono text-[10px] bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                      Score: {res.distance !== undefined ? res.distance.toFixed(3) : 'Match'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">{res.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </form>

      {/* Filter Tabs & Sorting Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/50 p-2 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 text-xs font-semibold">
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-2 rounded-xl transition whitespace-nowrap ${
              selectedCategory === 'all'
                ? 'bg-amber-500 text-slate-950 font-bold shadow'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            All Documents ({documents.length})
          </button>
          {collections.map((col) => (
            <button
              key={col.id}
              onClick={() => setSelectedCategory(col.id)}
              className={`px-3 py-2 rounded-xl transition whitespace-nowrap flex items-center gap-1.5 ${
                selectedCategory === col.id
                  ? 'bg-slate-800 text-amber-400 border border-amber-500/40 font-bold shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <span>{col.name.split(' ')[0]}</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-950/80 text-slate-400">
                {col.count}
              </span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 self-end sm:self-center">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 text-slate-300 rounded-xl px-2.5 py-1.5 text-xs focus:outline-none focus:border-amber-500"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="title_asc">Title (A-Z)</option>
              <option value="title_desc">Title (Z-A)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Filtered Document Cards (if any exist) */}
      {filteredDocuments.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center text-xs text-slate-400 font-medium">
            <span>
              Showing {filteredDocuments.length} {filteredDocuments.length === 1 ? 'Document' : 'Documents'}
              {selectedCategory !== 'all' ? ` in ${collections.find(c => c.id === selectedCategory)?.name || selectedCategory}` : ''}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocuments.map((doc) => {
              const styling = getCategoryColor(doc.doc_type);
              return (
                <div
                  key={doc.id}
                  className="p-4 bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl space-y-3 transition shadow-lg flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex justify-between items-start gap-2">
                      <div className="flex items-center gap-2 truncate">
                        <FileText className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                        <span className="font-bold text-slate-200 text-xs truncate" title={doc.title}>
                          {doc.title}
                        </span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border flex-shrink-0 ${styling.badge}`}>
                        {doc.category_name || doc.doc_type?.toUpperCase()}
                      </span>
                    </div>

                    {doc.metadata?.summary && (
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                        {doc.metadata.summary}
                      </p>
                    )}
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <span className="text-[11px] text-slate-500 font-mono">
                      {new Date(doc.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleOpenDocDetails(doc.id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-amber-500 hover:text-slate-950 text-slate-200 rounded-lg transition text-[11px] font-semibold"
                      >
                        Inspect
                      </button>
                      <button
                        onClick={() => handleDeleteDocument(doc.id, doc.title)}
                        className="p-1 text-slate-500 hover:text-red-400 rounded-lg hover:bg-slate-800 transition"
                        title="Delete Document"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Upload Document / Policy Modal */}
      {isUploadModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-950/60">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl border border-amber-500/20">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-100">Upload Company Data & Policies</h2>
                  <p className="text-xs text-slate-400">PDF, DOCX, TXT, CSV, XLSX, MD, or scanned image policies</p>
                </div>
              </div>
              <button
                onClick={() => !uploading && setIsUploadModalOpen(false)}
                disabled={uploading}
                className="p-2 text-slate-400 hover:text-slate-100 rounded-xl hover:bg-slate-800 transition disabled:opacity-50"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleUploadSubmit} className="p-6 space-y-5">
              {/* Dropzone */}
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition flex flex-col items-center justify-center gap-3 ${
                  isDragOver 
                    ? 'border-amber-400 bg-amber-950/20' 
                    : uploadFile 
                    ? 'border-emerald-500/60 bg-emerald-950/10' 
                    : 'border-slate-800 hover:border-slate-700 bg-slate-950/40'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                  className="hidden"
                  accept=".pdf,.docx,.doc,.txt,.csv,.xlsx,.xls,.md,.png,.jpg,.jpeg,.tiff,.webp"
                />

                {uploadFile ? (
                  <div className="space-y-1">
                    <div className="p-3 bg-emerald-500/20 text-emerald-400 rounded-full w-12 h-12 flex items-center justify-center mx-auto">
                      <FileCheck className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-bold text-emerald-300 truncate max-w-sm">{uploadFile.name}</p>
                    <p className="text-xs text-slate-400 font-mono">{(uploadFile.size / 1024).toFixed(1)} KB</p>
                    <span className="text-[11px] text-amber-400 underline block mt-2">Click or drop to replace file</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="p-3 bg-slate-800 text-amber-400 rounded-full w-12 h-12 flex items-center justify-center mx-auto">
                      <UploadCloud className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-200">
                        Drag and drop your document here, or <span className="text-amber-400 underline">browse</span>
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Supports PDF, Word (.docx), Excel, CSV, Text, Markdown, and scanned receipts
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Title input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 block">Document Title</label>
                <input
                  type="text"
                  placeholder="e.g. Employee Leave & Attendance Policy 2026"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-amber-500"
                />
              </div>

              {/* Category selector */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>Knowledge Category</span>
                  <span className="text-[11px] text-amber-400 font-normal">Automated or manual sorting</span>
                </label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-amber-500"
                >
                  <option value="auto">✨ Auto-Detect / AI Classifier (Recommended)</option>
                  <option value="hr">HR & Payroll Policies</option>
                  <option value="finance">Finance & Invoices</option>
                  <option value="policy">Corporate Governance & Compliance</option>
                  <option value="sop">Technical Manuals & Standard Operating Procedures</option>
                  <option value="contract">Vendor & Customer Contracts</option>
                  <option value="research">Market & Product Research</option>
                </select>
                <p className="text-[11px] text-slate-500">
                  {uploadDocType === 'auto'
                    ? '✨ System will analyze file contents and automatically sort into HR, Finance, Compliance, SOPs, Contracts, or Research.'
                    : `Document will be explicitly indexed under "${collections.find(c => c.id === uploadDocType)?.name || uploadDocType}".`}
                </p>
              </div>

              {/* Progress status */}
              {uploadProgress && (
                <div className="p-3 bg-slate-950 border border-amber-500/40 rounded-xl text-xs text-amber-300 flex items-center gap-3 animate-pulse">
                  <RefreshCw className="w-4 h-4 animate-spin flex-shrink-0" />
                  <span>{uploadProgress}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  disabled={uploading}
                  className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold rounded-xl text-xs transition disabled:opacity-50 shadow-lg shadow-amber-500/20"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" /> Ingesting Document...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" /> Ingest & Index Document
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Document Details & AI Extracted Metadata Modal */}
      {selectedDocId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-950/60">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-3">
                  <FileText className="w-6 h-6 text-amber-400" /> {docDetails?.name || 'Document Inspector'}
                </h2>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400 font-mono">
                  <span>Doc ID: {selectedDocId.slice(0, 8)}...</span>
                  <span>•</span>
                  <span className="text-amber-400">{docDetails?.category_name || docDetails?.type?.toUpperCase()}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleDeleteDocument(selectedDocId, docDetails?.name || 'Document')}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-950/50 hover:bg-red-900/80 text-red-300 rounded-xl text-xs transition border border-red-800/60 font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Delete
                </button>
                <button
                  onClick={() => setSelectedDocId(null)}
                  className="p-2 text-slate-400 hover:text-slate-100 rounded-xl hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Tabs */}
            <div className="flex border-b border-slate-800 px-6 bg-slate-950/30 text-xs font-semibold text-slate-400">
              {(['ai_metadata', 'preview', 'ocr'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDocTab(tab)}
                  className={`py-3.5 px-4 uppercase tracking-wider transition border-b-2 ${
                    docTab === tab
                      ? 'border-amber-400 text-amber-400 font-bold'
                      : 'border-transparent hover:text-slate-200'
                  }`}
                >
                  {tab === 'ai_metadata' ? '✨ AI Extracted Metadata' : tab === 'preview' ? 'Document Preview' : 'OCR Stream'}
                </button>
              ))}
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {detailsLoading ? (
                <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="w-6 h-6 animate-spin text-amber-400" />
                  <span>Loading document intelligence metadata...</span>
                </div>
              ) : (
                <>
                  {docTab === 'ai_metadata' && docDetails?.ai_extracted && (
                    <div className="space-y-6">
                      <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl space-y-2">
                        <span className="text-xs text-amber-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                          <Sparkles className="w-4 h-4" /> AI Document Executive Summary
                        </span>
                        <p className="text-sm text-slate-200 leading-relaxed">{docDetails.ai_extracted.summary}</p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl space-y-2">
                          <span className="text-slate-400 font-semibold block">Dynamic Extracted Keywords</span>
                          <div className="flex flex-wrap gap-1.5">
                            {docDetails.ai_extracted.keywords?.map((p: string, i: number) => (
                              <span key={i} className="px-2.5 py-1 rounded-lg bg-slate-800 text-amber-300 font-mono text-[11px]">
                                {p}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl space-y-2">
                          <span className="text-slate-400 font-semibold block">Knowledge Categorization</span>
                          <div className="flex flex-wrap gap-1.5">
                            {docDetails.ai_extracted.entities?.map((c: string, i: number) => (
                              <span key={i} className="px-2.5 py-1 rounded-lg bg-slate-800 text-cyan-400 text-[11px]">
                                {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                          <span className="text-slate-500 block">File Size</span>
                          <span className="text-amber-400 font-mono font-bold text-sm">{docDetails.size}</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                          <span className="text-slate-500 block">Word Count</span>
                          <span className="text-cyan-400 font-mono font-bold text-sm">{docDetails.word_count || 'N/A'} Words</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                          <span className="text-slate-500 block">Estimated Pages</span>
                          <span className="text-slate-200 font-mono font-bold text-sm">{docDetails.pages} Pages</span>
                        </div>
                        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-2xl">
                          <span className="text-slate-500 block">Extraction Confidence</span>
                          <span className="text-emerald-400 font-bold text-sm">
                            {Math.round((docDetails.confidence || 0.98) * 100)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {docTab === 'preview' && (
                    <div className="p-6 bg-slate-950 border border-slate-800 rounded-2xl text-slate-300 text-xs font-mono whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                      {docDetails?.content_preview || 'Document text preview unavailable.'}
                    </div>
                  )}

                  {docTab === 'ocr' && (
                    <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl font-mono text-xs text-slate-300 space-y-2">
                      <span className="text-emerald-400 block font-bold">// OCR Text Stream Output</span>
                      <p className="whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">{docDetails?.content_preview || 'No raw OCR stream data available.'}</p>
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
