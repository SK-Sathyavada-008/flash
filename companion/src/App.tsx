import React, { useState, useEffect, useCallback, useRef } from 'react';
import { History } from 'lucide-react';
import { Header } from './components/Header';
import { SlothAvatar } from './components/SlothAvatar';
import { VoiceControl } from './components/VoiceControl';
import { TaskProgress } from './components/TaskProgress';
import { TaskHistory } from './components/TaskHistory';
import { PairingModal } from './components/PairingModal';
import { SettingsModal } from './components/SettingsModal';
import { agentClient } from './services/agentClient';
import {
  clearTaskHistory,
  loadTaskHistory,
  saveTaskHistory,
} from './services/storage';
import {
  CompanionExpressionState,
  ConnectionStatus,
  CursorGazeCoordinates,
  ServerWebSocketEvent,
  TaskRecord,
  TaskStep,
} from './types';

export const App: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [connectionDetail, setConnectionDetail] = useState<string>('');
  const [expressionState, setExpressionState] = useState<CompanionExpressionState>('disconnected');
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(false);

  // Milestone 4: Cursor Gaze State (centered by default)
  const [cursorGaze, setCursorGaze] = useState<CursorGazeCoordinates | null>({ x: 0.5, y: 0.5 });
  const [gazeEnabled, setGazeEnabled] = useState<boolean>(true);

  const [currentTask, setCurrentTask] = useState<TaskRecord | null>(null);
  const [taskHistory, setTaskHistory] = useState<TaskRecord[]>([]);

  const [isPairingOpen, setIsPairingOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Load saved history & gaze setting on startup
  useEffect(() => {
    setTaskHistory(loadTaskHistory());
    const config = agentClient.getConfig();
    if (config.gazeEnabled !== undefined) {
      setGazeEnabled(config.gazeEnabled);
    }
  }, []);

  const lastWsGazeTimeRef = useRef<number>(0);

  // Real-time mouse pointer tracking when testing companion directly in laptop browser
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // If we recently received remote WebSocket gaze from laptop agent within 350ms, let backend stream take priority
      if (Date.now() - lastWsGazeTimeRef.current < 350) {
        return;
      }
      const normX = Math.max(0, Math.min(1, e.clientX / window.innerWidth));
      const normY = Math.max(0, Math.min(1, e.clientY / window.innerHeight));
      setCursorGaze({ x: normX, y: normY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Update expression state based on connection
  useEffect(() => {
    if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
      setExpressionState('disconnected');
    } else if (isEmergencyStopped) {
      setExpressionState('stopped');
    } else if (expressionState === 'disconnected') {
      setExpressionState('idle');
    }
  }, [connectionStatus, isEmergencyStopped]);

  // Handle incoming WebSocket events from agent backend
  const handleServerEvent = useCallback((event: ServerWebSocketEvent) => {
    const now = Date.now();

    switch (event.type) {
      // Milestone 4: Real-time Cursor Gaze event from Windows agent
      case 'cursor_gaze':
        if (typeof event.x === 'number' && typeof event.y === 'number') {
          lastWsGazeTimeRef.current = Date.now();
          setCursorGaze({ x: event.x, y: event.y });
        }
        break;

      case 'gaze_status':
        if (typeof event.enabled === 'boolean') {
          setGazeEnabled(event.enabled);
        }
        break;

      case 'connection_established':
        setConnectionStatus('connected');
        setIsEmergencyStopped(!!event.emergency_stop_active);
        setExpressionState(event.emergency_stop_active ? 'stopped' : 'idle');
        break;

      case 'stopped':
        setIsEmergencyStopped(true);
        setExpressionState('stopped');
        break;

      case 'resumed':
        setIsEmergencyStopped(false);
        setExpressionState('idle');
        break;

      case 'task_started': {
        const newTask: TaskRecord = {
          id: event.task_id || String(now),
          prompt: event.prompt || '',
          status: 'executing',
          steps: [],
          timestamp: now,
        };
        setCurrentTask(newTask);
        setExpressionState('executing');
        break;
      }

      case 'task_thinking': {
        setExpressionState('thinking');
        setCurrentTask((prev) =>
          prev
            ? {
                ...prev,
                status: 'thinking',
                intent: event.intent || prev.intent,
                explanation: event.explanation || prev.explanation,
              }
            : null
        );
        break;
      }

      case 'task_planned': {
        setCurrentTask((prev) =>
          prev
            ? {
                ...prev,
                intent: event.intent,
                explanation: event.explanation,
                totalSteps: event.total_steps,
              }
            : null
        );
        break;
      }

      case 'task_step_progress': {
        setExpressionState('executing');
        setCurrentTask((prev) => {
          if (!prev) return null;
          const updatedSteps = [...prev.steps];
          const existingIdx = updatedSteps.findIndex(
            (s) => s.step_index === event.step_index
          );
          const stepData: TaskStep = {
            step_index: event.step_index || 1,
            action_name: event.action || 'action',
            explanation: event.explanation || '',
          };
          if (existingIdx >= 0) {
            updatedSteps[existingIdx] = { ...updatedSteps[existingIdx], ...stepData };
          } else {
            updatedSteps.push(stepData);
          }
          return {
            ...prev,
            status: 'executing',
            steps: updatedSteps,
            currentStepIndex: event.step_index,
            totalSteps: event.total_steps || prev.totalSteps,
          };
        });
        break;
      }

      case 'task_step_completed': {
        setCurrentTask((prev) => {
          if (!prev) return null;
          const updatedSteps = prev.steps.map((s) => {
            if (s.step_index === event.step_index) {
              return {
                ...s,
                success: event.success,
                message: event.message,
                output_path: event.output_path,
              };
            }
            return s;
          });
          return { ...prev, steps: updatedSteps };
        });
        break;
      }

      case 'task_finished': {
        const finishedTask: TaskRecord = {
          id: event.task_id || String(now),
          prompt: event.prompt || currentTask?.prompt || '',
          intent: event.intent || currentTask?.intent,
          status: event.success ? 'completed' : 'failed',
          success: event.success,
          explanation: event.explanation,
          steps: (event.steps as TaskStep[]) || currentTask?.steps || [],
          execution_time_ms: event.execution_time_ms,
          timestamp: now,
          error: event.error,
        };

        setCurrentTask(finishedTask);
        setExpressionState(event.success ? 'success' : 'failure');

        // Add to history
        setTaskHistory((prev) => {
          const updated = [finishedTask, ...prev.filter((t) => t.id !== finishedTask.id)];
          saveTaskHistory(updated);
          return updated;
        });

        // Return to idle after celebration
        setTimeout(() => {
          setExpressionState((s) => (s === 'success' || s === 'failure' ? 'idle' : s));
        }, 5500);
        break;
      }

      case 'task_failed': {
        const failedTask: TaskRecord = {
          id: event.task_id || String(now),
          prompt: event.prompt || currentTask?.prompt || '',
          intent: event.intent || currentTask?.intent,
          status: 'failed',
          success: false,
          explanation: event.explanation,
          error: event.error,
          steps: currentTask?.steps || [],
          timestamp: now,
          execution_time_ms: event.execution_time_ms,
        };

        setCurrentTask(failedTask);
        setExpressionState('failure');

        setTaskHistory((prev) => {
          const updated = [failedTask, ...prev.filter((t) => t.id !== failedTask.id)];
          saveTaskHistory(updated);
          return updated;
        });

        setTimeout(() => {
          setExpressionState((s) => (s === 'failure' ? 'idle' : s));
        }, 5000);
        break;
      }

      case 'task_awaiting_confirmation': {
        setCurrentTask((prev) =>
          prev
            ? {
                ...prev,
                status: 'pending',
                intent: event.intent,
                explanation: event.explanation,
                error: 'CONFIRMATION_REQUIRED',
              }
            : null
        );
        setExpressionState('thinking');
        break;
      }
    }
  }, [currentTask]);

  // Setup WebSocket connection and listeners on mount
  useEffect(() => {
    const unsubStatus = agentClient.onStatusChange((status, detail) => {
      setConnectionStatus(status);
      setConnectionDetail(detail || '');
    });

    const unsubEvent = agentClient.onEvent(handleServerEvent);

    // Initial connection attempt if already paired or running on localhost
    const config = agentClient.getConfig();
    const isLocal = config.host === '127.0.0.1' || config.host === 'localhost';
    if (config.token || isLocal) {
      agentClient.connect();
    } else {
      // Prompt user to pair on first visit from remote phone
      setIsPairingOpen(true);
    }

    return () => {
      unsubStatus();
      unsubEvent();
    };
  }, [handleServerEvent]);

  // Send a user prompt (voice or typed)
  const handleSendCommand = (prompt: string, confirmed: boolean = false) => {
    if (connectionStatus !== 'connected') {
      setIsPairingOpen(true);
      return;
    }

    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;

    // Immediate visual feedback on companion screen
    const now = Date.now();
    setCurrentTask({
      id: String(now),
      prompt: cleanPrompt,
      status: 'thinking',
      intent: 'Thinking...',
      explanation: 'Flash is planning your task slowly and carefully...',
      steps: [],
      timestamp: now,
    });
    setExpressionState('thinking');

    agentClient.executeTask(cleanPrompt, confirmed);
  };

  const handleListeningStateChange = (listening: boolean) => {
    if (listening) {
      setExpressionState('listening');
    } else if (expressionState === 'listening') {
      setExpressionState('idle');
    }
  };

  const handleClearHistory = () => {
    clearTaskHistory();
    setTaskHistory([]);
  };

  const handleUnpair = async () => {
    await agentClient.unpair();
    setCurrentTask(null);
    setConnectionStatus('disconnected');
    setExpressionState('disconnected');
    setIsPairingOpen(true);
  };

  const handleToggleGaze = (enabled: boolean) => {
    setGazeEnabled(enabled);
    agentClient.setGazeEnabled(enabled);
  };

  return (
    <div className="app-viewport zootopia-theme">
      {/* Top Header */}
      <Header
        connectionStatus={connectionStatus}
        isEmergencyStopped={isEmergencyStopped}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenPairing={() => setIsPairingOpen(true)}
        onEmergencyStop={() => agentClient.stop()}
        onResume={() => agentClient.resume()}
      />

      {/* Main Companion Screen */}
      <main className="companion-main">
        {/* Flash 3D Sloth Companion & Emotive Expressions */}
        <SlothAvatar
          state={expressionState}
          cursorGaze={cursorGaze}
          gazeEnabled={gazeEnabled}
          subtext={
            connectionStatus !== 'connected'
              ? connectionDetail || 'Not connected to laptop agent'
              : currentTask?.explanation || '⚡ DMV Fastest Sloth'
          }
          onClick={() => {
            if (connectionStatus !== 'connected') {
              setIsPairingOpen(true);
            }
          }}
        />

        {/* Live Task Execution View */}
        <TaskProgress
          task={currentTask}
          onConfirmTask={(prompt) => handleSendCommand(prompt, true)}
        />
      </main>

      {/* Bottom Voice & Text Interaction Area */}
      <footer className="companion-footer">
        <VoiceControl
          disabled={connectionStatus !== 'connected' || isEmergencyStopped}
          onSendCommand={(p) => handleSendCommand(p, false)}
          onListeningStateChange={handleListeningStateChange}
        />

        {/* History drawer trigger button */}
        <div className="bottom-bar-actions">
          <button
            className="btn-history-pill"
            onClick={() => setIsHistoryOpen(true)}
            title="Open task history"
          >
            <History size={16} />
            <span>History ({taskHistory.length})</span>
          </button>
        </div>
      </footer>

      {/* Pairing Modal */}
      <PairingModal
        isOpen={isPairingOpen}
        onClose={() => setIsPairingOpen(false)}
        onPairSuccess={() => agentClient.connect()}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        gazeEnabled={gazeEnabled}
        onToggleGaze={handleToggleGaze}
        onClose={() => setIsSettingsOpen(false)}
        onClearHistory={handleClearHistory}
        onUnpair={handleUnpair}
        onReconnect={() => agentClient.connect()}
      />

      {/* Task History Modal */}
      <TaskHistory
        tasks={taskHistory}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onClearHistory={handleClearHistory}
        onSelectTask={(t) => setCurrentTask(t)}
      />
    </div>
  );
};

export default App;
