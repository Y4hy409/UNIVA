import React, { useEffect, useState, useMemo } from 'react';
import { 
  Plus, Upload, Download, FileSpreadsheet, Search, 
  X, SlidersHorizontal, MoreVertical, Eye, Edit, Trash2
} from 'lucide-react';
import { apiFetch } from '../../config/api';

export interface DepartmentRecord {
  id: string;
  code: string;
  name: string;
  branch: string;
  manager_name: string;
  description: string;
  department_members: number;
  status: string;
}

export const DepartmentManagement: React.FC = () => {
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');
  
  // Filter state
  const [filtersOpen, setFiltersOpen] = useState<boolean>(false);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterBranch, setFilterBranch] = useState<string>('all');

  // Modal states
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [showImportModal, setShowImportModal] = useState<boolean>(false);
  const [viewingDepartment, setViewingDepartment] = useState<DepartmentRecord | null>(null);
  const [editingDepartment, setEditingDepartment] = useState<DepartmentRecord | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Form draft state
  const [formData, setFormData] = useState<Partial<DepartmentRecord>>({
    code: '',
    name: '',
    branch: 'Anna Nagar Branch',
    manager_name: '',
    description: '',
    status: 'Active'
  });
  const [formError, setFormError] = useState<string>('');

  const fetchDepartments = async () => {
    try {
      const res = await apiFetch('/admin/departments');
      if (res.ok) {
        const data = await res.json();
        setDepartments(data);
      }
    } catch (err) {
      console.error("Failed to load departments catalog", err);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchDepartments();
      setLoading(false);
    };
    init();
  }, []);

  const filteredDepartments = useMemo(() => {
    return departments.filter(d => {
      const matchQuery = (d.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (d.code || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (d.branch || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (d.manager_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (d.description || '').toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchStatus = filterStatus === 'all' || d.status.toLowerCase() === filterStatus.toLowerCase();
      const matchBranch = filterBranch === 'all' || d.branch.toLowerCase().includes(filterBranch.toLowerCase());

      return matchQuery && matchStatus && matchBranch;
    });
  }, [departments, searchTerm, filterStatus, filterBranch]);

  const handleSaveDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.code) {
      setFormError("Department Name and Code are required.");
      return;
    }
    setFormError('');

    try {
      const res = await apiFetch('/admin/departments/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          id: editingDepartment ? editingDepartment.id : undefined
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save department");
      }

      setShowAddModal(false);
      setEditingDepartment(null);
      await fetchDepartments();
    } catch (err: any) {
      setFormError(err.message || "Save department failed.");
    }
  };

  const handleDeleteDepartment = async (deptId: string) => {
    if (!window.confirm("Are you sure you want to remove this department?")) return;
    try {
      const res = await apiFetch(`/admin/departments/${deptId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchDepartments();
      }
    } catch (err) {
      console.error("Failed to delete department", err);
    }
  };

  const handleExportDepartments = () => {
    const headers = ["Department Name", "Department Code", "Branch", "Manager", "Description", "Department Members", "Status"];
    const rows = departments.map(d => [
      `"${d.name}"`,
      `"${d.code}"`,
      `"${d.branch}"`,
      `"${d.manager_name}"`,
      `"${d.description}"`,
      `"${d.department_members}"`,
      `"${d.status}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `CLARIUS_Departments_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadTemplate = () => {
    const headers = ["Department Name", "Department Code", "Branch", "Manager", "Description", "Status"];
    const sampleRow = ["Profit Analysis Team", "DEPT-001", "Anna Nagar Branch", "Dev Analyst", "Handles imports costs wastage and reporting", "Active"];
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), sampleRow.join(",")].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "Department_Import_Template.csv");
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

        const importedList: Partial<DepartmentRecord>[] = [];
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(',').map(c => c.replace(/^"|"$/g, '').trim());
          if (cols.length >= 2) {
            importedList.push({
              name: cols[0] || 'Imported Department',
              code: cols[1] || `DEPT-${Math.floor(100 + Math.random() * 900)}`,
              branch: cols[2] || 'Anna Nagar Branch',
              manager_name: cols[3] || 'Unassigned',
              description: cols[4] || '',
              status: cols[5] || 'Active'
            });
          }
        }

        const res = await apiFetch('/admin/departments/import', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(importedList)
        });

        if (res.ok) {
          setShowImportModal(false);
          await fetchDepartments();
        }
      } catch (err) {
        console.error("Failed to parse department import file", err);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>Department Management</h1>
      </div>

      {/* Action Toolbar */}
      <div className="card" style={{ padding: '12px 16px', backgroundColor: '#0d131f', border: '1px solid #1e293b', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px' }}>
        <button
          type="button"
          className="btn btn-primary"
          style={{ padding: '8px 18px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '13px' }}
          onClick={() => {
            setEditingDepartment(null);
            setFormData({ code: '', name: '', branch: 'Anna Nagar Branch', manager_name: '', description: '', status: 'Active' });
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
          onClick={handleExportDepartments}
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
            placeholder="Search department"
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

      {/* Collapsible Filter Panel */}
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
          <div>
            <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>Filter by Branch</label>
            <select className="input-field" value={filterBranch} onChange={(e) => setFilterBranch(e.target.value)}>
              <option value="all">All Branches</option>
              <option value="Anna Nagar Branch">Anna Nagar Branch</option>
              <option value="Velachery Branch">Velachery Branch</option>
            </select>
          </div>
        </div>
      )}

      {/* Departments Table */}
      <div className="card" style={{ padding: 0, overflow: 'visible' }}>
        <div style={{ overflowX: 'auto', paddingBottom: openMenuId ? '80px' : '0px' }}>
          <table style={{ width: '100%', minWidth: '880px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#0b0f19', borderBottom: '1px solid #1e293b', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '12px 16px' }}>DEPARTMENT NAME</th>
                <th style={{ padding: '12px 16px' }}>BRANCH</th>
                <th style={{ padding: '12px 16px' }}>MANAGER</th>
                <th style={{ padding: '12px 16px' }}>DESCRIPTION</th>
                <th style={{ padding: '12px 16px' }}>DEPARTMENT MEMBERS</th>
                <th style={{ padding: '12px 16px' }}>STATUS</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
                    <div className="spinner" style={{ margin: '0 auto 8px auto' }}></div>
                    Loading organization departments...
                  </td>
                </tr>
              ) : filteredDepartments.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
                    No departments matching criteria.
                  </td>
                </tr>
              ) : (
                filteredDepartments.map((dept, dIdx) => {
                  const openAbove = dIdx >= filteredDepartments.length - 2 || filteredDepartments.length <= 3;
                  return (
                    <tr key={dept.id} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f8fafc' }}>{dept.name}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8' }}>{dept.branch}</td>
                      <td style={{ padding: '14px 16px', color: '#f8fafc' }}>{dept.manager_name}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8', maxWidth: '300px' }}>{dept.description}</td>
                      <td style={{ padding: '14px 16px', color: '#f8fafc', fontWeight: 600 }}>{dept.department_members}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          backgroundColor: dept.status === 'Active' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                          color: dept.status === 'Active' ? '#10b981' : '#ef4444',
                          padding: '3px 10px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: 500
                        }}>
                          {dept.status}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', position: 'relative' }}>
                        <button
                          onClick={() => setOpenMenuId(openMenuId === dept.id ? null : dept.id)}
                          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '6px', borderRadius: '4px' }}
                        >
                          <MoreVertical size={16} />
                        </button>

                        {openMenuId === dept.id && (
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
                              onClick={() => { setViewingDepartment(dept); setOpenMenuId(null); }}
                              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'none', border: 'none', color: '#f8fafc', fontSize: '12px', cursor: 'pointer', textAlign: 'left' }}
                            >
                              <Eye size={14} /> View
                            </button>
                            <button
                              onClick={() => {
                                setEditingDepartment(dept);
                                setFormData(dept);
                                setShowAddModal(true);
                                setOpenMenuId(null);
                              }}
                              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'none', border: 'none', color: '#f8fafc', fontSize: '12px', cursor: 'pointer', textAlign: 'left' }}
                            >
                              <Edit size={14} /> Edit
                            </button>
                            <button
                              onClick={() => { handleDeleteDepartment(dept.id); setOpenMenuId(null); }}
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

      {/* Add / Edit Department Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '540px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{editingDepartment ? "Edit Department" : "Add New Department"}</h3>
              <button onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', padding: '10px 12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
                {formError}
              </div>
            )}

            <form onSubmit={handleSaveDepartment} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Department Name</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. Profit Analysis Team"
                    value={formData.name || ''} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Department Code</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. DEPT-001"
                    value={formData.code || ''} onChange={(e) => setFormData({ ...formData, code: e.target.value })} required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Branch</label>
                  <select className="input-field" value={formData.branch || 'Anna Nagar Branch'} onChange={(e) => setFormData({ ...formData, branch: e.target.value })}>
                    <option value="Anna Nagar Branch">Anna Nagar Branch</option>
                    <option value="Velachery Branch">Velachery Branch</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Department Manager</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. Dev Analyst"
                    value={formData.manager_name || ''} onChange={(e) => setFormData({ ...formData, manager_name: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Description</label>
                <textarea
                  className="input-field" rows={3} placeholder="Describe department functions..."
                  value={formData.description || ''} onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button type="submit" className="btn btn-primary">Save Department</button>
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
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>Import Department Directory</h3>
              <button onClick={() => setShowImportModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '14px' }}>
              Upload a CSV or Excel file containing columns for Department Name, Department Code, Branch, Manager, Description, and Status.
            </p>
            <input type="file" accept=".csv,.xlsx" onChange={handleFileUpload} style={{ fontSize: '12px', color: '#94a3b8' }} />
          </div>
        </div>
      )}

      {/* View Department Modal */}
      {viewingDepartment && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '480px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{viewingDepartment.name}</h3>
              <button onClick={() => setViewingDepartment(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px' }}>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Branch</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingDepartment.branch}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Manager</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingDepartment.manager_name}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Department Members</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingDepartment.department_members}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Status</div>
                <div style={{ fontWeight: 600, color: viewingDepartment.status === 'Active' ? '#10b981' : '#ef4444', marginTop: '2px' }}>{viewingDepartment.status}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
