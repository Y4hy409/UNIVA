import React, { useState, useEffect } from 'react';
import { 
  MessageSquare, Search, Pin, Archive, Trash2, Edit3, 
  MoreVertical, Clock, Bot, AlertTriangle
} from 'lucide-react';
import { apiFetch } from '../../config/api';

interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  last_message_at: string;
  pinned: boolean;
  archived: boolean;
  message_count: number;
  preview: string;
}

interface ChatHistoryWorkspaceProps {
  onNewChat: () => void;
  onOpenConversation: (id: string) => void;
}

export const ChatHistoryWorkspace: React.FC<ChatHistoryWorkspaceProps> = ({
  onNewChat,
  onOpenConversation
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Actions modal states
  const [editingConv, setEditingConv] = useState<Conversation | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deletingConvId, setDeletingConvId] = useState<string | null>(null);
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  useEffect(() => {
    fetchConversations();
  }, [searchQuery]);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const url = searchQuery.trim() 
        ? `/conversations?q=${encodeURIComponent(searchQuery.trim())}`
        : '/conversations';
      const res = await apiFetch(url);
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error('Failed to fetch conversation history:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePin = async (id: string, currentPinned: boolean, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await apiFetch(`/conversations/${id}/pin`, { method: 'POST' });
      if (res.ok) {
        setConversations(prev => prev.map(c => c.id === id ? { ...c, pinned: !currentPinned } : c));
      }
    } catch (err) {
      console.error('Failed to toggle pin:', err);
    }
    setMenuOpenId(null);
  };

  const handleToggleArchive = async (id: string, _currentArchived: boolean, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await apiFetch(`/conversations/${id}/archive`, { method: 'POST' });
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== id));
      }
    } catch (err) {
      console.error('Failed to archive conversation:', err);
    }
    setMenuOpenId(null);
  };

  const handleSaveRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingConv || !editTitle.trim()) return;
    try {
      const res = await apiFetch(`/conversations/${editingConv.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title: editTitle.trim() })
      });
      if (res.ok) {
        setConversations(prev => prev.map(c => c.id === editingConv.id ? { ...c, title: editTitle.trim() } : c));
        setEditingConv(null);
      }
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingConvId) return;
    try {
      const res = await apiFetch(`/conversations/${deletingConvId}`, { method: 'DELETE' });
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== deletingConvId));
        setDeletingConvId(null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const formatRelativeTime = (isoString: string) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const pinnedConversations = conversations.filter(c => c.pinned);
  const recentConversations = conversations.filter(c => !c.pinned);

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 text-slate-100 font-sans">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent flex items-center gap-3">
            <MessageSquare className="w-8 h-8 text-cyan-400" /> Recent Threads
          </h1>
        </div>

        <button
          onClick={onNewChat}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-500 to-cyan-500 text-slate-950 font-bold rounded-xl hover:opacity-95 transition shadow-lg text-sm self-start md:self-auto"
        >
          New Chat
        </button>
      </div>

      {/* Search Input Bar */}
      <div className="relative max-w-2xl">
        <Search className="w-5 h-5 absolute left-3.5 top-3 text-slate-500" />
        <input
          type="text"
          placeholder="Search conversations by title, message content, or analytical query..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-slate-900/90 border border-slate-800 rounded-xl pl-11 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition shadow-inner"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-3 text-xs text-slate-500 hover:text-slate-300"
          >
            Clear
          </button>
        )}
      </div>

      {loading ? (
        <div className="py-20 text-center text-slate-500 space-y-3">
          <Clock className="w-8 h-8 animate-spin mx-auto text-cyan-400" />
          <p className="text-sm">Loading persistent conversation workspace...</p>
        </div>
      ) : conversations.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-12 text-center space-y-4 max-w-md mx-auto my-12">
          <div className="w-14 h-14 rounded-2xl bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center mx-auto text-cyan-400">
            <Bot className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-200">No previous conversations found. Start a new query!</h3>
          <p className="text-xs text-slate-400">
            {searchQuery ? `No chat records match "${searchQuery}"` : 'Start your first business analytics conversation with CLARIUS Assistant.'}
          </p>
          <button
            onClick={onNewChat}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-400 text-slate-950 font-bold text-xs rounded-lg transition"
          >
            New Chat
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {/* PINNED SECTION */}
          {pinnedConversations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <Pin className="w-3.5 h-3.5 fill-current" /> Pinned Conversations ({pinnedConversations.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {pinnedConversations.map(conv => (
                  <ConversationCard
                    key={conv.id}
                    conv={conv}
                    onOpen={() => onOpenConversation(conv.id)}
                    onTogglePin={(e) => handleTogglePin(conv.id, conv.pinned, e)}
                    onToggleArchive={(e) => handleToggleArchive(conv.id, conv.archived, e)}
                    onRename={() => {
                      setEditingConv(conv);
                      setEditTitle(conv.title);
                      setMenuOpenId(null);
                    }}
                    onDelete={() => {
                      setDeletingConvId(conv.id);
                      setMenuOpenId(null);
                    }}
                    isMenuOpen={menuOpenId === conv.id}
                    onToggleMenu={(e) => {
                      e.stopPropagation();
                      setMenuOpenId(menuOpenId === conv.id ? null : conv.id);
                    }}
                    formatTime={formatRelativeTime}
                  />
                ))}
              </div>
            </div>
          )}

          {/* RECENTS SECTION */}
          {recentConversations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" /> Recent Conversations ({recentConversations.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {recentConversations.map(conv => (
                  <ConversationCard
                    key={conv.id}
                    conv={conv}
                    onOpen={() => onOpenConversation(conv.id)}
                    onTogglePin={(e) => handleTogglePin(conv.id, conv.pinned, e)}
                    onToggleArchive={(e) => handleToggleArchive(conv.id, conv.archived, e)}
                    onRename={() => {
                      setEditingConv(conv);
                      setEditTitle(conv.title);
                      setMenuOpenId(null);
                    }}
                    onDelete={() => {
                      setDeletingConvId(conv.id);
                      setMenuOpenId(null);
                    }}
                    isMenuOpen={menuOpenId === conv.id}
                    onToggleMenu={(e) => {
                      e.stopPropagation();
                      setMenuOpenId(menuOpenId === conv.id ? null : conv.id);
                    }}
                    formatTime={formatRelativeTime}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* RENAME MODAL */}
      {editingConv && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-cyan-400" /> Rename Conversation
              </h3>
              <button onClick={() => setEditingConv(null)} className="text-slate-400 hover:text-slate-200">✕</button>
            </div>
            <form onSubmit={handleSaveRename} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Conversation Title</label>
                <input
                  type="text"
                  required
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingConv(null)}
                  className="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs rounded-lg"
                >
                  Save Title
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deletingConvId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-red-900/60 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-red-400">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold">Delete Conversation?</h3>
            </div>
            <p className="text-xs text-slate-300">
              Are you sure you want to permanently delete this conversation and its associated message history? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setDeletingConvId(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-lg"
              >
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

interface ConversationCardProps {
  conv: Conversation;
  onOpen: () => void;
  onTogglePin: (e: React.MouseEvent) => void;
  onToggleArchive: (e: React.MouseEvent) => void;
  onRename: () => void;
  onDelete: () => void;
  isMenuOpen: boolean;
  onToggleMenu: (e: React.MouseEvent) => void;
  formatTime: (iso: string) => string;
}

const ConversationCard: React.FC<ConversationCardProps> = ({
  conv,
  onOpen,
  onTogglePin,
  onToggleArchive,
  onRename,
  onDelete,
  isMenuOpen,
  onToggleMenu,
  formatTime
}) => {
  return (
    <div
      onClick={onOpen}
      className={`relative group border rounded-xl p-4 transition shadow-lg cursor-pointer flex flex-col justify-between ${
        conv.pinned 
          ? 'bg-gradient-to-r from-slate-900 via-slate-900/90 to-amber-950/20 border-amber-800/40 hover:border-amber-500/60' 
          : 'bg-slate-900/70 border-slate-800 hover:border-cyan-800/80 hover:bg-slate-900/90'
      }`}
    >
      <div>
        <div className="flex justify-between items-start gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="p-2 rounded-lg bg-slate-950 text-cyan-400 border border-slate-800 shrink-0">
              <MessageSquare className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-100 truncate group-hover:text-cyan-400 transition">
              {conv.title}
            </h3>
          </div>

          <div className="relative shrink-0">
            <button
              onClick={onToggleMenu}
              className="p-1 rounded text-slate-500 hover:text-slate-200 hover:bg-slate-800"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {isMenuOpen && (
              <>
                <div 
                  className="fixed inset-0 z-20" 
                  onClick={(e) => { e.stopPropagation(); onToggleMenu(e); }} 
                />
                <div className="absolute right-0 top-7 z-30 w-36 bg-slate-950 border border-slate-800 rounded-xl shadow-2xl py-1 text-xs space-y-0.5">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRename();
                    }}
                    className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 flex items-center gap-2"
                  >
                    <Edit3 className="w-3.5 h-3.5 text-cyan-400" /> Rename
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onTogglePin(e);
                    }}
                    className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 flex items-center gap-2"
                  >
                    <Pin className="w-3.5 h-3.5 text-amber-400" /> {conv.pinned ? 'Unpin' : 'Pin'}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleArchive(e);
                    }}
                    className="w-full text-left px-3 py-1.5 text-slate-300 hover:bg-slate-800 flex items-center gap-2"
                  >
                    <Archive className="w-3.5 h-3.5 text-slate-400" /> Archive
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete();
                    }}
                    className="w-full text-left px-3 py-1.5 text-red-400 hover:bg-red-950/60 flex items-center gap-2"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-400" /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-400 mt-2.5 line-clamp-2 pl-9 font-normal">
          {conv.preview || 'No preview available'}
        </p>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/80 flex justify-between items-center text-[11px] text-slate-500 pl-9">
        <span>{conv.message_count || 0} messages</span>
        <span>{formatTime(conv.last_message_at || conv.updated_at)}</span>
      </div>
    </div>
  );
};
