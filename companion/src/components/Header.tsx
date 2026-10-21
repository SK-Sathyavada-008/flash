import React from 'react';
import { OctagonX, Settings as SettingsIcon, Wifi, WifiOff } from 'lucide-react';
import { ConnectionStatus } from '../types';

interface HeaderProps {
  connectionStatus: ConnectionStatus;
  isEmergencyStopped: boolean;
  onOpenSettings: () => void;
  onOpenPairing: () => void;
  onEmergencyStop: () => void;
  onResume: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  connectionStatus,
  isEmergencyStopped,
  onOpenSettings,
  onOpenPairing,
  onEmergencyStop,
  onResume,
}) => {
  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Conn Error';
      case 'disconnected':
      default:
        return 'Pair Device';
    }
  };

  return (
    <header className="app-header">
      <div className="header-brand">
        <span className="brand-icon">🦥</span>
        <div className="brand-text">
          <h1>Flash</h1>
          <span className="brand-tag">Companion</span>
        </div>
      </div>

      <div className="header-actions">
        {/* Connection status pill */}
        <button
          className={`connection-pill status-${connectionStatus}`}
          onClick={connectionStatus !== 'connected' ? onOpenPairing : onOpenSettings}
          title="Connection details"
        >
          {connectionStatus === 'connected' ? (
            <Wifi size={14} className="icon-pulse" />
          ) : (
            <WifiOff size={14} />
          )}
          <span>{getStatusText()}</span>
        </button>

        {/* Emergency Stop / Resume button */}
        {isEmergencyStopped ? (
          <button
            className="btn-resume-header"
            onClick={onResume}
            title="Resume Flash agent operations"
          >
            Resume
          </button>
        ) : (
          <button
            className="btn-stop-header"
            onClick={onEmergencyStop}
            title="Emergency Stop: Halt agent immediately"
          >
            <OctagonX size={15} />
            <span>STOP</span>
          </button>
        )}

        {/* Settings button */}
        <button
          className="btn-icon-settings"
          onClick={onOpenSettings}
          aria-label="Companion Settings"
          title="Settings"
        >
          <SettingsIcon size={19} />
        </button>
      </div>
    </header>
  );
};
