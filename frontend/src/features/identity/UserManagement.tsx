import React, { useEffect, useState, useMemo } from 'react';
import { 
  Plus, Upload, Download, FileSpreadsheet, SlidersHorizontal, Search, 
  X, CheckCircle2, RefreshCw 
} from 'lucide-react';
import { KebabMenu } from '../../components/ui/KebabMenu';
import { apiFetch } from '../../config/api';

export interface UserRecord {
  id: string;
  username: string;
  email: string;
  full_name: string;
  phone: string;
  role: string;
  department: string;
  branch: string;
  team: string;
  status: 'Active' | 'Inactive' | 'Suspended';
  reporting_manager: string;
  employee_id: string;
  joining_date: string;
}

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Dynamic Options
  const [availableBranches, setAvailableBranches] = useState<string[]>([]);
  const [availableDepartments, setAvailableDepartments] = useState<string[]>([]);
  const [availableRoles, setAvailableRoles] = useState<{ id: string; name: string }[]>([]);

  // Filter state
  const [filtersOpen, setFiltersOpen] = useState<boolean>(false);
  const [filterRole, setFilterRole] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterBranch, setFilterBranch] = useState<string>('all');
  const [filterDepartment, setFilterDepartment] = useState<string>('all');

  // Modals state
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [showImportModal, setShowImportModal] = useState<boolean>(false);
  const [viewingUser, setViewingUser] = useState<UserRecord | null>(null);
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Form draft state
  const [formData, setFormData] = useState<Partial<UserRecord>>({
    full_name: '',
    email: '',
    phone: '',
    role: 'staff',
    branch: '',
    department: '',
    team: '',
    reporting_manager: '',
    employee_id: '',
    joining_date: '',
    status: 'Active'
  });

  const [formError, setFormError] = useState<string>('');
  const [erpSyncing, setErpSyncing] = useState<boolean>(false);
  const [erpMessage, setErpMessage] = useState<string | null>(null);

  const fetchDirectory = async () => {
    try {
      const res = await apiFetch('/admin/users/directory');
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error("Failed to load users directory", err);
    }
  };

  const fetchOptions = async () => {
    try {
      const [bRes, dRes, rRes] = await Promise.all([
        apiFetch('/admin/branches'),
        apiFetch('/admin/departments'),
        apiFetch('/auth/roles')
      ]);
      if (bRes.ok) {
        const data = await bRes.json();
        setAvailableBranches((data.branches || []).map((b: any) => b.name));
      }
      if (dRes.ok) {
        const data = await dRes.json();
        setAvailableDepartments((data || []).map((d: any) => d.name));
      }
      if (rRes.ok) {
        const data = await rRes.json();
        setAvailableRoles(data || []);
      }
    } catch (e) {
      console.error("Failed to load options", e);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchDirectory(), fetchOptions()]);
      setLoading(false);
    };
    init();
  }, []);

  const filteredUsers = useMemo(() => {
    return users.filter(user => {
      const nameMatch = (user.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                        (user.email || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                        (user.username || '').toLowerCase().includes(searchTerm.toLowerCase());
      
      const roleMatch = filterRole === 'all' || user.role.toLowerCase() === filterRole.toLowerCase();
      const statusMatch = filterStatus === 'all' || user.status.toLowerCase() === filterStatus.toLowerCase();
      const branchMatch = filterBranch === 'all' || user.branch.toLowerCase().includes(filterBranch.toLowerCase());
      const deptMatch = filterDepartment === 'all' || user.department.toLowerCase().includes(filterDepartment.toLowerCase());

      return nameMatch && roleMatch && statusMatch && branchMatch && deptMatch;
    });
  }, [users, searchTerm, filterRole, filterStatus, filterBranch, filterDepartment]);

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.full_name || !formData.email) {
      setFormError("Full Name and Email address are required.");
      return;
    }
    setFormError('');

    try {
      const res = await apiFetch('/admin/users/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          branch: formData.branch || (availableBranches[0] || 'Default Branch'),
          department: formData.department || (availableDepartments[0] || 'Default Dept'),
          id: editingUser ? editingUser.id : undefined
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to save user profile");
      }

      setShowAddModal(false);
      setEditingUser(null);
      await fetchDirectory();
    } catch (err: any) {
      setFormError(err.message || "Save user failed.");
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!window.confirm("Are you sure you want to remove this user profile?")) return;
    try {
      const res = await apiFetch(`/admin/users/${userId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchDirectory();
      }
    } catch (err) {
      console.error("Failed to delete user", err);
    }
  };

  const handleErpSync = async () => {
    setErpSyncing(true);
    setErpMessage(null);
    try {
      const res = await apiFetch('/admin/users/import-erp', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setErpMessage(data.message || `Successfully synced ${data.imported_count} ERP profiles!`);
        await fetchDirectory();
      } else {
        const err = await res.json();
        throw new Error(err.detail || "ERP sync failed");
      }
    } catch (err: any) {
      setErpMessage(`Error: ${err.message}`);
    } finally {
      setErpSyncing(false);
    }
  };

  const handleExportUsers = () => {
    const headers = ["Full Name", "Email", "Phone", "Role", "Branch", "Department", "Reporting Manager", "Employee ID", "Joining Date", "Team", "Status"];
    const rows = users.map(u => [
      `"${u.full_name}"`,
      `"${u.email}"`,
      `"${u.phone}"`,
      `"${u.role}"`,
      `"${u.branch}"`,
      `"${u.department}"`,
      `"${u.reporting_manager}"`,
      `"${u.employee_id}"`,
      `"${u.joining_date}"`,
      `"${u.team}"`,
      `"${u.status}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `CLARIUS_Users_Directory_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadTemplate = () => {
    const headers = ["Full Name", "Email", "Phone", "Role", "Branch", "Department", "Reporting Manager", "Employee ID", "Joining Date", "Team", "Status"];
    const sampleRow = ["Full Name Sample", "user@company.local", "9876543210", "staff", "Main Branch", "Operations", "", "EMP-001", "", "Team A", "Active"];
    
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), sampleRow.join(",")].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "User_Import_Template.csv");
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

        const importedList: Partial<UserRecord>[] = [];
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(',').map(c => c.replace(/^"|"$/g, '').trim());
          if (cols.length >= 2) {
            importedList.push({
              full_name: cols[0] || 'Imported User',
              email: cols[1] || `user_${Date.now()}@workspace.local`,
              phone: cols[2] || '',
              role: (cols[3] || 'staff').toLowerCase(),
              branch: cols[4] || (availableBranches[0] || 'Main Branch'),
              department: cols[5] || (availableDepartments[0] || 'General'),
              reporting_manager: cols[6] || '',
              employee_id: cols[7] || '',
              joining_date: cols[8] || '',
              team: cols[9] || 'General',
              status: (cols[10] || 'Active') as any
            });
          }
        }

        const res = await apiFetch('/admin/users/import-excel', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(importedList)
        });

        if (res.ok) {
          setShowImportModal(false);
          await fetchDirectory();
        }
      } catch (err) {
        console.error("Failed to parse uploaded user file", err);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header & Actions */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#f8fafc', margin: '0 0 4px 0' }}>User Management</h1>
          <div style={{ fontSize: '13px', color: '#94a3b8' }}>
            Total users <strong style={{ color: '#f8fafc' }}>{users.length}</strong>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            className="btn"
            style={{ backgroundColor: filtersOpen ? '#1e293b' : '#0f172a', border: '1px solid #1e293b', color: '#f8fafc', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
            onClick={() => setFiltersOpen(!filtersOpen)}
          >
            <SlidersHorizontal size={15} />
            <span>Filters</span>
          </button>

          <button
            type="button"
            className="btn btn-primary"
            style={{ padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '13px' }}
            onClick={() => {
              setEditingUser(null);
              setFormData({
                full_name: '', email: '', phone: '', role: 'staff',
                branch: availableBranches[0] || '', department: availableDepartments[0] || '', team: '',
                reporting_manager: '', employee_id: '', joining_date: '', status: 'Active'
              });
              setShowAddModal(true);
            }}
          >
            <Plus size={16} />
            <span>Add user</span>
          </button>

          <button
            type="button"
            className="btn"
            style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#f8fafc', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
            onClick={() => { setErpMessage(null); setShowImportModal(true); }}
          >
            <Upload size={15} />
            <span>Import</span>
          </button>

          <button
            type="button"
            className="btn"
            style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', color: '#f8fafc', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
            onClick={handleExportUsers}
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
      </div>

      {/* Dynamic Filters Panel */}
      {filtersOpen && (
        <div className="card" style={{ padding: '16px', backgroundColor: '#0c1220', border: '1px solid #1e293b', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>Filter by Role</label>
            <select className="input-field" value={filterRole} onChange={(e) => setFilterRole(e.target.value)}>
              <option value="all">All Roles</option>
              {availableRoles.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

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
              {availableBranches.map(b => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>Filter by Department</label>
            <select className="input-field" value={filterDepartment} onChange={(e) => setFilterDepartment(e.target.value)}>
              <option value="all">All Departments</option>
              {availableDepartments.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Search Input */}
      <div style={{ position: 'relative', width: '100%' }}>
        <Search size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
        <input
          type="text"
          className="input-field"
          placeholder="Search users"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ width: '100%', paddingLeft: '40px', backgroundColor: '#0d131f', border: '1px solid #1e293b', fontSize: '13px' }}
        />
      </div>

      {/* User Directory Table */}
      <div className="card" style={{ padding: 0, overflow: 'visible' }}>
        <div style={{ overflowX: 'auto', paddingBottom: openMenuId ? '80px' : '0px' }}>
          <table style={{ width: '100%', minWidth: '860px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#0b0f19', borderBottom: '1px solid #1e293b', color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '12px 16px' }}>USER NAME</th>
                <th style={{ padding: '12px 16px' }}>ACCESS</th>
                <th style={{ padding: '12px 16px' }}>STATUS</th>
                <th style={{ padding: '12px 16px', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
                    <div className="spinner" style={{ margin: '0 auto 8px auto' }}></div>
                    Loading workspace user directory...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
                    No users matching search or filter criteria.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user, uIdx) => {
                  const initial = (user.full_name || user.username || 'U')[0].toUpperCase();
                  const openAbove = uIdx > 1 && uIdx >= filteredUsers.length - 2;
                  return (
                    <tr key={user.id} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div style={{
                            width: '36px', height: '36px', borderRadius: '50%',
                            backgroundColor: '#1e293b', color: '#f8fafc',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 700, fontSize: '14px', flexShrink: 0
                          }}>
                            {initial}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '13px' }}>{user.full_name}</div>
                            <div style={{ fontSize: '12px', color: '#94a3b8' }}>{user.email}</div>
                          </div>
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                          <span style={{ backgroundColor: '#1e293b', color: '#f8fafc', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 500, textTransform: 'capitalize' }}>
                            {user.role}
                          </span>
                          {user.department && (
                            <span style={{ backgroundColor: '#1e293b', color: '#94a3b8', padding: '2px 10px', borderRadius: '12px', fontSize: '12px' }}>
                              {user.department}
                            </span>
                          )}
                          {user.branch && (
                            <span style={{ backgroundColor: '#1e293b', color: '#94a3b8', padding: '2px 10px', borderRadius: '12px', fontSize: '12px' }}>
                              {user.branch}
                            </span>
                          )}
                        </div>
                      </td>

                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          backgroundColor: user.status === 'Active' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                          color: user.status === 'Active' ? '#10b981' : '#ef4444',
                          padding: '3px 10px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: 500
                        }}>
                          {user.status}
                        </span>
                      </td>

                      <td style={{ padding: '12px 16px', textAlign: 'right', position: 'relative', zIndex: openMenuId === user.id ? 100 : 1 }}>
                        <KebabMenu
                          isOpen={openMenuId === user.id}
                          onToggle={() => setOpenMenuId(openMenuId === user.id ? null : user.id)}
                          openAbove={openAbove}
                          items={[
                            { label: 'View', icon: 'view', onClick: () => setViewingUser(user) },
                            { label: 'Edit', icon: 'edit', onClick: () => { setEditingUser(user); setFormData(user); setShowAddModal(true); } },
                            { label: 'Delete', icon: 'delete', variant: 'danger', onClick: () => handleDeleteUser(user.id) }
                          ]}
                        />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit User Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{editingUser ? "Edit User Profile" : "Add New User"}</h3>
              <button onClick={() => setShowAddModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            {formError && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', padding: '10px 12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
                {formError}
              </div>
            )}

            <form onSubmit={handleSaveUser} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Full Name</label>
                  <input
                    type="text" className="input-field" placeholder="Full Name"
                    value={formData.full_name || ''} onChange={(e) => setFormData({ ...formData, full_name: e.target.value })} required
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Email Address</label>
                  <input
                    type="email" className="input-field" placeholder="user@company.com"
                    value={formData.email || ''} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Phone Number</label>
                  <input
                    type="text" className="input-field" placeholder="Phone"
                    value={formData.phone || ''} onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Role</label>
                  <select className="input-field" value={formData.role || 'staff'} onChange={(e) => setFormData({ ...formData, role: e.target.value })}>
                    {availableRoles.length > 0 ? (
                      availableRoles.map(r => (
                        <option key={r.id} value={r.id}>{r.name}</option>
                      ))
                    ) : (
                      <>
                        <option value="owner">Owner</option>
                        <option value="admin">Admin</option>
                        <option value="manager">Manager</option>
                        <option value="staff">Staff</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Branch</label>
                  <select className="input-field" value={formData.branch || ''} onChange={(e) => setFormData({ ...formData, branch: e.target.value })}>
                    <option value="">Select Branch</option>
                    {availableBranches.map(b => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Department</label>
                  <select className="input-field" value={formData.department || ''} onChange={(e) => setFormData({ ...formData, department: e.target.value })}>
                    <option value="">Select Department</option>
                    {availableDepartments.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Reporting Manager</label>
                  <input
                    type="text" className="input-field" placeholder="Manager Name"
                    value={formData.reporting_manager || ''} onChange={(e) => setFormData({ ...formData, reporting_manager: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Employee ID</label>
                  <input
                    type="text" className="input-field" placeholder="e.g. EMP-001"
                    value={formData.employee_id || ''} onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Joining Date</label>
                  <input
                    type="date" className="input-field"
                    value={formData.joining_date || ''} onChange={(e) => setFormData({ ...formData, joining_date: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Status</label>
                  <select className="input-field" value={formData.status || 'Active'} onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}>
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button type="submit" className="btn btn-primary">Save User Profile</button>
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
          <div className="card" style={{ width: '100%', maxWidth: '540px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>Import User Directory</h3>
              <button onClick={() => setShowImportModal(false)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            {erpMessage && (
              <div style={{
                backgroundColor: erpMessage.startsWith('Error') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                border: `1px solid ${erpMessage.startsWith('Error') ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                color: erpMessage.startsWith('Error') ? '#ef4444' : '#10b981',
                padding: '10px 12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px'
              }}>
                {erpMessage}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ border: '1px solid #1e293b', borderRadius: '8px', padding: '16px', backgroundColor: '#090d16' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <RefreshCw size={20} style={{ color: '#3b82f6' }} />
                  <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>Sync from Connected ERP Connector</div>
                </div>
                <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 12px 0', lineHeight: 1.4 }}>
                  If connected to an existing ERP system, employee data will automatically be fetched and placed into appropriate user roles, departments, and branches.
                </p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleErpSync}
                  disabled={erpSyncing}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}
                >
                  {erpSyncing ? <div className="spinner" style={{ width: '12px', height: '12px' }}></div> : <CheckCircle2 size={14} />}
                  <span>{erpSyncing ? 'Fetching ERP Data...' : 'Sync Data from Connected ERP'}</span>
                </button>
              </div>

              <div style={{ border: '1px solid #1e293b', borderRadius: '8px', padding: '16px', backgroundColor: '#090d16' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <FileSpreadsheet size={20} style={{ color: '#10b981' }} />
                  <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>Upload Excel / CSV File</div>
                </div>
                <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 12px 0' }}>
                  Select an Excel or CSV file formatted with headers matching the standard template.
                </p>
                <input
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={handleFileUpload}
                  style={{ fontSize: '12px', color: '#94a3b8' }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View User Modal */}
      {viewingUser && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100, padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '520px', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '50%', backgroundColor: '#1e293b', color: '#f8fafc', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '16px' }}>
                  {(viewingUser.full_name || 'U')[0].toUpperCase()}
                </div>
                <div>
                  <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{viewingUser.full_name}</h3>
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>{viewingUser.email}</div>
                </div>
              </div>
              <button onClick={() => setViewingUser(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize: '12px' }}>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Role</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px', textTransform: 'capitalize' }}>{viewingUser.role}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Status</div>
                <div style={{ fontWeight: 600, color: viewingUser.status === 'Active' ? '#10b981' : '#ef4444', marginTop: '2px' }}>{viewingUser.status}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Branch</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingUser.branch || 'None'}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Department</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingUser.department || 'None'}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Reporting Manager</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingUser.reporting_manager || 'None'}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ color: '#94a3b8' }}>Employee ID</div>
                <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '2px' }}>{viewingUser.employee_id || 'N/A'}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
