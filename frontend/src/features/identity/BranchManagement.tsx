import React, { useEffect, useState, useMemo } from 'react';
import { 
  MapPin, Users, Building, Plus, Upload, Download, FileSpreadsheet, 
  Search, SlidersHorizontal, MoreVertical, X, Eye, Edit, Trash2 
} from 'lucide-react';
import { apiFetch } from '../../config/api';

export interface BranchRecord {
  id: string;
  code: string;
  name: string;
  location: string;
  manager_name: string;
  phone: string;
  operating_hours: string;
  status: string;
  description?: string;
}

export interface BranchMetrics {
  total_branches: number;
  total_managers: number;
  active_branches: number;
}

export const BranchManagement: React.FC = () => {
  const [branches, setBranches] = useState<BranchRecord[]>([]);
  const [metrics, setMetrics] = useState<BranchMetrics>({ total_branches: 0, total_managers: 0, active_branches: 0 });
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  
  // Filters state
  const [filtersOpen, setFiltersOpen] = useState<boolean>(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // Modals state
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [showImportModal, setShowImportModal] = useState<boolean>(false);
  const [viewingBranch, setViewingBranch] = useState<BranchRecord | null>(null);
  const [editingBranch, setEditingBranch] = useState<BranchRecord | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Form draft state
  const [formData, setFormData] = useState<Partial<BranchRecord>>({
    code: '',
    name: '',
    location: '',
    manager_name: '',
    phone: '',
    operating_hours: '10:00 AM - 11:00 PM',
    status: 'Active',
    description: ''
  });
  const [formError, setFormError] = useState<string>('');

  const fetchBranches = async () => {
    try {
      const res = await apiFetch('/admin/branches');
      if (res.ok) {
        const data = await res.json();
        setBranches(data.branches || []);
        setMetrics(data.metrics || { total_branches: 0, total_managers: 0, active_branches: 0 });
      }
    } catch (err) {
      console.error("Failed to load branches", err);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchBranches();
      setLoading(false);
    };
    init();
  }, []);

  const filteredBranches = useMemo(() => {
    return branches.filter(b => {
      const matchQuery = (b.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (b.code || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (b.location || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (b.manager_name || '').toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchStatus = filterStatus === 'all' || b.status.toLowerCase() === filterStatus.toLowerCase();
      return matchQuery && matchStatus;
    });
  }, [branches, searchTerm, filterStatus]);

  const handleSaveBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.code) {
      setFormError("Branch Name and Branch Code are required.");
      return;
    }
    setFormError('');

    try {
      const res = await apiFetch('/admin/branches/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          id: editingBranch ? editingBranch.id : undefined
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save branch");
      }

      setShowAddModal(false);
      setEditingBranch(null);
      await fetchBranches();
    } catch (err: any) {
      setFormError(err.message || "Save branch failed.");
    }
  };

  const handleDeleteBranch = async (branchId: string) => {
    if (!window.confirm("Are you sure you want to remove this branch?")) return;
    try {
      const res = await apiFetch(`/admin/branches/${branchId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchBranches();
      }
    } catch (err) {
      console.error("Failed to delete branch", err);
    }
  };

  const handleExportBranches = () => {
    const headers = ["Branch Name", "Branch Code", "Location", "Assigned Manager", "Phone", "Operating Hours", "Status"];
    const rows = branches.map(b => [
      `"${b.name}"`,
      `"${b.code}"`,
      `"${b.location}"`,
      `"${b.manager_name}"`,
      `"${b.phone}"`,
      `"${b.operating_hours}"`,
      `"${b.status}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `CLARIUS_Branches_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadTemplate = () => {
    const headers = ["Branch Name", "Branch Code", "Location", "Assigned Manager", "Phone", "Operating Hours", "Status"];
    const sampleRow = ["Anna Nagar Branch", "BR-001", "Anna Nagar Chennai", "Meera Manager", "+91 98765 43210", "10:00 AM - 11:00 PM", "Active"];
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), sampleRow.join(",")].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "Branch_Import_Template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const text = evt.target?.result as string;
        const lines = text.split('\n').filter(l => l.trim().length > 0);
        if (lines.length <= 1) return;

        const importedList: Partial<BranchRecord>[] = [];
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(',').map(c => c.replace(/^"|"$/g, '').trim());
          if (cols.length >= 2) {
            importedList.push({
              name: cols[0] || 'Imported Branch',
              code: cols[1] || `BR-${Math.floor(100 + Math.random() * 900)}`,
              location: cols[2] || '',
              manager_name: cols[3] || 'Unassigned',
              phone: cols[4] || '',
              operating_hours: cols[5] || '10:00 AM - 11:00 PM',
              status: cols[6] || 'Active'
            });
          }
        }

        const res = await apiFetch('/admin/branches/import', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(importedList)
        });

        if (res.ok) {
          setShowImportModal(false);
          await fetchBranches();
        }
      } catch (err) {
        console.error("Failed to parse branch import file", err);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Breadcrumb & Header */}
      <div>
        <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px' }}>
          Business Administration &gt; <span style={{ color: '#94a3b8' }}>Branch Management</span>
        </div>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>Branch Management</h1>
      </div>

      {/* Top 3 Summary Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        
        {/* Card 1: Branches */}
        <div className="card" style={{ padding: '16px 20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Branches</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>{metrics.total_branches}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Operational locations</div>
          </div>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#1e293b', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <MapPin size={20} />
          </div>
        </div>

        {/* Card 2: Managers */}
        <div className="card" style={{ padding: '16px 20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Managers</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>{metrics.total_managers}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Assigned branch owners</div>
          </div>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#1e293b', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Users size={20} />
          </div>
        </div>

        {/* Card 3: Active Branches */}
        <div className="card" style={{ padding: '16px 20px', backgroundColor: '#0d131f', border: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Active Branches</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>{metrics.active_branches}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>Live branches</div>
          </div>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: '#1e293b', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Building size={20} />
          </div>
        </div>

      </div>

      {/* Action Buttons Toolbar */}
      <div className="card" style={{ padding: '12px 16px', backgroundColor: '#0d131f', border: '1px solid #1e293b', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px' }}>
        <button
          type="button"
          className="btn btn-primary"
          style={{ padding: '8px 18px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '13px' }}
          onClick={() => {
            setEditingBranch(null);
            setFormData({ code: '', name: '', location: '', manager_name: '', phone: '', operating_hours: '10:00 AM - 11:00 PM', status: 'Active', description: '' });
            setShowAddModal(true);
          }}
        >
          <Plus size={16} />
          <span>Add</span>
        </button>

        <button
          type="button"
          className="btn"
          style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#f8fafc', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          onClick={() => setShowImportModal(true)}
        >
          <Upload size={15} />
          <span>Import</span>
        </button>

        <button
          type="button"
          className="btn"
          style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#f8fafc', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          onClick={handleExportBranches}
        >
          <Download size={15} />
          <span>Export</span>
        </button>

        <button
          type="button"
          className="btn"
          style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#f8fafc', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          onClick={handleDownloadTemplate}
        >
          <FileSpreadsheet size={15} />
          <span>Template</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
          <input
            type="text"
            className="input-field"
            placeholder="Search branch"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '100%', paddingLeft: '40px', backgroundColor: '#0d131f', border: '1px solid #1e293b', fontSize: '13px' }}
          />
        </div>

        <button
          type="button"
          className="btn"
          style={{ backgroundColor: filtersOpen ? '#1e293b' : '#0d131f', border: '1px solid #1e293b', color: '#f8fafc', padding: '9px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          onClick={() => setFiltersOpen(!filtersOpen)}
        >
          <SlidersHorizontal size={15} />
          <span>Filters</span>
        </button>
      </div>

      {/* Collapsible Filter Options */}
      {filtersOpen && (
        <div className="card" style={{ padding: '14px 16px', backgroundColor: '#0c1220', border: '1px solid #1e293b', display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div>
            <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>Filter by Status</label>
            <select className="input-field" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
      )}

      {/* Branches Table */}
      <div className="card" style={{ padding: 0, overflow: 'visible' }}>
        <div style={{ overflowX: 'auto', paddingBottom: openMenuId ? '80px' : '0px' }}>
          <table style={{ width: '100%', minWidth: '880px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#0b0f19', borderBottom: '1px solid #1e293b', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '12px 16px' }}>BRANCH NAME</th>
                <th style={{ padding: '12px 16px' }}>BRANCH CODE</th>
                <th style={{ padding: '12px 16px' }}>LOCATION</th>
                <th style={{ padding: '12px 16px' }}>ASSIGNED MANAGER</th>
                <th style={{ padding: '12px 16px' }}>PHONE</th>
                <th style={{ padding: '12px 16px' }}>OPERATING HOURS</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
                    <div className="spinner" style={{ margin: '0 auto 8px auto' }}></div>
                    Loading operational branches...
                  </td>
                </tr>
              ) : filteredBranches.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
                    No branch locations matching criteria.
                  </td>
                </tr>
              ) : (
                filteredBranches.map((branch, bIdx) => {
                  const openAbove = bIdx >= filteredBranches.length - 2 || filteredBranches.length <= 3;
                  return (
                    <tr key={branch.id} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f8fafc' }}>{branch.name}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8' }}>{branch.code}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8' }}>{branch.location}</td>
                      <td style={{ padding: '14px 16px', color: '#f8fafc' }}>{branch.manager_name}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8' }}>{branch.phone || '-'}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8' }}>{branch.operating_hours}</td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', position: 'relative' }}>
                        <button
                          onClick={() => setOpenMenuId(openMenuId === branch.id ? null : branch.id)}
                          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '6px', borderRadius: '4px' }}
                        >
                          <MoreVertical size={16} />
                        </button>

                        {openMenuId === branch.id && (
                          <div style={{
                            position: 'absolute',
                            right: '16px',
                            ...(openAbove ? { bottom: '36px' } : { top: '40px' }),
                            zIndex: 50,
                            backgroundColor: '#0f172a',
                            border: '1px solid #1e293b',
                            borderRadius: '6px',
                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                            minWidth: '110px',
                            overflow: 'hidden'
                          }}>
                            <button
                              onClick={() => { setViewingBranch(branch); setOpenMenuId(null); }}
                              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'none', border: 'none', color: '#f8fafc', fontSize: '12px', cursor: 'pointer', textAlign: 'left' }}
                            >
                              <Eye size={14} /> View
                            </button>
                            <button
                              onClick={() => {
                                setEditingBranch(branch);
                                setFormData(branch);
                                setShowAddModal(true);
                                setOpenMenuId(null);
                              }}
                              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'none', border: 'none', color: '#f8fafc', fontSize: '12px', cursor: 'pointer', textAlign: 'left' }}
                            >
                              <Edit size={14} /> Edit
                            </button>
                            <button
                              onClick={() => { handleDeleteBranch(branch.id); setOpenMenuId(null); }}
                              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'none', border: 'none', color: '#ef4444', fontSize: '12px', cursor: 'pointer', textAlign: 'left' }}
                            >
                              <Trash2 size={14} /> Delete
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Branch Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '540px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{editingBranch ? "Edit Branch" : "Add New Branch"}</h3>
              <button onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', padding: '10px 12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
                {formError}
              </div>
            )}

            <form onSubmit={handleSaveBranch} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Branch Name</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. Anna Nagar Branch"
                    value={formData.name || ''} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Branch Code</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. BR-001"
                    value={formData.code || ''} onChange={(e) => setFormData({ ...formData, code: e.target.value })} required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Location</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. Anna Nagar Chennai"
                    value={formData.location || ''} onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Assigned Manager</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. Meera Manager"
                    value={formData.manager_name || ''} onChange={(e) => setFormData({ ...formData, manager_name: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Phone</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. +91 98765 43210"
                    value={formData.phone || ''} onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Operating Hours</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. 10:00 AM - 11:00 PM"
                    value={formData.operating_hours || ''} onChange={(e) => setFormData({ ...formData, operating_hours: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button type="submit" className="btn btn-primary">Save Branch</button>
                <button type="button" className="btn" style={{ backgroundColor: '#1e293b', color: '#f8fafc' }} onClick={() => setShowAddModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '480px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>Import Branch Directory</h3>
              <button onClick={() => setShowImportModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '14px' }}>
              Upload a CSV or Excel file containing columns for Branch Name, Branch Code, Location, Manager, Phone, and Operating Hours.
            </p>
            <input type="file" accept=".csv,.xlsx" onChange={handleFileUpload} style={{ fontSize: '12px', color: '#94a3b8' }} />
          </div>
        </div>
      )}

      {/* View Branch Modal */}
      {viewingBranch && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '480px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{viewingBranch.name}</h3>
              <button onClick={() => setViewingBranch(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px' }}>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Branch Code</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingBranch.code}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Location</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingBranch.location}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Assigned Manager</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingBranch.manager_name}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Operating Hours</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingBranch.operating_hours}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
