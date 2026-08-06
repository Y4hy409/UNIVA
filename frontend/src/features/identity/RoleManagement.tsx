import React, { useEffect, useState, useMemo } from 'react';
import { 
  Plus, X 
} from 'lucide-react';
import { apiFetch } from '../../config/api';
import { KebabMenu } from '../../components/ui/KebabMenu';

export interface RoleRecord {
  id: string;
  name: string;
  description: string;
  level: number;
  status: 'Active' | 'Inactive';
  permissions: Record<string, string[]>;
  assigned_users_count?: number;
}

export interface HierarchyNodeData {
  user: {
    id: string;
    name: string;
    username: string;
    email: string;
    department: string;
    branch: string;
  };
  roleId: string;
  role: string;
  level: number;
  children: HierarchyNodeData[];
}

const DEFAULT_PERMISSIONS_CONFIG = [
  {
    module: 'System Control',
    permissions: ['system.settings.update', 'system.health.read', 'audit.read', 'license.manage']
  },
  {
    module: 'Sales & Operations',
    permissions: ['sales.read', 'sales.create', 'sales.update', 'sales.delete']
  },
  {
    module: 'Knowledge & Documents',
    permissions: ['docs.read', 'docs.upload', 'docs.delete', 'rag.query']
  },
  {
    module: 'ERP Connectors',
    permissions: ['erp.read', 'erp.sync', 'erp.configure']
  }
];

