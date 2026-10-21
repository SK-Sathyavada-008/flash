// Authenticated WebSocket Client for Flash Desktop Agent
import {
  ConnectionConfig,
  ConnectionStatus,
  PairingCodeInfo,
  ServerWebSocketEvent,
} from '../types';
import { loadConnectionConfig, saveConnectionConfig } from './storage';

export type EventCallback = (event: ServerWebSocketEvent) => void;
export type StatusCallback = (status: ConnectionStatus, detail?: string) => void;

export class AgentClient {
  private config: ConnectionConfig;
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = 'disconnected';
  private eventListeners: Set<EventCallback> = new Set();
  private statusListeners: Set<StatusCallback> = new Set();

  private heartbeatInterval: any = null;
  private reconnectTimeout: any = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private isExplicitlyClosed = false;

  constructor() {
    this.config = loadConnectionConfig();
  }

  public getConfig(): ConnectionConfig {
    return { ...this.config };
  }

  public updateConfig(newConfig: Partial<ConnectionConfig>): void {
    this.config = { ...this.config, ...newConfig };
    saveConnectionConfig(this.config);
  }

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  public onEvent(callback: EventCallback): () => void {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  public onStatusChange(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => this.statusListeners.delete(callback);
  }

  private notifyStatus(status: ConnectionStatus, detail?: string): void {
    this.status = status;
    for (const listener of this.statusListeners) {
      try {
        listener(status, detail);
      } catch (e) {
        console.error('Error in status listener', e);
      }
    }
  }

  private notifyEvent(event: ServerWebSocketEvent): void {
    for (const listener of this.eventListeners) {
      try {
        listener(event);
      } catch (e) {
        console.error('Error in event listener', e);
      }
    }
  }

  /**
   * Fetch active pairing code from agent host (when accessed from same machine or companion pairing screen)
   */
  public async fetchPairingCode(host?: string, port?: number): Promise<PairingCodeInfo> {
    const targetHost = host || this.config.host;
    const targetPort = port || this.config.port;
    const url = `http://${targetHost}:${targetPort}/api/v1/auth/pair-code`;

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to fetch pairing code (HTTP ${res.status})`);
    }

    return await res.json();
  }

  /**
   * Pair with the desktop agent using a 6-digit code to acquire a permanent bearer token.
   */
  public async pair(code: string, host?: string, port?: number, deviceName?: string): Promise<string> {
    const targetHost = host || this.config.host;
    const targetPort = port || this.config.port;
    const targetDevice = deviceName || this.config.deviceName;

    const url = `http://${targetHost}:${targetPort}/api/v1/auth/pair`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: code.trim(),
        device_name: targetDevice,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Pairing failed (HTTP ${res.status})`);
    }

    const data = await res.json();
    const token = data.token;

    // Update and persist config
    this.updateConfig({
      host: targetHost,
      port: targetPort,
      token,
      deviceName: targetDevice,
    });

    return token;
  }

  /**
   * Revoke current token and unpair device.
   */
  public async unpair(): Promise<void> {
    if (this.config.token) {
      try {
        const url = `http://${this.config.host}:${this.config.port}/api/v1/auth/revoke`;
        await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: this.config.token }),
        });
      } catch (e) {
        console.warn('Could not notify server of token revocation', e);
      }
    }
    this.disconnect();
    this.updateConfig({ token: null });
  }

  /**
   * Connect WebSocket to the agent.
   */
  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const isLocal = this.config.host === '127.0.0.1' || this.config.host === 'localhost';
    if (!this.config.token && !isLocal) {
      this.notifyStatus('disconnected', 'Device is not paired. Please enter pairing code.');
      return;
    }

    this.isExplicitlyClosed = false;
    this.notifyStatus('connecting', `Connecting to ${this.config.host}:${this.config.port}...`);

    try {
      const tokenParam = this.config.token ? `?token=${encodeURIComponent(this.config.token)}` : '';
      const wsUrl = `ws://${this.config.host}:${this.config.port}/ws/v1/companion${tokenParam}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.notifyStatus('connected');
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: ServerWebSocketEvent = JSON.parse(event.data);
          this.notifyEvent(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      this.ws.onerror = (err) => {
        console.error('WebSocket connection error', err);
        this.notifyStatus('error', 'Connection error. Check Wi-Fi and agent IP.');
      };

      this.ws.onclose = (event) => {
        this.stopHeartbeat();
        this.ws = null;

        if (event.code === 4401) {
          this.updateConfig({ token: null });
          this.notifyStatus('disconnected', 'Token expired or unauthorized. Please re-pair.');
          return;
        }

        if (!this.isExplicitlyClosed) {
          this.notifyStatus('disconnected', 'Disconnected from agent.');
          this.scheduleReconnect();
        } else {
          this.notifyStatus('disconnected');
        }
      };
    } catch (err: any) {
      this.notifyStatus('error', err.message || 'Failed to initiate WebSocket');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.notifyStatus('disconnected');
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping', timestamp: Date.now() });
      }
    }, 10000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.isExplicitlyClosed || !this.config.token) return;

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.notifyStatus('error', 'Could not reconnect after multiple attempts. Check agent status.');
      return;
    }

    const backoffMs = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 10000);
    this.reconnectAttempts++;

    this.reconnectTimeout = setTimeout(() => {
      if (!this.isExplicitlyClosed && this.config.token) {
        this.connect();
      }
    }, backoffMs);
  }

  public send(payload: Record<string, any>): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send: WebSocket is not open', payload);
      return false;
    }
    try {
      this.ws.send(JSON.stringify(payload));
      return true;
    } catch (err) {
      console.error('Failed to send WebSocket message', err);
      return false;
    }
  }

  public executeTask(prompt: string, confirmed: boolean = false): boolean {
    return this.send({
      type: 'execute_task',
      prompt: prompt.trim(),
      confirmed,
      timestamp: Date.now(),
    });
  }

  public stop(): boolean {
    return this.send({ type: 'stop' });
  }

  public resume(): boolean {
    return this.send({ type: 'resume' });
  }

  public refreshStatus(): boolean {
    return this.send({ type: 'get_status' });
  }

  public setGazeEnabled(enabled: boolean): boolean {
    this.updateConfig({ gazeEnabled: enabled });
    return this.send({
      type: 'set_gaze_enabled',
      enabled,
      timestamp: Date.now(),
    });
  }
}

export const agentClient = new AgentClient();

