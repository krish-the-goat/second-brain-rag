import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrainCircuit } from 'lucide-react';
import ErrorBoundary from './components/ErrorBoundary';
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
        <header className="header" role="banner">
          <div className="brand">
            <BrainCircuit className="brand-icon" size={32} aria-hidden="true" />
            <span className="text-gradient">Second Brain RAG</span>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Premium Edition</span>
          </div>
        </header>

        {/* Dashboard Main Content */}
        <main className="dashboard" role="main">

          {/* Sidebar (Left) */}
          <aside className="glass-panel sidebar" aria-label="Document management">
            <section aria-labelledby="upload-heading">
              <h2 id="upload-heading" className="section-title">
                Add Knowledge
              </h2>
              <ErrorBoundary fallbackMessage="File upload encountered an error. Please try again.">
                <FileUpload />
              </ErrorBoundary>
            </section>

            <section aria-labelledby="library-heading" style={{ flex: 1, minHeight: '300px' }}>
              <h2 id="library-heading" className="section-title">
                Knowledge Library
              </h2>
              <ErrorBoundary fallbackMessage="Failed to load documents. Please refresh.">
                <DocumentList />
              </ErrorBoundary>
            </section>
          </aside>

          {/* Chat Interface (Right) */}
          <section className="glass-panel chat-container" aria-label="AI Chat">
            <ErrorBoundary fallbackMessage="Chat interface encountered an error. Please refresh the page.">
              <ChatInterface />
            </ErrorBoundary>
          </section>

        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