export const RoleManagement: React.FC = () => {
  const [roles, setRoles] = useState<RoleRecord[]>([]);
  const [hierarchy, setHierarchy] = useState<HierarchyNodeData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [draft, setDraft] = useState<Partial<RoleRecord> | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [viewingRole, setViewingRole] = useState<RoleRecord | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string>('');

  const fetchRolesCatalog = async () => {
    try {
      const res = await apiFetch('/admin/roles/catalog');
      if (res.ok) {
        const data = await res.json();
        setRoles(data);
      }
    } catch (err) {
      console.error("Failed to load roles catalog", err);
    }
  };

  const fetchHierarchy = async () => {
    try {
      const res = await apiFetch('/admin/organization/hierarchy');
      if (res.ok) {
        const data = await res.json();
        setHierarchy(data);
      }
    } catch (err) {
      console.error("Failed to load organization hierarchy", err);
    }
  };

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      await Promise.all([fetchRolesCatalog(), fetchHierarchy()]);
      setLoading(false);
    };
    loadAll();
  }, []);

  const sortedRoles = useMemo(
    () => [...roles].sort((a, b) => b.level - a.level),
    [roles]
  );

  const emptyDraft = (): Partial<RoleRecord> => ({
    name: '',
    description: '',
    level: 25,
    status: 'Active',
    permissions: {}
  });

  const handleEditRole = (role: RoleRecord) => {
    setEditingId(role.id);
    setViewingRole(null);
    setDraft({
      id: role.id,
      name: role.name,
      description: role.description,
      level: role.level,
      status: role.status,
      permissions: role.permissions || {}
    });
    setOpenMenuId(null);
  };

  const togglePermission = (moduleName: string, permId: string) => {
    if (!draft) return;
    const currentPerms = draft.permissions || {};
    const moduleList = currentPerms[moduleName] || [];
    const updated = moduleList.includes(permId)
      ? moduleList.filter(p => p !== permId)
      : [...moduleList, permId];

    setDraft({
      ...draft,
      permissions: {
        ...currentPerms,
        [moduleName]: updated
      }
    });
  };

  const toggleAllModulePerms = (moduleName: string, allPerms: string[]) => {
    if (!draft) return;
    const currentPerms = draft.permissions || {};
    const moduleList = currentPerms[moduleName] || [];
    const allSelected = allPerms.every(p => moduleList.includes(p));

    setDraft({
      ...draft,
      permissions: {
        ...currentPerms,
        [moduleName]: allSelected ? [] : [...allPerms]
      }
    });
  };

  const handleSaveRole = async () => {
    if (!draft || !draft.name) {
      setValidationError("Role Name is required.");
      return;
    }
    setValidationError('');

    try {
      const payload = {
        id: editingId || undefined,
        name: draft.name,
        description: draft.description || '',
        level: Number(draft.level || 10),
        status: draft.status || 'Active',
        permissions: draft.permissions || {}
      };

      const res = await apiFetch('/admin/roles/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to save role");
      }

      setDraft(null);
      setEditingId(null);
      await fetchRolesCatalog();
      await fetchHierarchy();
    } catch (err: any) {
      setValidationError(err.message || "Save role failed.");
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner Card */}
      <div className="card" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '12px', padding: '16px 20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', margin: '0 0 4px 0' }}>Organization Roles</h2>
          <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>Reusable roles, permissions, members, and hierarchy.</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => { setEditingId(null); setViewingRole(null); setDraft(emptyDraft()); }}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}
        >
          <Plus size={16} />
          <span>Add Role</span>
        </button>
      </div>

      {/* Roles Table */}
      <div className="card" style={{ padding: 0, overflow: 'visible' }}>
        <div style={{ overflowX: 'auto', paddingBottom: openMenuId ? '80px' : '0px' }}>
          <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ backgroundColor: '#111827', borderBottom: '1px solid #1e293b', color: '#9ca3af', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '12px 16px', width: '60px' }}>S.NO</th>
                <th style={{ padding: '12px 16px', width: '200px' }}>ROLE NAME</th>
                <th style={{ padding: '12px 16px' }}>DESCRIPTION</th>
                <th style={{ padding: '12px 16px', width: '100px', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} style={{ padding: '30px', textAlign: 'center', color: '#9ca3af' }}>
                    <div className="spinner" style={{ margin: '0 auto 8px auto' }}></div>
                    Loading organization roles...
                  </td>
                </tr>
              ) : sortedRoles.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: '24px', textAlign: 'center', color: '#9ca3af' }}>No roles defined. Click "+ Add Role" to create one.</td>
                </tr>
              ) : (
                sortedRoles.map((role, idx) => {
                  const openAbove = idx >= sortedRoles.length - 2 || sortedRoles.length <= 3;
                  return (
                    <tr key={role.id} style={{ borderBottom: '1px solid #1e293b' }}>
                      <td style={{ padding: '14px 16px', color: '#94a3b8' }}>{idx + 1}</td>
                      <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f8fafc' }}>{role.name}</td>
                      <td style={{ padding: '14px 16px', color: '#94a3b8', maxWidth: '400px' }}>{role.description}</td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <KebabMenu
                          isOpen={openMenuId === role.id}
                          onToggle={() => setOpenMenuId(openMenuId === role.id ? null : role.id)}
                          openAbove={openAbove}
                          items={[
                            { label: 'View', icon: 'view', onClick: () => { setViewingRole(role); setDraft(null); } },
                            { label: 'Edit', icon: 'edit', onClick: () => handleEditRole(role) }
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

      {/* Add / Edit Role Modal */}
      {draft && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '640px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{editingId ? "Edit Role" : "Add Role"}</h3>
              <button onClick={() => { setDraft(null); setEditingId(null); }} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            {validationError && (
              <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', padding: '10px 12px', borderRadius: '6px', marginBottom: '14px', fontSize: '13px' }}>
                {validationError}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Role Name</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Example: Branch Manager"
                    value={draft.name || ''}
                    onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Description</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Example: Manages branch operations"
                    value={draft.description || ''}
                    onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Hierarchy Level (1-100)</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    className="input-field"
                    placeholder="Example: 50"
                    value={draft.level ?? 25}
                    onChange={(e) => setDraft({ ...draft, level: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>Status</label>
                  <select
                    className="input-field"
                    value={draft.status || 'Active'}
                    onChange={(e) => setDraft({ ...draft, status: e.target.value as any })}
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>

              {/* Permission Matrix */}
              <div style={{ marginTop: '8px' }}>
                <h4 style={{ color: '#f8fafc', fontSize: '14px', marginBottom: '8px' }}>Permission Matrix</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {DEFAULT_PERMISSIONS_CONFIG.map(group => {
                    const activeModulePerms = draft.permissions?.[group.module] || [];
                    return (
                      <div key={group.module} style={{ border: '1px solid #1e293b', borderRadius: '6px', padding: '12px', backgroundColor: '#090d16' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ fontWeight: 600, fontSize: '13px', color: '#f8fafc' }}>{group.module}</span>
                          <button
                            type="button"
                            onClick={() => toggleAllModulePerms(group.module, group.permissions)}
                            className="btn"
                            style={{ padding: '2px 8px', fontSize: '11px', backgroundColor: '#1e293b', color: '#3b82f6', border: 'none' }}
                          >
                            Select all
                          </button>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '8px' }}>
                          {group.permissions.map(perm => (
                            <label key={perm} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#94a3b8', cursor: 'pointer' }}>
                              <input
                                type="checkbox"
                                checked={activeModulePerms.includes(perm)}
                                onChange={() => togglePermission(group.module, perm)}
                              />
                              <span>{perm}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px' }}>
                <button type="button" className="btn btn-primary" onClick={handleSaveRole}>Save Role</button>
                <button type="button" className="btn" style={{ backgroundColor: '#1e293b', color: '#f8fafc' }} onClick={() => { setDraft(null); setEditingId(null); }}>Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View Role Modal */}
      {viewingRole && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '580px', maxHeight: '90vh', overflowY: 'auto', backgroundColor: '#0d131f', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid #1e293b', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px', fontWeight: 600 }}>{viewingRole.name}</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>{viewingRole.description}</p>
              </div>
              <button onClick={() => setViewingRole(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '16px' }}>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>Hierarchy Level</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#3b82f6', marginTop: '2px' }}>{viewingRole.level}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>Assigned Users</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#3b82f6', marginTop: '2px' }}>{viewingRole.assigned_users_count || 0}</div>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>Accessible Modules</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#3b82f6', marginTop: '2px' }}>{Object.keys(viewingRole.permissions || {}).length}</div>
              </div>
            </div>

            {/* Readonly Matrix */}
            <h4 style={{ color: '#f8fafc', fontSize: '14px', marginBottom: '8px' }}>Configured Permissions</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {DEFAULT_PERMISSIONS_CONFIG.map(group => {
                const perms = viewingRole.permissions?.[group.module] || [];
                return (
                  <div key={group.module} style={{ border: '1px solid #1e293b', borderRadius: '6px', padding: '10px', backgroundColor: '#090d16' }}>
                    <div style={{ fontWeight: 600, fontSize: '12px', color: '#f8fafc', marginBottom: '6px' }}>{group.module}</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {group.permissions.map(p => (
                        <span key={p} style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: perms.includes(p) ? 'rgba(59, 130, 246, 0.15)' : '#1e293b',
                          color: perms.includes(p) ? '#3b82f6' : '#64748b'
                        }}>
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Organization Hierarchy Section */}
      <div className="card" style={{ padding: '20px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', margin: '0 0 16px 0' }}>Organization Hierarchy</h2>
        <div style={{ overflowX: 'auto', paddingBottom: '16px' }}>
          {hierarchy.length === 0 ? (
            <div style={{ color: '#94a3b8', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
              No organization hierarchy nodes found in database.
            </div>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'center', minWidth: '700px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', width: '100%' }}>
                {hierarchy.map(node => (
                  <HierarchyBranch key={node.user.id} node={node} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const HierarchyBranch: React.FC<{ node: HierarchyNodeData }> = ({ node }) => {
  const initial = (node.user.name || node.user.username || 'U')[0].toUpperCase();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {/* Node Card */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        backgroundColor: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: '8px',
        padding: '12px 16px',
        minWidth: '240px',
        maxWidth: '300px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          backgroundColor: '#000',
          color: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '16px',
          flexShrink: 0
        }}>
          {initial}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {node.user.name}
          </div>
          <div style={{ color: '#3b82f6', fontSize: '12px', fontWeight: 500 }}>
            {node.role} - Level {node.level}
          </div>
          <div style={{ color: '#64748b', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {node.user.department} | {node.user.branch}
          </div>
        </div>
      </div>

      {/* Children branches */}
      {node.children && node.children.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', marginTop: '12px' }}>
          {/* Connector Line down */}
          <div style={{ width: '2px', height: '16px', backgroundColor: '#334155' }}></div>
          
          <div style={{ display: 'flex', gap: '24px', position: 'relative' }}>
            {node.children.map(child => (
              <React.Fragment key={child.user.id}>
                <HierarchyBranch node={child} />
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
