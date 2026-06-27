import React, { useState } from 'react';
import { ChevronDown, ChevronRight, FileText, LayoutTemplate } from 'lucide-react';

interface Citation {
  filename: string;
  page_number: string | number;
  excerpt: string;
  score: number;
}

interface CitationsProps {
  citations: Citation[];
}

export default function Citations({ citations }: CitationsProps) {
  const [expanded, setExpanded] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div style={{ marginTop: '0.75rem' }}>
      <button 
        onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500, background: 'none', border: 'none', cursor: 'pointer' }}
      >
        {expanded ? <ChevronDown size={14} style={{ marginRight: '4px' }} /> : <ChevronRight size={14} style={{ marginRight: '4px' }} />}
        Sources ({citations.length})
      </button>

      {expanded && (
        <div style={{ marginTop: '0.75rem', display: 'grid', gap: '0.5rem' }}>
          {citations.map((cite, idx) => {
            const pct = Math.round(cite.score * 100);
            return (
              <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', padding: '0.75rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', color: 'var(--accent-secondary)', fontWeight: 500 }}>
                    <FileText size={14} style={{ marginRight: '6px' }} />
                    <span>{cite.filename}</span>
                    {cite.page_number && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '0.5rem', display: 'flex', alignItems: 'center' }}>
                        <LayoutTemplate size={12} style={{ marginRight: '4px' }} /> p. {cite.page_number}
                      </span>
                    )}
                  </div>
                  <span style={{ 
                    fontSize: '0.7rem', fontWeight: 600, padding: '0.15rem 0.5rem', borderRadius: '99px',
                    background: pct > 80 ? 'rgba(0, 245, 212, 0.1)' : 'rgba(157, 78, 221, 0.1)',
                    color: pct > 80 ? 'var(--accent-secondary)' : 'var(--accent-primary)'
                  }}>
                    {pct}% match
                  </span>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', fontStyle: 'italic', opacity: 0.9 }}>"{cite.excerpt}..."</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
