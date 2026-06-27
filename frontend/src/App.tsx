import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrainCircuit } from 'lucide-react';
import FileUpload from './components/FileUpload';
import DocumentList from './components/DocumentList';
import ChatInterface from './components/ChatInterface';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-background text-white font-sans flex flex-col">
        
        {/* Header */}
        <header className="border-b border-gray-800 bg-surface/50 backdrop-blur-md sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center">
            <BrainCircuit className="w-8 h-8 text-brand mr-3" />
            <h1 className="text-xl font-bold tracking-tight">Second Brain RAG</h1>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-[calc(100vh-10rem)]">
            
            {/* Left Column: Docs & Upload */}
            <div className="lg:col-span-5 flex flex-col space-y-6 h-full overflow-y-auto pr-2 pb-8 lg:pb-0">
              <div>
                <h2 className="text-lg font-semibold mb-3">Add Knowledge</h2>
                <FileUpload />
              </div>
              
              <div className="flex-1 min-h-[300px]">
                <h2 className="text-lg font-semibold mb-3">Your Library</h2>
                <DocumentList />
              </div>
            </div>

            {/* Right Column: Chat */}
            <div className="lg:col-span-7 h-full min-h-[500px]">
              <ChatInterface />
            </div>

          </div>
        </main>
      </div>
    </QueryClientProvider>
  );
}

export default App;
