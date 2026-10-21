import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, Laptop, Loader2, QrCode, ShieldCheck, X } from 'lucide-react';
import { agentClient } from '../services/agentClient';

interface PairingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPairSuccess: () => void;
}

export const PairingModal: React.FC<PairingModalProps> = ({
  isOpen,
  onClose,
  onPairSuccess,
}) => {
  const currentConfig = agentClient.getConfig();
  const initialHost =
    typeof window !== 'undefined' &&
    window.location.hostname &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1'
      ? window.location.hostname
      : currentConfig.host;

  const [host, setHost] = useState(initialHost);
  const [port, setPort] = useState(String(currentConfig.port || 8765));
  const [code, setCode] = useState('');
  const [deviceName, setDeviceName] = useState(currentConfig.deviceName || 'Redmi Android');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  React.useEffect(() => {
    if (isOpen) {
      const cfg = agentClient.getConfig();
      const resolved =
        typeof window !== 'undefined' &&
        window.location.hostname &&
        window.location.hostname !== 'localhost' &&
        window.location.hostname !== '127.0.0.1'
          ? window.location.hostname
          : cfg.host;
      setHost(resolved);
      setPort(String(cfg.port || 8765));
      setErrorMessage(null);
      setSuccessMessage(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handlePair = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    const cleanHost = host.trim();
    const cleanPort = parseInt(port.trim(), 10);
    const cleanCode = code.trim();

    if (!cleanHost) {
      setErrorMessage('Please enter your Windows laptop LAN IP address.');
      return;
    }
    if (!cleanCode) {
      setErrorMessage('Please enter the 6-digit pairing code shown on your laptop.');
      return;
    }

    setIsLoading(true);

    try {
      await agentClient.pair(cleanCode, cleanHost, cleanPort, deviceName);
      setSuccessMessage('Successfully paired with Flash! Connecting...');
      setTimeout(() => {
        setIsLoading(false);
        onPairSuccess();
        onClose();
      }, 700);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(
        err.message || 'Pairing failed. Make sure laptop and phone are on the same Wi-Fi.'
      );
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet pairing-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title-group">
            <ShieldCheck size={22} className="text-amber" />
            <h3>Pair Device</h3>
          </div>
          <button className="btn-close-modal" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handlePair} className="pairing-form">
          {/* Instructions card */}
          <div className="info-card">
            <Laptop size={18} className="text-amber" />
            <div className="info-text">
              <strong>Same Wi-Fi Connection</strong>
              <p>
                Connect your Redmi phone to the same Wi-Fi network as your Windows laptop. Run{' '}
                <code>run-agent.ps1</code> on your laptop to see your LAN IP and active pairing code.
              </p>
            </div>
          </div>

          {/* Laptop LAN IP input */}
          <div className="form-group">
            <label htmlFor="agent-ip">Laptop Wi-Fi IP Address</label>
            <input
              id="agent-ip"
              type="text"
              className="form-input"
              placeholder="e.g. 192.168.1.15"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              required
            />
            <span className="form-hint">Run <code>ipconfig</code> in Windows PowerShell to find this.</span>
          </div>

          {/* Port input */}
          <div className="form-group">
            <label htmlFor="agent-port">Agent Port</label>
            <input
              id="agent-port"
              type="number"
              className="form-input"
              value={port}
              onChange={(e) => setPort(e.target.value)}
              required
            />
          </div>

          {/* 6-digit Pairing Code */}
          <div className="form-group">
            <label htmlFor="pair-code">6-Digit Pairing Code</label>
            <div className="code-input-wrapper">
              <QrCode size={20} className="code-icon" />
              <input
                id="pair-code"
                type="text"
                className="form-input code-input"
                placeholder="123-456"
                value={code}
                onChange={(e) => {
                  let val = e.target.value.replace(/[^0-9-]/g, '');
                  if (val.length === 3 && !val.includes('-')) {
                    val = val + '-';
                  }
                  setCode(val);
                }}
                maxLength={7}
                required
              />
            </div>
            <span className="form-hint">
              Generated securely on your laptop. Expires in 5 minutes.
            </span>
          </div>

          {/* Device nickname */}
          <div className="form-group">
            <label htmlFor="device-name">Device Nickname</label>
            <input
              id="device-name"
              type="text"
              className="form-input"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
            />
          </div>

          {/* Status feedback */}
          {errorMessage && (
            <div className="alert-box alert-error" role="alert">
              <AlertCircle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="alert-box alert-success" role="status">
              <CheckCircle2 size={16} />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Action button */}
          <button
            type="submit"
            className="btn-primary-action"
            disabled={isLoading || !host || !code}
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="spin" />
                <span>Pairing With Flash...</span>
              </>
            ) : (
              <span>Pair With Flash</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
