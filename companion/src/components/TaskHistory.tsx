import React from 'react';
import { CheckCircle2, AlertCircle, Clock, Trash2, X } from 'lucide-react';
import { TaskRecord } from '../types';

interface TaskHistoryProps {
  tasks: TaskRecord[];
  isOpen: boolean;
  onClose: () => void;
  onClearHistory: () => void;
  onSelectTask: (task: TaskRecord) => void;
}

export const TaskHistory: React.FC<TaskHistoryProps> = ({
  tasks,
  isOpen,
  onClose,
  onClearHistory,
  onSelectTask,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet history-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title-group">
            <h3>Task History</h3>
            <span className="count-badge">{tasks.length}</span>
          </div>
          <div className="modal-header-actions">
            {tasks.length > 0 && (
              <button
                className="btn-text-danger"
                onClick={onClearHistory}
                title="Clear all history"
              >
                <Trash2 size={16} />
                <span>Clear</span>
              </button>
            )}
            <button className="btn-close-modal" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="history-content-scroll">
          {tasks.length === 0 ? (
            <div className="empty-history-notice">
              <Clock size={28} className="text-muted" />
              <p>No recorded tasks yet.</p>
              <span>Commands you execute will be saved here locally.</span>
            </div>
          ) : (
            <div className="history-item-list">
              {tasks.map((t) => (
                <div
                  key={t.id}
                  className={`history-card status-${t.status}`}
                  onClick={() => {
                    onSelectTask(t);
                    onClose();
                  }}
                >
                  <div className="history-card-top">
                    <div className="history-status-indicator">
                      {t.status === 'completed' ? (
                        <CheckCircle2 size={14} className="text-green" />
                      ) : (
                        <AlertCircle size={14} className="text-red" />
                      )}
                      <span className="history-status-name">{t.status}</span>
                    </div>
                    <span className="history-time">
                      {new Date(t.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <p className="history-prompt">"{t.prompt}"</p>
                  {t.steps && t.steps.length > 0 && (
                    <span className="history-step-count">
                      {t.steps.length} {t.steps.length === 1 ? 'step' : 'steps'} executed
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
