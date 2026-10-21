import React from 'react';
import { Code2, ExternalLink, Laptop, ShieldCheck, X, Zap } from 'lucide-react';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenPairing: () => void;
}

export const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose, onOpenPairing }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet about-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title-group">
            <span className="flash-emoji">🦥</span>
            <h3>About Flash Agent</h3>
          </div>
          <button className="btn-close-modal" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="about-content">
          <div className="about-hero-card">
            <h4>Deliberate, Safe AI Desktop Companion</h4>
            <p>
              Flash pairs an interactive mobile companion with a native Windows desktop agent powered by local Gemma 2B inference.
            </p>
          </div>

          <div className="about-section">
            <div className="section-title-row">
              <ShieldCheck size={18} className="text-green" />
              <h5>Security Boundary Guarantee</h5>
            </div>
            <p className="section-text">
              When deployed to <strong>Render</strong>, this web service acts as the cloud coordinator and companion interface. 
              <strong>Render has zero remote access or desktop execution privileges.</strong> All real desktop actions, file modifications, 
              and Office documents execute 100% locally on your Windows PC through the authenticated local agent.
            </p>
          </div>

          <div className="about-section">
            <div className="section-title-row">
              <Zap size={18} className="text-amber" />
              <h5>Hacktoberfest 2026 Partner Stack</h5>
            </div>
            <ul className="partner-list">
              <li><strong>Gemma (Google)</strong>: Local SLM tool planning via Ollama with &lt;1ms fast-path.</li>
              <li><strong>Render</strong>: Cloud coordinator and companion web app hosting.</li>
              <li><strong>ElevenLabs</strong>: Neural speech synthesis with offline SAPI fallback.</li>
              <li><strong>Browserbase / Stagehand</strong>: Web extraction and browser reasoning.</li>
              <li><strong>MongoDB Atlas</strong>: Optional cloud sync for user routines and settings.</li>
              <li><strong>Sentry</strong>: Privacy-first performance tracing with path and token scrubbing.</li>
            </ul>
          </div>

          <div className="about-actions-row">
            <button
              className="btn-primary-action"
              onClick={() => {
                onClose();
                onOpenPairing();
              }}
            >
              <Laptop size={16} />
              <span>Connect to Your Windows PC</span>
            </button>

            <a
              href="https://github.com/SK-Sathyavada-008/flash"
              target="_blank"
              rel="noreferrer"
              className="btn-github-link"
            >
              <Code2 size={16} />
              <span>View on GitHub</span>
              <ExternalLink size={14} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
