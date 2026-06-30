import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, FileText, Loader2 } from 'lucide-react';
import api from '../services/api';

interface Document {
  doc_id: string;
  filename: string;
  status: string; // "processing", "completed", "failed" (mapped from job status or Chroma)
  chunk_count: number;
  created_at: string;
}

export default function DocumentList() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: async () => {
      const res = await api.get('/documents');
      return res.data.documents as Document[];
    },
    // Poll every 10 s — polling every 3 s consumes ~20 req/min which alone
    // exceeds the old 10/min global rate limit and causes self-throttling.
    refetchInterval: 10_000, 
  });

  const deleteMutation = useMutation({
    mutationFn: async (docId: string) => {
      await api.delete(`/documents/${docId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleDelete = (docId: string, filename: string) => {
    if (window.confirm(`Are you sure you want to delete ${filename}?`)) {
      deleteMutation.mutate(docId);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-brand" />
      </div>
    );
  }

  const docs = data || [];

  if (docs.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem 1rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: 'var(--glass-border)' }}>
        <FileText size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>No documents yet</h3>
        <p style={{ color: 'var(--text-secondary)' }}>Upload your first document to get started.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {docs.map((doc) => (
        <div key={doc.doc_id} className="doc-card">
          <div className="doc-icon">
            <FileText size={24} />
          </div>
          <div className="doc-info" style={{ flex: 1 }}>
            <h4>{doc.filename}</h4>
            <p>{doc.chunk_count} chunks • Indexed successfully</p>
          </div>
          <button 
            onClick={() => handleDelete(doc.doc_id, doc.filename)}
            className="delete-btn"
            title="Delete document"
          >
            <Trash2 size={18} />
          </button>
        </div>
      ))}
    </div>
  );
}
