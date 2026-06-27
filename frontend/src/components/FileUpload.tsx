import React, { useState, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { UploadCloud, File, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';
import api from '../services/api';

const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

export default function FileUpload() {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [successStatus, setSuccessStatus] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: globalThis.File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProgress(pct);
          }
        },
      });
      return res.data;
    },
    onSuccess: () => {
      setSuccessStatus(true);
      setTimeout(() => {
        setSuccessStatus(false);
        setProgress(0);
      }, 3000);
      // Invalidate documents to refetch list
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
      setProgress(0);
    },
  });

  const validateFile = (file: globalThis.File): boolean => {
    setError(null);
    setSuccessStatus(false);
    
    if (file.size > MAX_SIZE_BYTES) {
      setError(`File size exceeds ${MAX_SIZE_MB}MB limit.`);
      return false;
    }
    
    const validTypes = [
      'application/pdf', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ];
    if (!validTypes.includes(file.type) && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      setError('Only PDF and DOCX files are allowed.');
      return false;
    }
    
    return true;
  };

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (validateFile(file)) {
      uploadMutation.mutate(file);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const onButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div style={{ width: '100%' }}>
      <div 
        className={`dropzone ${dragActive ? 'active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={onButtonClick}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          style={{ display: 'none' }}
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleChange}
        />
        
        <UploadCloud className="dropzone-icon" size={48} />
        <p style={{ fontSize: '1.1rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
          Drag and drop your file here
        </p>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Supports PDF and DOCX up to {MAX_SIZE_MB}MB
        </p>
        
        {uploadMutation.isPending && (
          <div style={{ width: '100%', maxWidth: '300px', margin: '1.5rem auto 0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <div style={{ width: '100%', backgroundColor: 'rgba(255,255,255,0.1)', borderRadius: '99px', height: '8px' }}>
              <div style={{ backgroundColor: 'var(--accent-primary)', height: '8px', borderRadius: '99px', width: `${progress}%`, transition: 'width 0.3s ease' }}></div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-box" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {successStatus && (
        <div style={{ background: 'rgba(0, 245, 212, 0.1)', border: '1px solid rgba(0, 245, 212, 0.3)', color: 'var(--accent-secondary)', padding: '1rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle2 size={16} />
          <span>Upload complete. Status: Processing...</span>
        </div>
      )}
    </div>
  );
}
