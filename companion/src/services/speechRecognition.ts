// Speech Recognition Service with Web Speech API and Extensible Backend Architecture

export interface SpeechCallbacks {
  onTranscript: (text: string, isFinal: boolean) => void;
  onError: (error: string) => void;
  onStateChange: (listening: boolean) => void;
}

export interface SpeechProvider {
  name: string;
  isSupported: () => boolean;
  start: (callbacks: SpeechCallbacks) => void;
  stop: () => void;
  abort: () => void;
}

/**
 * Standard Web Speech API provider (supported on Android Chrome, Edge, etc.)
 */
class BrowserSpeechProvider implements SpeechProvider {
  name = 'WebSpeechAPI';
  private recognition: any = null;
  private isListening = false;

  isSupported(): boolean {
    if (typeof window === 'undefined') return false;
    return !!(
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition
    );
  }

  start(callbacks: SpeechCallbacks): void {
    if (!this.isSupported()) {
      callbacks.onError('Web Speech API is not supported in this browser. Please use text input.');
      return;
    }

    try {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onstart = () => {
        this.isListening = true;
        callbacks.onStateChange(true);
      };

      this.recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item.isFinal) {
            finalTranscript += item[0].transcript;
          } else {
            interimTranscript += item[0].transcript;
          }
        }

        const text = (finalTranscript || interimTranscript).trim();
        if (text) {
          callbacks.onTranscript(text, !!finalTranscript);
        }
      };

      this.recognition.onerror = (event: any) => {
        const errType = event.error || 'speech_error';
        let userMessage = 'Microphone error: ' + errType;
        if (errType === 'not-allowed') {
          userMessage = 'Microphone permission was denied. Please allow microphone access in Android settings.';
        } else if (errType === 'no-speech') {
          userMessage = 'No speech detected. Please speak louder or closer to the phone.';
        }
        callbacks.onError(userMessage);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        callbacks.onStateChange(false);
      };

      this.recognition.start();
    } catch (err: any) {
      this.isListening = false;
      callbacks.onStateChange(false);
      callbacks.onError('Could not start microphone: ' + (err.message || String(err)));
    }
  }

  stop(): void {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch {}
    }
    this.isListening = false;
  }

  abort(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {}
    }
    this.isListening = false;
  }
}

/**
 * Placeholder for future backend transcription (Whisper / ElevenLabs)
 * Captures raw audio for server-side processing when configured.
 */
class RemoteAudioProvider implements SpeechProvider {
  name = 'RemoteTranscription';
  isSupported(): boolean {
    return false; // Can be toggled on when ElevenLabs/Whisper backend is configured
  }
  start(callbacks: SpeechCallbacks): void {
    callbacks.onError('Remote audio transcription is not configured in this milestone.');
  }
  stop(): void {}
  abort(): void {}
}

export class SpeechManager {
  private activeProvider: SpeechProvider;

  constructor() {
    this.activeProvider = new BrowserSpeechProvider();
  }

  public isSupported(): boolean {
    return this.activeProvider.isSupported();
  }

  public getProviderName(): string {
    return this.activeProvider.name;
  }

  public startListening(callbacks: SpeechCallbacks): void {
    this.activeProvider.start(callbacks);
  }

  public stopListening(): void {
    this.activeProvider.stop();
  }

  public abortListening(): void {
    this.activeProvider.abort();
  }

  public setProvider(provider: SpeechProvider): void {
    this.activeProvider = provider;
  }
}

export const speechManager = new SpeechManager();
