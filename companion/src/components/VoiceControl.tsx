import React, { useState, useEffect, useRef } from 'react';
import { Keyboard, Mic, MicOff, Send, X } from 'lucide-react';
import { speechManager } from '../services/speechRecognition';

interface VoiceControlProps {
  disabled: boolean;
  onSendCommand: (prompt: string) => void;
  onListeningStateChange: (listening: boolean) => void;
}

export const VoiceControl: React.FC<VoiceControlProps> = ({
  disabled,
  onSendCommand,
  onListeningStateChange,
}) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isSpeechSupported, setIsSpeechSupported] = useState(true);

  const touchStartTimeRef = useRef<number>(0);
  const wasHoldingRef = useRef<boolean>(false);

  useEffect(() => {
    setIsSpeechSupported(speechManager.isSupported());
  }, []);

  const handleStartListening = () => {
    if (disabled) return;
    setSpeechError(null);
    setTranscript('');

    if (!isSpeechSupported) {
      setSpeechError('Speech recognition is not supported in this browser. Please use text input.');
      setShowTextInput(true);
      return;
    }

    speechManager.startListening({
      onTranscript: (text, _isFinal) => {
        setTranscript(text);
      },
      onError: (err) => {
        setSpeechError(err);
        setIsListening(false);
        onListeningStateChange(false);
      },
      onStateChange: (listening) => {
        setIsListening(listening);
        onListeningStateChange(listening);
      },
    });
  };

  const handleStopListening = () => {
    speechManager.stopListening();
    setIsListening(false);
    onListeningStateChange(false);

    // If we captured spoken text, submit it!
    const finalPrompt = transcript.trim();
    if (finalPrompt.length > 0) {
      onSendCommand(finalPrompt);
      setTranscript('');
    }
  };

  const handleToggleListening = () => {
    if (isListening) {
      handleStopListening();
    } else {
      handleStartListening();
    }
  };

  const handleTouchStart = () => {
    touchStartTimeRef.current = Date.now();
    wasHoldingRef.current = false;
    if (!isListening) {
      handleStartListening();
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const duration = Date.now() - touchStartTimeRef.current;
    if (duration > 400) {
      // Long press / push-to-talk
      wasHoldingRef.current = true;
      e.preventDefault();
      handleStopListening();
    }
  };

  const handleClick = () => {
    if (wasHoldingRef.current) {
      wasHoldingRef.current = false;
      return;
    }
    handleToggleListening();
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = textInput.trim();
    if (clean && !disabled) {
      onSendCommand(clean);
      setTextInput('');
      setTranscript('');
    }
  };

  return (
    <div className="voice-control-container">
      {/* Transcript / Spoken Preview Area */}
      {transcript && (
        <div className="transcript-bubble">
          <span className="transcript-label">Heard:</span>
          <p className="transcript-text">"{transcript}"</p>
        </div>
      )}

      {/* Speech error alert */}
      {speechError && (
        <div className="speech-error-alert" role="alert">
          <span>{speechError}</span>
          <button
            onClick={() => setSpeechError(null)}
            className="btn-dismiss-error"
            title="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Interaction Controls */}
      <div className="controls-row">
        {/* Toggle Text Input Fallback Button */}
        <button
          type="button"
          className={`btn-fallback-toggle ${showTextInput ? 'active' : ''}`}
          onClick={() => setShowTextInput(!showTextInput)}
          title={showTextInput ? 'Hide text keyboard' : 'Type command manually'}
          aria-label="Toggle text keyboard"
        >
          <Keyboard size={22} />
        </button>

        {/* Primary Push-to-Talk Mic Button */}
        <div className="mic-button-wrapper">
          {isListening && <div className="pulse-ring"></div>}
          <button
            type="button"
            className={`btn-push-to-talk ${isListening ? 'listening' : ''} ${
              disabled ? 'disabled' : ''
            }`}
            disabled={disabled}
            onClick={handleClick}
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            title={
              disabled
                ? 'Connect companion first'
                : isListening
                ? 'Tap or release to send'
                : 'Hold or tap to speak'
            }
            aria-label={isListening ? 'Listening. Tap to send.' : 'Push to talk'}
          >
            {isListening ? (
              <Mic size={36} className="mic-icon active-mic" />
            ) : isSpeechSupported ? (
              <Mic size={36} className="mic-icon" />
            ) : (
              <MicOff size={36} className="mic-icon unsupported" />
            )}
          </button>
        </div>

        {/* Quick Send or Status spacer */}
        <div className="controls-spacer">
          {isListening && (
            <button
              className="btn-quick-send"
              onClick={handleStopListening}
              title="Send spoken command now"
            >
              <Send size={18} />
            </button>
          )}
        </div>
      </div>

      <div className="ptt-hint">
        {isListening ? (
          <span className="text-listening">Listening... Tap or release when done</span>
        ) : isSpeechSupported ? (
          <span>Tap mic to speak to Flash</span>
        ) : (
          <span>Tap keyboard below to type commands</span>
        )}
      </div>

      {/* Text Input Fallback Drawer */}
      {showTextInput && (
        <form className="text-fallback-drawer" onSubmit={handleTextSubmit}>
          <input
            type="text"
            className="text-input-field"
            placeholder="E.g. Make a grocery list with milk..."
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            disabled={disabled}
            autoFocus
          />
          <button
            type="submit"
            className="btn-send-text"
            disabled={disabled || !textInput.trim()}
            title="Send command"
          >
            <Send size={18} />
          </button>
        </form>
      )}
    </div>
  );
};
