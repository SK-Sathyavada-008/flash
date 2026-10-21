import React, { useState } from 'react';
import { Eye, EyeOff, LogOut, RefreshCw, Server, Shield, Sparkles, Trash2, X } from 'lucide-react';
import { agentClient } from '../services/agentClient';

interface SettingsModalProps {
  isOpen: boolean;
  gazeEnabled: boolean;
  onToggleGaze: (enabled: boolean) => void;
  onClose: () => void;
  onClearHistory: () => void;
  onUnpair: () => void;
  onReconnect: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  gazeEnabled,
  onToggleGaze,
  onClose,
  onClearHistory,
  onUnpair,
  onReconnect,
}) => {
  const config = agentClient.getConfig();
  const [host, setHost] = useState(config.host);
  const [port, setPort] = useState(String(config.port));

  if (!isOpen) return null;

  const handleSaveConnection = (e: React.FormEvent) => {
    e.preventDefault();
    agentClient.updateConfig({
      host: host.trim(),
      port: parseInt(port.trim(), 10) || 8765,
    });
    onReconnect();
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet settings-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title-group">
            <span className="dmv-badge-icon">🦥</span>
            <h3>Settings & Preferences</h3>
          </div>
          <button className="btn-close-modal" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="settings-content">
          {/* Zootopia DMV Theme Banner */}
          <div className="dmv-theme-card">
            <div className="dmv-header">
              <span className="dmv-seal">🏛️ ZOOTOPIA DMV</span>
              <span className="dmv-tag">Dept of Mammal Vehicles</span>
            </div>
            <p className="dmv-quote">"Flash, Flash, Hundred Yard Dash... You want it when?"</p>
          </div>

          {/* Gaze Tracking Toggle */}
          <section className="settings-section">
            <div className="section-title">
              <Eye size={18} className="text-amber" />
              <h4>Cursor Gaze Tracking</h4>
            </div>
            <div className="privacy-actions">
              <div className="privacy-row">
                <div>
                  <strong>Sync Eyes to Laptop Mouse</strong>
                  <p>Flash's eyes and head smoothly follow your Windows cursor position in real time.</p>
                </div>
                <button
                  type="button"
                  className={`btn-toggle-switch ${gazeEnabled ? 'active' : ''}`}
                  onClick={() => onToggleGaze(!gazeEnabled)}
                  title={gazeEnabled ? 'Disable cursor gaze' : 'Enable cursor gaze'}
                >
                  {gazeEnabled ? <Eye size={16} /> : <EyeOff size={16} />}
                  <span>{gazeEnabled ? 'ON' : 'OFF'}</span>
                </button>
              </div>
            </div>
          </section>

          {/* Connection Settings */}
          <section className="settings-section">
            <div className="section-title">
              <Server size={18} className="text-amber" />
              <h4>Agent Connection</h4>
            </div>
            <form onSubmit={handleSaveConnection} className="settings-form">
              <div className="form-group">
                <label>Laptop Wi-Fi IP</label>
                <input
                  type="text"
                  className="form-input"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Port</label>
                <input
                  type="number"
                  className="form-input"
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                />
              </div>
              <div className="settings-btn-row">
                <button type="submit" className="btn-secondary-action">
                  <RefreshCw size={15} />
                  <span>Update & Reconnect</span>
                </button>
              </div>
            </form>
          </section>

          {/* Privacy & Pairing */}
          <section className="settings-section">
            <div className="section-title">
              <Shield size={18} className="text-amber" />
              <h4>Privacy & Security</h4>
            </div>
            <div className="privacy-actions">
              <div className="privacy-row">
                <div>
                  <strong>Clear Task History</strong>
                  <p>Removes all saved task logs and prompts from this phone.</p>
                </div>
                <button
                  type="button"
                  className="btn-text-danger"
                  onClick={() => {
                    if (confirm('Clear local task history on this device?')) {
                      onClearHistory();
                    }
                  }}
                >
                  <Trash2 size={16} />
                  <span>Clear</span>
                </button>
              </div>

              <div className="privacy-row">
                <div>
                  <strong>Unpair Companion</strong>
                  <p>Revokes your permanent authorization token on the laptop.</p>
                </div>
                <button
                  type="button"
                  className="btn-danger"
                  onClick={() => {
                    if (confirm('Unpair this phone and revoke authorization?')) {
                      onUnpair();
                      onClose();
                    }
                  }}
                >
                  <LogOut size={16} />
                  <span>Unpair</span>
                </button>
              </div>
            </div>
          </section>

          {/* Device & Agent Metadata */}
          <div className="settings-meta-footer">
            <p>Flash 3D Companion • Disney's Zootopia Edition</p>
            <p>Target Device: {config.deviceName || 'Redmi Android'}</p>
            <p>Auth Token: {config.token ? `${config.token.slice(0, 8)}... (Active)` : 'Not Paired'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
