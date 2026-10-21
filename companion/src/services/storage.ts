// Persistent Local Storage for Companion Configuration & Task History
import { ConnectionConfig, TaskRecord } from '../types';

const STORAGE_KEYS = {
  CONFIG: 'flash_companion_config',
  TASKS: 'flash_companion_tasks',
  AUDIO_ENABLED: 'flash_companion_audio',
};

const DEFAULT_CONFIG: ConnectionConfig = {
  // If companion is opened on http://192.168.1.15:5173, use that same IP for the agent backend
  host: typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : '127.0.0.1',
  port: 8765,
  token: null,
  deviceName: 'Redmi Android',
};

export const loadConnectionConfig = (): ConnectionConfig => {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.CONFIG);
    if (raw) {
      const parsed = JSON.parse(raw);
      const config = { ...DEFAULT_CONFIG, ...parsed };
      // When opened on a phone (e.g. http://192.168.x.x:5173), ensure the backend host targets the laptop IP, not phone's loopback
      if (
        typeof window !== 'undefined' &&
        window.location.hostname &&
        window.location.hostname !== 'localhost' &&
        window.location.hostname !== '127.0.0.1'
      ) {
        if (!config.host || config.host === '127.0.0.1' || config.host === 'localhost') {
          config.host = window.location.hostname;
        }
      }
      return config;
    }
  } catch (err) {
    console.warn('Failed to read config from localStorage', err);
  }
  return DEFAULT_CONFIG;
};

export const saveConnectionConfig = (config: ConnectionConfig): void => {
  try {
    localStorage.setItem(STORAGE_KEYS.CONFIG, JSON.stringify(config));
  } catch (err) {
    console.error('Failed to save config to localStorage', err);
  }
};

export const clearAuthToken = (): void => {
  const current = loadConnectionConfig();
  current.token = null;
  saveConnectionConfig(current);
};

export const loadTaskHistory = (): TaskRecord[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.TASKS);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (err) {
    console.warn('Failed to read task history from localStorage', err);
  }
  return [];
};

export const saveTaskHistory = (tasks: TaskRecord[]): void => {
  try {
    // Keep at most 30 recent tasks
    const trimmed = tasks.slice(0, 30);
    localStorage.setItem(STORAGE_KEYS.TASKS, JSON.stringify(trimmed));
  } catch (err) {
    console.error('Failed to save task history', err);
  }
};

export const clearTaskHistory = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEYS.TASKS);
  } catch (err) {
    console.error('Failed to clear task history', err);
  }
};
