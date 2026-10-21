import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { SlothAvatar } from '../components/SlothAvatar';
import { Header } from '../components/Header';
import { VoiceControl } from '../components/VoiceControl';
import { TaskProgress } from '../components/TaskProgress';
import { PairingModal } from '../components/PairingModal';
import { SettingsModal } from '../components/SettingsModal';
import { TaskRecord } from '../types';

describe('SlothAvatar Component', () => {
  it('renders idle state with correct accessible label and subtext', () => {
    render(<SlothAvatar state="idle" subtext="Ready for command" />);
    expect(screen.getByRole('region')).toHaveAttribute(
      'aria-label',
      'Flash companion avatar: idle'
    );
    expect(screen.getByText('Flash is ready')).toBeInTheDocument();
    expect(screen.getByText('Ready for command')).toBeInTheDocument();
  });

  it('syncs 2D Flash eyes with mouse pointer coordinates from laptop', () => {
    const { container, rerender } = render(
      <SlothAvatar
        state="idle"
        cursorGaze={{ x: 1.0, y: 1.0 }} // Mouse pointer at bottom-right of laptop
        gazeEnabled={true}
      />
    );

    // Left and right eye gaze groups rendered with live pupil offset
    const leftEye = container.querySelector('[data-testid="left-eye-gaze"]');
    const rightEye = container.querySelector('[data-testid="right-eye-gaze"]');
    expect(leftEye).toBeInTheDocument();
    expect(rightEye).toBeInTheDocument();

    // Pupil assembly translated based on mouse coordinates (1.0 -> gazeX = 1.0, pupilDx = +9.5px, pupilDy = +6px)
    const leftAssembly = container.querySelector('[data-testid="left-pupil-assembly"]');
    expect(leftAssembly).toHaveStyle({ transform: 'translate(9.5px, 6px)' });

    // Move mouse pointer to top-left (0.0, 0.0 -> gazeX = -1.0, pupilDx = -9.5px, pupilDy = -6px)
    rerender(
      <SlothAvatar
        state="idle"
        cursorGaze={{ x: 0.0, y: 0.0 }}
        gazeEnabled={true}
      />
    );
    expect(leftAssembly).toHaveStyle({ transform: 'translate(-9.5px, -6px)' });
    expect(leftAssembly).toHaveAttribute('transform', 'translate(-9.5, -6)');
  });

  it('wakes up eyes and syncs gaze even in disconnected state when cursor moves', () => {
    const { container } = render(
      <SlothAvatar
        state="disconnected"
        cursorGaze={{ x: 0.8, y: 0.2 }}
        gazeEnabled={true}
      />
    );

    // Eyes must be open and tracking, not asleep
    const leftEye = container.querySelector('[data-testid="left-eye-gaze"]');
    expect(leftEye).toBeInTheDocument();
    expect(container.querySelector('.sleepy-zzz')).not.toBeInTheDocument();

    const leftAssembly = container.querySelector('[data-testid="left-pupil-assembly"]');
    expect(leftAssembly).toBeInTheDocument();
  });


  it('renders listening and executing state indicators', () => {
    const { rerender } = render(<SlothAvatar state="listening" />);
    expect(screen.getByText('Listening...')).toBeInTheDocument();

    rerender(<SlothAvatar state="thinking" />);
    expect(screen.getByText('Flash is thinking...')).toBeInTheDocument();

    rerender(<SlothAvatar state="executing" />);
    expect(screen.getByText('Working...')).toBeInTheDocument();

    rerender(<SlothAvatar state="stopped" />);
    expect(screen.getByText('Emergency Stopped')).toBeInTheDocument();
  });

  it('renders 2D Zootopia Flash with cursor gaze coordinates and success laughing state', () => {
    const { container, rerender } = render(
      <SlothAvatar
        state="idle"
        cursorGaze={{ x: 0.75, y: 0.25 }}
        gazeEnabled={true}
        subtext="⚡ DMV Fastest Sloth"
      />
    );

    // Assert that the unwanted text is not present
    expect(screen.queryByText(/Syncing gaze with laptop mouse/i)).not.toBeInTheDocument();
    expect(screen.getByText('⚡ DMV Fastest Sloth')).toBeInTheDocument();

    // Verify SVG is rendered with DMV elements (Polo, Tie, Desk)
    const svg = container.querySelector('svg.sloth-svg');
    expect(svg).toBeInTheDocument();
    expect(container.querySelector('#dmvPolo')).toBeInTheDocument();
    expect(container.querySelector('#dmvDesk')).toBeInTheDocument();

    // Switch to success state: renders the iconic Zootopia open-mouth laugh
    rerender(
      <SlothAvatar
        state="success"
        cursorGaze={{ x: 0.5, y: 0.5 }}
      />
    );
    expect(container.querySelector('.flash-laugh-mouth')).toBeInTheDocument();
  });
});

