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
    // We poll if any document implies we might be waiting for it.
    // However, our backend doesn't store "processing" status in ChromaDB yet, it's just in memory jobs.
    // If we wanted to accurately poll, we'd check jobs endpoint.
    // For now, let's poll every 3s if we think something is uploading, or just blindly poll for simplicity.
    refetchInterval: 3000, 
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
      <div className="text-center py-12 bg-surface rounded-xl border border-gray-800">
        <FileText className="w-12 h-12 text-gray-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-200">No documents yet</h3>
        <p className="text-gray-400 mt-2">Upload your first document to get started.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl border border-gray-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-gray-300">
          <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase font-semibold">
            <tr>
              <th className="px-6 py-4">Name</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Chunks</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {docs.map((doc) => (
              <tr key={doc.doc_id} className="hover:bg-gray-800/20 transition-colors">
                <td className="px-6 py-4 font-medium flex items-center">
                  <FileText className="w-4 h-4 mr-2 text-brand" />
                  {doc.filename}
                </td>
                <td className="px-6 py-4">
                  <span className="bg-green-500/10 text-green-400 px-2 py-1 rounded-full text-xs font-medium border border-green-500/20">
                    Ready
                  </span>
                </td>
                <td className="px-6 py-4">{doc.chunk_count}</td>
                <td className="px-6 py-4">
                  <button 
                    onClick={() => handleDelete(doc.doc_id, doc.filename)}
                    className="text-gray-500 hover:text-red-400 transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
