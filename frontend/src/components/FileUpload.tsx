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
    <div className="w-full">
      <div 
        className={`relative border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center transition-colors cursor-pointer
          ${dragActive ? 'border-brand bg-brand/10' : 'border-gray-600 hover:border-gray-500 bg-surface'}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={onButtonClick}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          className="hidden" 
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleChange}
        />
        
        <UploadCloud className={`w-12 h-12 mb-4 ${dragActive ? 'text-brand' : 'text-gray-400'}`} />
        <p className="text-lg font-medium text-gray-200">Drag and drop your file here</p>
        <p className="text-sm text-gray-400 mt-2">Supports PDF and DOCX up to {MAX_SIZE_MB}MB</p>
        
        {uploadMutation.isPending && (
          <div className="w-full max-w-xs mt-6">
            <div className="flex justify-between text-xs mb-1 text-gray-400">
              <span>Uploading...</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div className="bg-brand h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      {successStatus && (
        <div className="mt-4 p-3 bg-green-900/30 border border-green-500/50 rounded-lg flex items-center text-green-400 text-sm">
          <CheckCircle2 className="w-4 h-4 mr-2 flex-shrink-0" />
          Upload complete. Status: Processing...
        </div>
      )}
    </div>
  );
}
