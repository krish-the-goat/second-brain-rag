import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrainCircuit } from 'lucide-react';
import FileUpload from './components/FileUpload';
import DocumentList from './components/DocumentList';
import ChatInterface from './components/ChatInterface';
import './index.css';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-container">
        
        {/* Header */}
        <header className="header">
          <div className="brand">
            <BrainCircuit className="brand-icon" size={32} />
            <span className="text-gradient">OmniSync RAG</span>
          </div>
          {/* Add optional right side controls (like theme toggle or user profile) if needed later */}
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Premium Edition</span>
          </div>
        </header>

        {/* Dashboard Main Content */}
        <main className="dashboard">
          
          {/* Sidebar (Left) */}
          <div className="glass-panel sidebar">
            <div>
              <h2 className="section-title">
                Add Knowledge
              </h2>
              <FileUpload />
            </div>
            
            <div style={{ flex: 1, minHeight: '300px' }}>
              <h2 className="section-title">
                Knowledge Library
              </h2>
              <DocumentList />
            </div>
          </div>

          {/* Chat Interface (Right) */}
          <div className="glass-panel chat-container">
            <ChatInterface />
          </div>

        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
