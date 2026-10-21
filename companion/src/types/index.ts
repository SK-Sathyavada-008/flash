// Frontend Type Definitions for Flash Phone Companion

export type CompanionExpressionState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'executing'
  | 'success'
  | 'failure'
  | 'stopped'
  | 'disconnected';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

export interface TaskStep {
  step_index: number;
  action_name: string;
  explanation: string;
  success?: boolean;
  message?: string;
  output_path?: string;
  data?: Record<string, any>;
  execution_time_ms?: number;
}

export interface TaskRecord {
  id: string;
  prompt: string;
  intent?: string;
  status: 'pending' | 'thinking' | 'executing' | 'completed' | 'failed' | 'stopped';
  success?: boolean;
  explanation?: string;
  steps: TaskStep[];
  currentStepIndex?: number;
  totalSteps?: number;
  execution_time_ms?: number;
  timestamp: number;
  error?: string;
}

export interface ConnectionConfig {
  host: string;
  port: number;
  token: string | null;
  deviceName: string;
  gazeEnabled?: boolean;
}

export interface PairingCodeInfo {
  code: string;
  expires_in_seconds: number;
  expires_at: number;
}

export interface CursorGazeCoordinates {
  x: number; // 0.0 (left) to 1.0 (right)
  y: number; // 0.0 (top) to 1.0 (bottom)
}

export interface ServerWebSocketEvent {
  type: string;
  agent_name?: string;
  version?: string;
  status?: string;
  emergency_stop_active?: boolean;
  task_id?: string;
  prompt?: string;
  intent?: string;
  explanation?: string;
  total_steps?: number;
  step_index?: number;
  action?: string;
  success?: boolean;
  message?: string;
  output_path?: string;
  steps?: TaskStep[];
  execution_time_ms?: number;
  error?: string;
  code?: string;
  timestamp?: number;
  server_timestamp?: number;
  // Cursor gaze updates
  x?: number;
  y?: number;
  enabled?: boolean;
}