describe('Header Component', () => {
  it('triggers emergency stop callback when STOP is clicked', () => {
    const onStop = vi.fn();
    const onResume = vi.fn();
    render(
      <Header
        connectionStatus="connected"
        isEmergencyStopped={false}
        onOpenSettings={vi.fn()}
        onOpenPairing={vi.fn()}
        onEmergencyStop={onStop}
        onResume={onResume}
      />
    );

    const stopBtn = screen.getByTitle('Emergency Stop: Halt agent immediately');
    fireEvent.click(stopBtn);
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it('shows Resume button when emergency stop is active', () => {
    const onResume = vi.fn();
    render(
      <Header
        connectionStatus="connected"
        isEmergencyStopped={true}
        onOpenSettings={vi.fn()}
        onOpenPairing={vi.fn()}
        onEmergencyStop={vi.fn()}
        onResume={onResume}
      />
    );

    const resumeBtn = screen.getByText('Resume');
    fireEvent.click(resumeBtn);
    expect(onResume).toHaveBeenCalledTimes(1);
  });
});

describe('VoiceControl Component', () => {
  it('renders push to talk button and allows typing fallback', () => {
    const onSend = vi.fn();
    render(
      <VoiceControl
        disabled={false}
        onSendCommand={onSend}
        onListeningStateChange={vi.fn()}
      />
    );

    // Toggle keyboard
    const keyboardBtn = screen.getByLabelText('Toggle text keyboard');
    fireEvent.click(keyboardBtn);

    const input = screen.getByPlaceholderText(/Make a grocery list/i);
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { value: 'Create shopping list' } });
    fireEvent.submit(input.closest('form')!);

    expect(onSend).toHaveBeenCalledWith('Create shopping list');
  });
});

describe('TaskProgress Component', () => {
  it('renders multi-step progress and confirmation banner', () => {
    const mockTask: TaskRecord = {
      id: 'task-1',
      prompt: 'Make an excel file',
      intent: 'Create spreadsheet document',
      status: 'executing',
      explanation: 'Building spreadsheet for you slowly.',
      steps: [
        {
          step_index: 1,
          action_name: 'create_spreadsheet',
          explanation: 'Writing rows to disk',
          success: true,
          output_path: 'C:\\Workspace\\test.csv',
        },
      ],
      totalSteps: 1,
      timestamp: Date.now(),
    };

    render(<TaskProgress task={mockTask} />);
    expect(screen.getByText(/"Make an excel file"/)).toBeInTheDocument();
    expect(screen.getByText('create_spreadsheet')).toBeInTheDocument();
    expect(screen.getByText('Building spreadsheet for you slowly.')).toBeInTheDocument();
    expect(screen.getByText(/test\.csv/)).toBeInTheDocument();
  });
});

describe('SettingsModal Component', () => {
  it('renders Zootopia theme banner and toggles cursor gaze', () => {
    const onToggleGaze = vi.fn();
    render(
      <SettingsModal
        isOpen={true}
        gazeEnabled={true}
        onToggleGaze={onToggleGaze}
        onClose={vi.fn()}
        onClearHistory={vi.fn()}
        onUnpair={vi.fn()}
        onReconnect={vi.fn()}
      />
    );

    expect(screen.getByText(/ZOOTOPIA DMV/i)).toBeInTheDocument();
    expect(screen.getByText(/Sync Eyes to Laptop Mouse/i)).toBeInTheDocument();

    const gazeBtn = screen.getByText('ON');
    fireEvent.click(gazeBtn);
    expect(onToggleGaze).toHaveBeenCalledWith(false);
  });
});

describe('PairingModal Component', () => {
  it('renders pairing code input and validates required fields', () => {
    render(
      <PairingModal
        isOpen={true}
        onClose={vi.fn()}
        onPairSuccess={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/Laptop Wi-Fi IP Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/6-Digit Pairing Code/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Pair With Flash/i })).toBeInTheDocument();
  });
});
