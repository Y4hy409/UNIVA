import React from 'react';
import { MoreVertical, Eye, Edit, Trash2 } from 'lucide-react';

export interface MenuItem {
  label: string;
  icon?: 'view' | 'edit' | 'delete' | React.ReactNode;
  onClick: () => void;
  variant?: 'danger' | 'default';
}

export interface KebabMenuProps {
  isOpen: boolean;
  onToggle: () => void;
  items: MenuItem[];
  openAbove?: boolean;
}

export const KebabMenu: React.FC<KebabMenuProps> = ({
  isOpen,
  onToggle,
  items,
  openAbove = false
}) => {
  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        onClick={onToggle}
        style={{
          background: 'none',
          border: 'none',
          color: '#94a3b8',
          cursor: 'pointer',
          padding: '6px',
          borderRadius: '4px',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <MoreVertical size={16} />
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            right: 0,
            ...(openAbove ? { bottom: '34px' } : { top: '38px' }),
            zIndex: 1000,
            backgroundColor: '#0f172a',
            border: '1px solid #1e293b',
            borderRadius: '6px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
            minWidth: '120px',
            overflow: 'hidden'
          }}
        >
          {items.map((item, index) => {
            const isDanger = item.variant === 'danger';
            return (
              <button
                key={index}
                type="button"
                onClick={() => {
                  item.onClick();
                  onToggle();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%',
                  padding: '8px 12px',
                  background: 'none',
                  border: 'none',
                  color: isDanger ? '#ef4444' : '#f8fafc',
                  fontSize: '12px',
                  cursor: 'pointer',
                  textAlign: 'left'
                }}
              >
                {item.icon === 'view' && <Eye size={14} />}
                {item.icon === 'edit' && <Edit size={14} />}
                {item.icon === 'delete' && <Trash2 size={14} />}
                {typeof item.icon !== 'string' && item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
