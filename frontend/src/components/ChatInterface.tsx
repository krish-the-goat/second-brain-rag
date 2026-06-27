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
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          'X-API-Key': import.meta.env.VITE_API_KEY || 'default-secret-key-change-in-prod'
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
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-status" />
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>AI Research Assistant</h2>
        {messages.length > 0 && (
          <button onClick={clearChat} className="delete-btn" title="Clear Chat" style={{ marginLeft: 'auto' }}>
            <Trash2 size={16} />
          </button>
        )}
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && !isTyping && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <Bot size={48} style={{ opacity: 0.5, marginBottom: '1rem' }} />
            <p>Ask a question about your documents.</p>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="bubble">
              {msg.content}
              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <div className="citations-box">
                  {msg.citations.map((c, idx) => (
                    <span key={idx} className="citation-pill" title={c.excerpt}>
                      {c.filename}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isTyping && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="message ai">
            <div className="bubble" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', minHeight: '44px' }}>
              <span className="spinner"></span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Synthesizing...</span>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-wrapper">
        <form onSubmit={handleSend} className="input-box">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend(e);
              }
            }}
            placeholder="Ask AI Assistant..."
            disabled={isTyping}
            rows={1}
          />
          <button type="submit" disabled={!input.trim() || isTyping} className="btn-send">
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
