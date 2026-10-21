import React, { useState, useEffect, useCallback, useRef } from 'react';
import { History } from 'lucide-react';
import { Header } from './components/Header';
import { SlothAvatar } from './components/SlothAvatar';
import { VoiceControl } from './components/VoiceControl';
import { TaskProgress } from './components/TaskProgress';
import { TaskHistory } from './components/TaskHistory';
import { PairingModal } from './components/PairingModal';
import { SettingsModal } from './components/SettingsModal';
import { AboutModal } from './components/AboutModal';
import { NotepadModal } from './components/NotepadModal';
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
  const [expressionState, setExpressionState] = useState<CompanionExpressionState>('idle');
  const [isEmergencyStopped, setIsEmergencyStopped] = useState(false);

  // Milestone 4: Cursor Gaze State (centered by default)
  const [cursorGaze, setCursorGaze] = useState<CursorGazeCoordinates | null>({ x: 0.5, y: 0.5 });
  const [gazeEnabled, setGazeEnabled] = useState<boolean>(true);

  const [currentTask, setCurrentTask] = useState<TaskRecord | null>(null);
  const [taskHistory, setTaskHistory] = useState<TaskRecord[]>([]);

  const [isPairingOpen, setIsPairingOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isNotepadOpen, setIsNotepadOpen] = useState(false);
  const [notepadText, setNotepadText] = useState('');

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

  // Update expression state based on emergency stop
  useEffect(() => {
    if (isEmergencyStopped) {
      setExpressionState('stopped');
    } else if (expressionState === 'stopped') {
      setExpressionState('idle');
    }
  }, [isEmergencyStopped]);

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
    }

    return () => {
      unsubStatus();
      unsubEvent();
    };
  }, [handleServerEvent]);

  // Voice & Web Demo Helper Functions
  const speakSlothText = (text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.72; // Deliberate sloth pacing
        utterance.pitch = 0.85; // Warm, deeper pitch
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        console.warn('Speech synthesis not allowed or supported', e);
      }
    }
  };

  const openNewTab = (url: string): boolean => {
    try {
      const w = window.open(url, '_blank', 'noopener,noreferrer');
      return !!w;
    } catch (e) {
      console.warn('Failed to open tab', e);
      return false;
    }
  };

  const downloadCsvSpreadsheet = (filename = 'Flash_Budget_Worksheet.csv') => {
    const csvContent =
      'Date,Category,Description,Amount,Status\n' +
      '2026-10-21,Groceries,Carrots & Pawpsicles,15.50,Completed\n' +
      '2026-10-21,Office,DMV Ink & Printer Paper,42.00,Completed\n' +
      '2026-10-21,Coffee,Triple Espresso for Officer Judy,8.75,Pending\n' +
      '2026-10-21,Transit,Express Train to Zootopia Center,12.00,Completed\n' +
      '2026-10-21,Sloth Care,Tree Branch Cushion,29.99,Completed\n';

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const downloadGroceryList = (filename = 'Flash_Grocery_List.md') => {
    const content =
      '# 🛒 Flash Grocery Checklist\n\n' +
      '- [x] Organic Carrots (for Judy)\n' +
      '- [x] Jumbo Pawpsicles (for Nick)\n' +
      '- [ ] Espresso beans (triple roast)\n' +
      '- [ ] Whole Milk & Fresh Bread\n' +
      '- [ ] Blueberries & Honey\n';

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Send a user prompt (voice or typed)
  const handleSendCommand = (prompt: string, confirmed: boolean = false) => {
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;

    const now = Date.now();

    // 1. Interactive Web Demo Mode when not paired with a Windows PC
    if (connectionStatus !== 'connected') {
      setCurrentTask({
        id: String(now),
        prompt: cleanPrompt,
        status: 'thinking',
        intent: 'Flash is thinking...',
        explanation: 'Flash is planning your task slowly and carefully...',
        steps: [],
        timestamp: now,
      });
      setExpressionState('thinking');

      setTimeout(() => {
        let intent = 'Interactive Web Demo';
        let explanation = 'Executed in Flash Web Demo mode.';
        let actionName = 'open_application';
        let message = `Flash received '${cleanPrompt}'.`;
        let outputPath: string | undefined = undefined;

        const p = cleanPrompt.toLowerCase();

        // 1. Browser & Web Search automation
        if (
          p.includes('browser') ||
          p.includes('google') ||
          p.includes('chrome') ||
          p.includes('search') ||
          p.includes('find') ||
          p.includes('look up') ||
          p.includes('github') ||
          p.includes('dev.to') ||
          p.includes('dev to') ||
          p.includes('youtube')
        ) {
          actionName = 'open_browser_search';
          let targetUrl = 'https://www.google.com';
          let searchTopic = '';

          if (p.includes('github')) {
            targetUrl = 'https://github.com/SK-Sathyavada-008/flash';
            searchTopic = 'Flash GitHub Repository';
            intent = 'Open GitHub Repository';
            explanation = 'Opening Flash GitHub repository in a new browser tab...';
          } else if (p.includes('dev.to') || p.includes('dev to')) {
            targetUrl = 'https://dev.to';
            searchTopic = 'DEV Community';
            intent = 'Open DEV.to';
            explanation = 'Navigating to DEV Community in a new browser tab...';
          } else if (p.includes('youtube')) {
            const rawQ = cleanPrompt.replace(/.*(?:youtube|search for|search|find)\s*/i, '').trim();
            targetUrl = rawQ
              ? `https://www.youtube.com/results?search_query=${encodeURIComponent(rawQ)}`
              : 'https://www.youtube.com';
            searchTopic = rawQ ? `YouTube: ${rawQ}` : 'YouTube';
            intent = `Search YouTube for "${rawQ || 'trending'}"`;
            explanation = `Opening YouTube search for "${rawQ || 'trending'}"...`;
          } else if (
            p.includes('search') ||
            p.includes('google') ||
            p.includes('look up') ||
            p.includes('find')
          ) {
            const rawQ = cleanPrompt
              .replace(/.*(?:search for|search|google for|google|find|look up)\s*/i, '')
              .trim();
            const query = rawQ || 'Hacktoberfest 2026 Open Source AI Challenge';
            targetUrl = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
            searchTopic = query;
            intent = `Search the Web for "${query}"`;
            explanation = `Opening a new browser tab to search for "${query}"... slowly but surely!`;
          } else {
            targetUrl = 'https://www.google.com';
            searchTopic = 'Google Search';
            intent = 'Open Web Browser';
            explanation = 'Launching a new browser tab to https://www.google.com...';
          }

          outputPath = targetUrl;
          openNewTab(targetUrl);
          speakSlothText(searchTopic ? `Searching the web for ${searchTopic}` : 'Opening browser tab for you.');
          message = `Successfully opened new tab: ${targetUrl}. (If popup was blocked by your browser, click the link above!)`;
        }
        // 2. Windows Notepad & Note typing simulation
        else if (
          p.includes('notepad') ||
          p.includes('note') ||
          p.includes('memo') ||
          p.includes('type')
        ) {
          intent = 'Launch Notepad & Type Note';
          actionName = 'open_notepad';
          explanation = 'Launching Notepad on your screen and typing your memo character by character...';

          let noteBody =
            'Zootopia DMV Memo #402\n' +
            'Date: October 21, 2026\n' +
            'From: Flash Slothmore\n' +
            'To: Officer Judy Hopps & Nick Wilde\n\n' +
            'Subject: Desktop Automation & Hacktoberfest\n\n' +
            'Slow and steady wins the race. All requests are processed with deliberate care. ' +
            'Please enjoy a pawpsicle while waiting.\n\n' +
            '— Flash 🦥';

          const noteMatch = cleanPrompt.match(
            /(?:notepad|note|write|type)\s+(?:that|about|saying)?\s*[:"-]?\s*(.+)/i
          );
          if (noteMatch && noteMatch[1] && noteMatch[1].length > 3) {
            noteBody = `Note from Flash:\n\n${noteMatch[1].trim()}\n\n— Typed by Flash Desktop Companion`;
          }

          setNotepadText(noteBody);
          setIsNotepadOpen(true);
          speakSlothText('Opening Notepad on your screen and typing your memo.');
          message = 'Launched Flash Interactive Notepad modal and typed memo character-by-character.';
        }
        // 3. Excel Spreadsheet generation & download
        else if (
          p.includes('excel') ||
          p.includes('spreadsheet') ||
          p.includes('sheet') ||
          p.includes('budget') ||
          p.includes('csv')
        ) {
          intent = 'Generate Excel Spreadsheet';
          actionName = 'create_spreadsheet';
          explanation = 'Building formatted spreadsheet (Flash_Budget_Worksheet.csv)...';
          outputPath = 'Flash_Budget_Worksheet.csv';
          downloadCsvSpreadsheet();
          speakSlothText('Building your Excel spreadsheet. Downloading file now.');
          message = 'Generated and downloaded workbook (Flash_Budget_Worksheet.csv) with Date, Category, Description, and Amount columns.';
        }
        // 4. Grocery Checklist generation & download
        else if (
          p.includes('grocery') ||
          p.includes('shopping') ||
          p.includes('checklist') ||
          p.includes('market')
        ) {
          intent = 'Create Grocery Checklist';
          actionName = 'create_grocery_list';
          explanation = 'Created your grocery checklist with Carrots, Pawpsicles, and Espresso.';
          outputPath = 'Flash_Grocery_List.md';
          downloadGroceryList();
          speakSlothText('Created your grocery checklist with carrots and pawpsicles.');
          message = 'Generated and downloaded grocery checklist (Flash_Grocery_List.md).';
        }
        // 5. Sloth Jokes
        else if (p.includes('joke') || p.includes('laugh')) {
          intent = 'Tell Sloth Joke';
          actionName = 'speak_text';
          explanation = 'What... do... you... call... a... three-humped... camel? ...... Pregnant!';
          speakSlothText('What... do... you... call... a... three-humped... camel? ...... Pregnant!');
          message = 'What... do... you... call... a... three-humped... camel? ...... Pregnant!';
        }
        // 6. Introductions & Help
        else {
          intent = 'Introduce Flash Desktop Companion';
          actionName = 'speak_text';
          explanation =
            'I am Flash, the fastest sloth at the DMV! Try asking me to search the web, generate an Excel sheet, or open Notepad.';
          speakSlothText(
            'I am Flash, the fastest sloth at the DMV. Try asking me to search the web, create an excel sheet, or open notepad!'
          );
          message =
            "I can search the web, download spreadsheets, open Notepad, manage grocery lists, and pair with your Windows desktop for full OS automation!";
        }

        const taskRecord: TaskRecord = {
          id: String(now),
          prompt: cleanPrompt,
          intent,
          status: 'completed',
          success: true,
          explanation,
          steps: [
            {
              step_index: 1,
              action_name: actionName,
              explanation,
              success: true,
              message,
              output_path: outputPath,
            },
          ],
          execution_time_ms: 450,
          timestamp: now,
        };

        setCurrentTask(taskRecord);
        setExpressionState('success');
        setTaskHistory((prev) => [taskRecord, ...prev.slice(0, 20)]);

        setTimeout(() => {
          setExpressionState('idle');
        }, 5000);
      }, 700);

      return;
    }

    // 2. Connected to local Windows laptop: stream over WebSocket
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
    setExpressionState('idle');
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
        onOpenAbout={() => setIsAboutOpen(true)}
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
            connectionStatus === 'connected'
              ? currentTask?.explanation || '⚡ DMV Fastest Sloth (Connected to PC)'
              : currentTask?.explanation || '⚡ DMV Fastest Sloth (Interactive Web Demo)'
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
          disabled={isEmergencyStopped}
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

      {/* About & Security Boundary Modal */}
      <AboutModal
        isOpen={isAboutOpen}
        onClose={() => setIsAboutOpen(false)}
        onOpenPairing={() => setIsPairingOpen(true)}
      />

      {/* Task History Modal */}
      <TaskHistory
        tasks={taskHistory}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onClearHistory={handleClearHistory}
        onSelectTask={(t) => setCurrentTask(t)}
      />

      {/* Notepad Simulator Modal */}
      <NotepadModal
        isOpen={isNotepadOpen}
        onClose={() => setIsNotepadOpen(false)}
        initialText={notepadText}
      />
    </div>
  );
};

export default App;
