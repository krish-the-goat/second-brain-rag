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
    <div className="mt-3">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="flex items-center text-xs text-gray-400 hover:text-brand transition-colors font-medium"
      >
        {expanded ? <ChevronDown className="w-4 h-4 mr-1" /> : <ChevronRight className="w-4 h-4 mr-1" />}
        Sources ({citations.length})
      </button>

      {expanded && (
        <div className="mt-3 grid gap-2">
          {citations.map((cite, idx) => {
            const pct = Math.round(cite.score * 100);
            return (
              <div key={idx} className="bg-gray-800/40 border border-gray-700/50 rounded-lg p-3 text-sm flex flex-col">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center text-brand font-medium">
                    <FileText className="w-3.5 h-3.5 mr-1.5" />
                    <span className="truncate max-w-[180px]">{cite.filename}</span>
                    {cite.page_number && (
                      <span className="text-gray-500 text-xs ml-2 flex items-center">
                        <LayoutTemplate className="w-3 h-3 mr-1" /> p. {cite.page_number}
                      </span>
                    )}
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    pct > 80 ? 'bg-green-500/10 text-green-400' : 'bg-yellow-500/10 text-yellow-400'
                  }`}>
                    {pct}% match
                  </span>
                </div>
                <p className="text-gray-300 text-xs italic opacity-90 line-clamp-3">"{cite.excerpt}..."</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
