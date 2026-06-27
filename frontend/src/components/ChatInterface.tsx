import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Trash2 } from 'lucide-react';
import Citations from './Citations';

interface CitationType {
  filename: string;
  page_number: string | number;
  excerpt: string;
  score: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationType[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    const history = messages.map(m => ({ role: m.role, content: m.content }));
    const payload = { question: userMessage.content, chat_history: history };

    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify(payload)
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      let aiMessage: Message = { role: 'assistant', content: '' };
      setMessages(prev => [...prev, aiMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') {
              setIsTyping(false);
              break;
            }
            try {
              const data = JSON.parse(dataStr);
              if (data.text) {
                aiMessage.content += data.text;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1] = { ...aiMessage };
                  return newMsgs;
                });
              } else if (data.citations) {
                aiMessage.citations = data.citations;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1] = { ...aiMessage };
                  return newMsgs;
                });
              }
            } catch (e) {
              // ignore parse errors for partial chunks if any
            }
          }
        }
      }
      setIsTyping(false);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'An error occurred while streaming the response.' }]);
      setIsTyping(false);
    }
  };

  const clearChat = () => setMessages([]);

  return (
    <div className="flex flex-col h-full bg-surface rounded-xl border border-gray-800 overflow-hidden relative">
      <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-gray-900/50">
        <h2 className="font-semibold text-gray-200">Assistant</h2>
        {messages.length > 0 && (
          <button onClick={clearChat} className="text-gray-500 hover:text-red-400 transition-colors" title="Clear Chat">
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
        {messages.length === 0 && !isTyping && (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <Bot className="w-12 h-12 mb-4 opacity-50" />
            <p>Ask a question about your documents.</p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center mt-1
                ${msg.role === 'user' ? 'bg-brand/20 text-brand ml-3' : 'bg-gray-800 text-gray-300 mr-3'}`}>
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              
              <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-4 py-3 rounded-2xl ${
                  msg.role === 'user' 
                    ? 'bg-brand text-white rounded-tr-none' 
                    : 'bg-gray-800/80 text-gray-200 rounded-tl-none border border-gray-700/50'
                }`}>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
                </div>
                {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <div className="w-full pl-2">
                    <Citations citations={msg.citations} />
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {isTyping && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="flex justify-start">
            <div className="flex max-w-[85%] flex-row">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-800 text-gray-300 mr-3 flex items-center justify-center mt-1">
                <Bot className="w-4 h-4" />
              </div>
              <div className="px-5 py-4 rounded-2xl rounded-tl-none bg-gray-800/80 border border-gray-700/50 flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-900/50 border-t border-gray-800">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your documents..."
            className="w-full bg-surface border border-gray-700 rounded-full pl-5 pr-12 py-3 text-sm text-white focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand placeholder-gray-500 transition-all shadow-inner"
            disabled={isTyping}
          />
          <button 
            type="submit"
            disabled={!input.trim() || isTyping}
            className="absolute right-2 p-2 bg-brand text-white rounded-full hover:bg-brand/90 disabled:opacity-50 disabled:hover:bg-brand transition-colors"
          >
            <Send className="w-4 h-4 ml-0.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
