import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrainCircuit, User, LogOut } from 'lucide-react';
import ErrorBoundary from './components/ErrorBoundary';
import FileUpload from './components/FileUpload';
import DocumentList from './components/DocumentList';
import ChatInterface from './components/ChatInterface';
import AuthScreen from './components/AuthScreen';
import { AuthProvider, useAuth } from './context/AuthContext';
import './index.css';

const queryClient = new QueryClient();

function Dashboard() {
  const { userEmail, logout } = useAuth();

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header" role="banner">
        <div className="brand">
          <BrainCircuit className="brand-icon" size={32} aria-hidden="true" />
          <span className="text-gradient">Second Brain RAG</span>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Premium Edition</span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              paddingLeft: '1rem',
              borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
              }}
            >
              <User size={16} style={{ color: 'var(--accent-secondary)' }} aria-hidden="true" />
              <span>{userEmail || 'Account'}</span>
            </div>
            <button
              onClick={logout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
                padding: '0.35rem 0.7rem',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              title="Log out"
              aria-label="Log out"
            >
              <LogOut size={14} aria-hidden="true" />
              <span>Logout</span>
            </button>
          </div>
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
  );
}

function AppContent() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <AuthScreen />;
  }

  return <Dashboard />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </QueryClientProvider>
  );
}
