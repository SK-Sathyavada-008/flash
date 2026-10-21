import React from 'react';
import { AlertCircle, CheckCircle2, Clock, Loader2, Play } from 'lucide-react';
import { TaskRecord } from '../types';

interface TaskProgressProps {
  task: TaskRecord | null;
  onConfirmTask?: (prompt: string) => void;
}

export const TaskProgress: React.FC<TaskProgressProps> = ({ task, onConfirmTask }) => {
  if (!task) {
    return (
      <div className="task-empty-state">
        <p className="empty-title">No task active</p>
        <p className="empty-sub">Say or type a command to wake up Flash.</p>
      </div>
    );
  }

  const isCompleted = task.status === 'completed';
  const isFailed = task.status === 'failed';
  const isThinking = task.status === 'thinking';
  const isExecuting = task.status === 'executing';

  return (
    <div className={`task-progress-card status-${task.status}`}>
      <div className="task-header-row">
        <div className="task-status-pill">
          {isThinking && <Loader2 size={14} className="spin" />}
          {isExecuting && <Loader2 size={14} className="spin text-blue" />}
          {isCompleted && <CheckCircle2 size={14} className="text-green" />}
          {isFailed && <AlertCircle size={14} className="text-red" />}
          <span className="task-status-label">{task.status.toUpperCase()}</span>
        </div>

        {task.execution_time_ms !== undefined && (
          <div className="task-timing">
            <Clock size={13} />
            <span>{(task.execution_time_ms / 1000).toFixed(1)}s</span>
          </div>
        )}
      </div>

      {/* Original user prompt */}
      <div className="task-prompt-section">
        <span className="prompt-label">Prompt:</span>
        <p className="prompt-text">"{task.prompt}"</p>
      </div>

      {/* Interpreted intent / Flash's words */}
      {task.explanation && (
        <div className="task-explanation-box">
          <span className="flash-emoji">🦥</span>
          <p className="explanation-text">{task.explanation}</p>
        </div>
      )}

      {/* Confirmation gate if needed */}
      {task.error === 'CONFIRMATION_REQUIRED' && onConfirmTask && (
        <div className="confirmation-banner">
          <AlertCircle size={18} className="text-amber" />
          <div className="confirmation-content">
            <p className="confirm-title">Confirmation Required</p>
            <p className="confirm-sub">This action makes real changes to your computer.</p>
            <button
              className="btn-confirm-action"
              onClick={() => onConfirmTask(task.prompt)}
            >
              <Play size={14} />
              <span>Confirm & Proceed</span>
            </button>
          </div>
        </div>
      )}

      {/* Multi-step execution breakdown */}
      {task.steps && task.steps.length > 0 && (
        <div className="task-steps-list">
          <span className="steps-header">
            Execution Steps ({task.steps.length} {task.totalSteps ? `of ${task.totalSteps}` : ''})
          </span>
          {task.steps.map((step, idx) => (
            <div
              key={idx}
              className={`step-row ${
                step.success === true ? 'success' : step.success === false ? 'failure' : 'pending'
              }`}
            >
              <div className="step-icon">
                {step.success === true ? (
                  <CheckCircle2 size={15} className="text-green" />
                ) : step.success === false ? (
                  <AlertCircle size={15} className="text-red" />
                ) : (
                  <Loader2 size={15} className="spin text-blue" />
                )}
              </div>
              <div className="step-details">
                <div className="step-action-name">
                  <span>{step.action_name}</span>
                </div>
                <p className="step-explanation">{step.message || step.explanation}</p>
                {step.output_path && (
                  <span className="step-path-badge" title={step.output_path}>
                    📁 {step.output_path.split('\\').pop() || step.output_path}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error display if failed */}
      {isFailed && task.error && task.error !== 'CONFIRMATION_REQUIRED' && (
        <div className="task-error-box">
          <AlertCircle size={15} />
          <span>Error: {task.error}</span>
        </div>
      )}
    </div>
  );
};
