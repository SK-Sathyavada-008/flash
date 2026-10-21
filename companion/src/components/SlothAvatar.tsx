import React from 'react';
import { CompanionExpressionState, CursorGazeCoordinates } from '../types';

interface SlothAvatarProps {
  state: CompanionExpressionState;
  subtext?: string;
  cursorGaze?: CursorGazeCoordinates | null;
  gazeEnabled?: boolean;
  onClick?: () => void;
}

export const SlothAvatar: React.FC<SlothAvatarProps> = ({
  state,
  subtext,
  cursorGaze,
  gazeEnabled = true,
  onClick,
}) => {
  // Gaze coordinates calculation for 2D eyes
  const gazeX = gazeEnabled && cursorGaze ? (cursorGaze.x - 0.5) * 2 : 0;
  const gazeY = gazeEnabled && cursorGaze ? (cursorGaze.y - 0.5) * 2 : 0;

  // Real-time visible pupil travel within almond eyes (travel up to +/-9.5px horizontal, +/-6.0px vertical)
  const pupilDx = gazeX * 9.5;
  const pupilDy = gazeY * 6.0;

  // Subtle head tilt following cursor gaze
  const headTilt = gazeX * 3.5;

  // Flash is sleeping with closed eyes only if disconnected and no active cursor gaze is received
  const isSleeping = state === 'disconnected' && !cursorGaze;

  // Color aura glow based on companion state
  const getGlowColor = () => {
    switch (state) {
      case 'listening':
        return 'rgba(16, 185, 129, 0.4)'; // Emerald
      case 'thinking':
        return 'rgba(245, 158, 11, 0.45)'; // Amber
      case 'executing':
        return 'rgba(59, 130, 246, 0.5)'; // Blue
      case 'success':
        return 'rgba(34, 197, 94, 0.55)'; // Green
      case 'failure':
        return 'rgba(239, 68, 68, 0.45)'; // Red
      case 'stopped':
        return 'rgba(220, 38, 38, 0.6)'; // Crimson
      case 'disconnected':
      case 'idle':
      default:
        return 'rgba(217, 119, 6, 0.25)'; // Warm sloth golden amber
    }
  };

  const getStatusLabel = () => {
    switch (state) {
      case 'listening':
        return 'Listening...';
      case 'thinking':
        return 'Flash is thinking...';
      case 'executing':
        return 'Working...';
      case 'success':
        return 'Done!';
      case 'failure':
        return 'Oops! Something went wrong.';
      case 'stopped':
        return 'Emergency Stopped';
      case 'disconnected':
        return 'Offline / Disconnected';
      case 'idle':
      default:
        return 'Flash is ready';
    }
  };

  return (
    <div
      className={`sloth-container state-${state}`}
      onClick={onClick}
      role="region"
      aria-label={`Flash companion avatar: ${state}`}
    >
      <div
        className="avatar-glow-ring"
        style={{
          boxShadow: `0 0 50px 10px ${getGlowColor()}`,
        }}
      >
        <svg
          className="sloth-svg"
          viewBox="0 0 240 220"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Sloth Fur & Skin Gradients */}
            <linearGradient id="slothFurBase" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#877568" />
              <stop offset="60%" stopColor="#68564a" />
              <stop offset="100%" stopColor="#4d3d33" />
            </linearGradient>

            {/* Silvery/blonde combed-back hair streaks */}
            <linearGradient id="slothFurStreaks" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#d9cdbf" />
              <stop offset="50%" stopColor="#b4a494" />
              <stop offset="100%" stopColor="#7a695b" />
            </linearGradient>

            {/* Dark teardrop eye mask patch */}
            <linearGradient id="slothEyeMask" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3d271c" />
              <stop offset="100%" stopColor="#21130b" />
            </linearGradient>

            {/* Cream muzzle & face disc */}
            <linearGradient id="slothMuzzle" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#f7f0e1" />
              <stop offset="100%" stopColor="#ded1ba" />
            </linearGradient>

            {/* Leathery nose gradient */}
            <linearGradient id="slothSnout" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3d3736" />
              <stop offset="70%" stopColor="#241e1d" />
              <stop offset="100%" stopColor="#14100f" />
            </linearGradient>

            {/* Zootopia DMV Sage Green Polo */}
            <linearGradient id="dmvPolo" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#7ba07e" />
              <stop offset="100%" stopColor="#557558" />
            </linearGradient>

            {/* DMV Honey Oak Counter Desk */}
            <linearGradient id="dmvDesk" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#c5915d" />
              <stop offset="25%" stopColor="#a3713f" />
              <stop offset="100%" stopColor="#6d4724" />
            </linearGradient>

            {/* Hazel/Amber eye iris */}
            <radialGradient id="irisGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#9e6231" />
              <stop offset="70%" stopColor="#6f3b14" />
              <stop offset="100%" stopColor="#431e08" />
            </radialGradient>

            {/* Almond Eye Socket Clip Paths */}
            <clipPath id="leftEyeClip">
              <path d="M 68 83 C 74 74 90 74 96 83 C 90 92 74 92 68 83 Z" />
            </clipPath>
            <clipPath id="rightEyeClip">
              <path d="M 144 83 C 150 74 166 74 172 83 C 166 92 150 92 144 83 Z" />
            </clipPath>
          </defs>

          {/* --- Layer 1: Torso, Green DMV Polo, and Striped Tie --- */}
          {/* Shoulders & Torso */}
          <path
            d="M 35 152 Q 120 126 205 152 L 220 185 L 20 185 Z"
            fill="url(#dmvPolo)"
          />

          {/* Arm fur at sides */}
          <ellipse cx="38" cy="166" rx="18" ry="24" fill="url(#slothFurBase)" />
          <ellipse cx="202" cy="166" rx="18" ry="24" fill="url(#slothFurBase)" />

          {/* Polo Collar Back */}
          <path
            d="M 98 126 Q 120 134 142 126 L 138 135 Q 120 142 102 135 Z"
            fill="#425d45"
          />
          {/* Polo Collar Leaves */}
          <polygon
            points="98,126 118,146 112,148 94,136"
            fill="#7ba27e"
            stroke="#436146"
            strokeWidth="1.2"
          />
          <polygon
            points="142,126 122,146 128,148 146,136"
            fill="#7ba27e"
            stroke="#436146"
            strokeWidth="1.2"
          />

          {/* Striped Tie Base (Orange) */}
          <polygon points="115,142 125,142 123,150 117,150" fill="#dd5e28" />
          <path
            d="M 116 150 L 124 150 L 128 185 L 120 188 L 112 185 Z"
            fill="#dd5e28"
          />
          {/* Diagonal Navy Stripes on Tie */}
          <polygon points="116,154 124,158 124,162 115,158" fill="#1e293b" />
          <polygon points="114,167 126,171 126,175 113,171" fill="#1e293b" />
          <polygon points="112,179 128,183 128,186 112,182" fill="#1e293b" />

          {/* Gold Tie Clip */}
          <rect
            x="113"
            y="163"
            width="14"
            height="3"
            rx="1.5"
            fill="#facc15"
            stroke="#ca8a04"
            strokeWidth="0.5"
          />

          {/* --- Layer 2: Head Group (Animated Tilt tracking mouse) --- */}
          <g
            style={{
              transformOrigin: '120px 95px',
              transform: `rotate(${headTilt}deg)`,
              transition: 'transform 0.12s ease-out',
            }}
          >
            {/* Back Fur Dome */}
            <ellipse cx="120" cy="85" rx="66" ry="60" fill="url(#slothFurBase)" />

            {/* Silvery/blonde combed-back hair streaks */}
            <path
              d="M 100 35 Q 120 22 140 35"
              stroke="url(#slothFurStreaks)"
              strokeWidth="6"
              strokeLinecap="round"
              fill="none"
            />
            <path
              d="M 92 46 Q 120 30 148 46"
              stroke="url(#slothFurStreaks)"
              strokeWidth="5"
              strokeLinecap="round"
              fill="none"
            />
            <path
              d="M 86 58 Q 120 42 154 58"
              stroke="url(#slothFurStreaks)"
              strokeWidth="4"
              strokeLinecap="round"
              fill="none"
            />

            {/* Cream Face Disc */}
            <ellipse cx="120" cy="94" rx="54" ry="46" fill="url(#slothMuzzle)" />

            {/* Sloth Dark Teardrop Eye Patches (Slanted downward to cheeks) */}
            <path
              d="M 72 70 C 88 64 102 74 98 94 C 94 110 68 108 64 92 C 60 78 68 72 72 70 Z"
              fill="url(#slothEyeMask)"
            />
            <path
              d="M 168 70 C 152 64 138 74 142 94 C 146 110 172 108 176 92 C 180 78 172 72 168 70 Z"
              fill="url(#slothEyeMask)"
            />

            {/* Left Eye & Real-time Gaze Tracking */}
            {isSleeping ? (
              // Sleeping closed eye
              <path
                d="M 70 84 Q 82 92 94 84"
                stroke="#21130b"
                strokeWidth="3.5"
                strokeLinecap="round"
                fill="none"
              />
            ) : state === 'stopped' ? (
              // Emergency stopped 'X' eye
              <g stroke="#ffffff" strokeWidth="3" strokeLinecap="round">
                <line x1="74" y1="78" x2="90" y2="88" />
                <line x1="90" y1="78" x2="74" y2="88" />
              </g>
            ) : state === 'success' ? (
              // Laughing joyful eye squint
              <path
                d="M 70 85 Q 82 74 94 85"
                stroke="#21130b"
                strokeWidth="3.5"
                strokeLinecap="round"
                fill="none"
              />
            ) : (
              // Active Eye with live cursor gaze tracking!
              <g clipPath="url(#leftEyeClip)" data-testid="left-eye-gaze">
                {/* Eye Sclera (White/Cream) */}
                <rect x="65" y="70" width="35" height="30" fill="#fcfaf4" />

                {/* Pupil and Iris assembly with GPU-accelerated transform */}
                <g
                  data-testid="left-pupil-assembly"
                  transform={`translate(${pupilDx}, ${pupilDy})`}
                  style={{
                    transform: `translate(${pupilDx}px, ${pupilDy}px)`,
                    transition: 'transform 0.05s ease-out',
                  }}
                >
                  {/* Hazel Iris */}
                  <circle cx={82} cy={83} r={9} fill="url(#irisGrad)" />

                  {/* Black Pupil */}
                  <circle cx={82} cy={83} r={5.5} fill="#090a0f" />

                  {/* Primary Catchlight */}
                  <circle cx={84} cy={80} r={2.4} fill="#ffffff" />
                  {/* Secondary Subtle Catchlight */}
                  <circle cx={80} cy={85} r={1.2} fill="#ffffff" opacity="0.8" />
                </g>

                {/* Heavy Drooping Upper Eyelid (Sleepy Sloth Look) */}
                <path
                  d={
                    state === 'listening'
                      ? "M 67 81 C 73 75 91 75 97 81 C 91 79 73 79 67 81 Z"
                      : "M 67 83 C 73 73 91 73 97 83 C 91 79 73 79 67 83 Z"
                  }
                  fill="url(#slothEyeMask)"
                />
              </g>
            )}

            {/* Right Eye & Real-time Gaze Tracking */}
            {isSleeping ? (
              // Sleeping closed eye
              <path
                d="M 146 84 Q 158 92 170 84"
                stroke="#21130b"
                strokeWidth="3.5"
                strokeLinecap="round"
                fill="none"
              />
            ) : state === 'stopped' ? (
              // Emergency stopped 'X' eye
              <g stroke="#ffffff" strokeWidth="3" strokeLinecap="round">
                <line x1="150" y1="78" x2="166" y2="88" />
                <line x1="166" y1="78" x2="150" y2="88" />
              </g>
            ) : state === 'success' ? (
              // Laughing joyful eye squint
              <path
                d="M 146 85 Q 158 74 170 85"
                stroke="#21130b"
                strokeWidth="3.5"
                strokeLinecap="round"
                fill="none"
              />
            ) : (
              // Active Eye with live cursor gaze tracking!
              <g clipPath="url(#rightEyeClip)" data-testid="right-eye-gaze">
                {/* Eye Sclera (White/Cream) */}
                <rect x="140" y="70" width="35" height="30" fill="#fcfaf4" />

                {/* Pupil and Iris assembly with GPU-accelerated transform */}
                <g
                  data-testid="right-pupil-assembly"
                  transform={`translate(${pupilDx}, ${pupilDy})`}
                  style={{
                    transform: `translate(${pupilDx}px, ${pupilDy}px)`,
                    transition: 'transform 0.05s ease-out',
                  }}
                >
                  {/* Hazel Iris */}
                  <circle cx={158} cy={83} r={9} fill="url(#irisGrad)" />

                  {/* Black Pupil */}
                  <circle cx={158} cy={83} r={5.5} fill="#090a0f" />

                  {/* Primary Catchlight */}
                  <circle cx={160} cy={80} r={2.4} fill="#ffffff" />
                  {/* Secondary Subtle Catchlight */}
                  <circle cx={156} cy={85} r={1.2} fill="#ffffff" opacity="0.8" />
                </g>

                {/* Heavy Drooping Upper Eyelid (Sleepy Sloth Look) */}
                <path
                  d={
                    state === 'listening'
                      ? "M 143 81 C 149 75 167 75 173 81 C 167 79 149 79 143 81 Z"
                      : "M 143 83 C 149 73 167 73 173 83 C 167 79 149 79 143 83 Z"
                  }
                  fill="url(#slothEyeMask)"
                />
              </g>
            )}

            {/* Sleepy eye crease lines underneath */}
            <path
              d="M 72 90 Q 82 96 92 90"
              stroke="#2a180f"
              strokeWidth="1.5"
              fill="none"
              opacity="0.6"
            />
            <path
              d="M 148 90 Q 158 96 168 90"
              stroke="#2a180f"
              strokeWidth="1.5"
              fill="none"
              opacity="0.6"
            />

            {/* Muzzle Mound */}
            <ellipse cx="120" cy="112" rx="26" ry="18" fill="url(#slothMuzzle)" />

            {/* Leathery Snout / Nose */}
            <ellipse cx="120" cy="104" rx="14" ry="10" fill="url(#slothSnout)" />
            {/* Nostrils */}
            <ellipse cx="115" cy="106" rx="3" ry="2.2" fill="#0c0908" />
            <ellipse cx="125" cy="106" rx="3" ry="2.2" fill="#0c0908" />
            {/* Nose Bridge Highlight */}
            <ellipse cx="118" cy="100" rx="6" ry="2" fill="#ffffff" opacity="0.3" />

            {/* Mouth & Expressions */}
            {state === 'success' ? (
              // The iconic Flash Zootopia Slow Laugh!
              <g className="flash-laugh-mouth">
                <path
                  d="M 98 114 Q 120 156 142 114 Z"
                  fill="#6b1227"
                  stroke="#240c11"
                  strokeWidth="2.5"
                />
                {/* Tongue */}
                <ellipse cx="120" cy="138" rx="13" ry="8" fill="#fb7185" />
                {/* Upper teeth row */}
                <path d="M 106 115 L 106 119 L 134 119 L 134 115" fill="#f8fafc" />
              </g>
            ) : state === 'thinking' ? (
              <ellipse cx="120" cy="120" rx="5" ry="4" fill="#3a1e12" />
            ) : state === 'failure' ? (
              <path
                d="M 108 124 Q 120 117 132 124"
                stroke="#3a1e12"
                strokeWidth="3"
                fill="none"
                strokeLinecap="round"
              />
            ) : state === 'stopped' ? (
              <circle cx="120" cy="122" r="6" fill="#3a1e12" />
            ) : (
              // Iconic wry half-smile
              <path
                d="M 106 118 Q 120 126 134 118 C 136 115 138 113 138 111"
                stroke="#3a1e12"
                strokeWidth="3"
                fill="none"
                strokeLinecap="round"
              />
            )}
          </g>

          {/* --- Layer 3: DMV Office Desk Counter in Foreground --- */}
          {/* Counter Desk Surface */}
          <path
            d="M 0 178 L 240 178 L 240 220 L 0 220 Z"
            fill="url(#dmvDesk)"
          />
          {/* Polished Counter Wood Highlight */}
          <line
            x1="0"
            y1="179"
            x2="240"
            y2="179"
            stroke="#f6c28b"
            strokeWidth="2"
            opacity="0.6"
          />

          {/* Coffee Mug on Desk */}
          <rect
            x="18"
            y="152"
            width="26"
            height="26"
            rx="4"
            fill="#fafafa"
            stroke="#cbd5e1"
            strokeWidth="1"
          />
          {/* Mug Handle */}
          <path
            d="M 18 158 C 10 158 10 172 18 172"
            fill="none"
            stroke="#cbd5e1"
            strokeWidth="2.5"
          />
          <text
            x="31"
            y="167"
            fontSize="6"
            fontWeight="bold"
            fill="#dc2626"
            textAnchor="middle"
          >
            DMV
          </text>

          {/* Flash's 3 Curved Claws resting on Counter */}
          <path
            d="M 172 175 C 172 166 178 166 178 175 L 178 183 C 178 184 172 184 172 183 Z"
            fill="#ded0ba"
            stroke="#a69477"
            strokeWidth="1"
          />
          <path
            d="M 180 173 C 180 164 186 164 186 173 L 186 183 C 186 184 180 184 180 183 Z"
            fill="#ded0ba"
            stroke="#a69477"
            strokeWidth="1"
          />
          <path
            d="M 188 176 C 188 167 194 167 194 176 L 194 183 C 194 184 188 184 188 183 Z"
            fill="#ded0ba"
            stroke="#a69477"
            strokeWidth="1"
          />

          {/* State overlays: Thinking bubble / Sleep ZZZ */}
          {state === 'thinking' && (
            <g className="thinking-orbit">
              <circle cx="185" cy="40" r="14" fill="#f59e0b" opacity="0.95" />
              <text x="180" y="46" fontSize="16" fill="#ffffff">
                💭
              </text>
            </g>
          )}

          {isSleeping && (
            <g className="sleepy-zzz">
              <text x="180" y="55" fontSize="18" fill="#cbd5e1" fontWeight="bold">
                z
              </text>
              <text x="194" y="42" fontSize="22" fill="#94a3b8" fontWeight="bold">
                Z
              </text>
            </g>
          )}
        </svg>
      </div>

      <div className="status-badge">
        <span className="status-dot"></span>
        <span className="status-text">{getStatusLabel()}</span>
      </div>

      {subtext && <p className="status-subtext">{subtext}</p>}
    </div>
  );
};
