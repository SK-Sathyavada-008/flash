import React, { useState, useEffect, useRef } from 'react';
import { X, Copy, Download, Check, FileText } from 'lucide-react';

interface NotepadModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialText?: string;
  title?: string;
}

export const NotepadModal: React.FC<NotepadModalProps> = ({
  isOpen,
  onClose,
  initialText = '',
  title = 'Untitled - Notepad (Flash Windows Simulator)',
}) => {
  const [content, setContent] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copied, setCopied] = useState(false);
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setContent('');
      setIsTyping(false);
      if (typingTimerRef.current) clearInterval(typingTimerRef.current);
      return;
    }

    if (!initialText) {
      setContent('');
      return;
    }

    // Type text character-by-character in authentic deliberate sloth fashion
    setContent('');
    setIsTyping(true);
    let index = 0;

    typingTimerRef.current = setInterval(() => {
      if (index < initialText.length) {
        setContent(initialText.slice(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        if (typingTimerRef.current) clearInterval(typingTimerRef.current);
      }
    }, 28);

    return () => {
      if (typingTimerRef.current) clearInterval(typingTimerRef.current);
    };
  }, [isOpen, initialText]);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'Flash_Note.txt';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="notepad-window"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '90%',
          maxWidth: '640px',
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '10px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeIn 0.2s ease-out',
        }}
      >
        {/* Title bar */}
        <div
          style={{
            background: '#0f172a',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #334155',
            userSelect: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f8fafc', fontSize: '0.85rem' }}>
            <FileText size={16} color="#38bdf8" />
            <span style={{ fontWeight: 600 }}>{title}</span>
            {isTyping && (
              <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontStyle: 'italic' }}>
                (Flash is typing...)
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              padding: '4px',
              borderRadius: '4px',
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Menu bar */}
        <div
          style={{
            display: 'flex',
            gap: '16px',
            padding: '4px 12px',
            background: '#1e293b',
            borderBottom: '1px solid #334155',
            fontSize: '0.8rem',
            color: '#94a3b8',
          }}
        >
          <span style={{ cursor: 'pointer' }}>File</span>
          <span style={{ cursor: 'pointer' }}>Edit</span>
          <span style={{ cursor: 'pointer' }}>Format</span>
          <span style={{ cursor: 'pointer' }}>View</span>
          <span style={{ cursor: 'pointer' }}>Help</span>
        </div>

        {/* Text area */}
        <div style={{ padding: '12px', flex: 1, minHeight: '200px', display: 'flex', flexDirection: 'column' }}>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Type your notes or let Flash write for you..."
            style={{
              width: '100%',
              flex: 1,
              minHeight: '180px',
              background: '#090d16',
              color: '#f1f5f9',
              border: '1px solid #334155',
              borderRadius: '6px',
              padding: '12px',
              fontFamily: "'Consolas', 'Courier New', monospace",
              fontSize: '0.9rem',
              lineHeight: '1.5',
              resize: 'none',
              outline: 'none',
            }}
          />
        </div>

        {/* Footer actions */}
        <div
          style={{
            padding: '8px 12px',
            background: '#0f172a',
            borderTop: '1px solid #334155',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Characters: {content.length} | Lines: {content.split('\n').length}
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleCopy}
              style={{
                background: '#334155',
                color: '#f8fafc',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              {copied ? <Check size={14} color="#22c55e" /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <button
              onClick={handleDownload}
              style={{
                background: '#0284c7',
                color: '#ffffff',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 600,
              }}
            >
              <Download size={14} />
              Save Note
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
