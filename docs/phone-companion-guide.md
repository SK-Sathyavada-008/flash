# Flash Phone Companion & LAN Connection Guide (Milestone 3)

This guide documents the architecture, Windows Firewall configuration, pairing protocol, and step-by-step setup for connecting your **Redmi Android device** to the **Flash Windows Desktop Agent** over your local Wi-Fi network.

---

## 1. Security & Network Boundary

- **Local Network Only**: Communication occurs directly between your phone and laptop over your private Wi-Fi. No data leaves your home network; no paid cloud relay or third-party server is required.
- **Never Publicly Exposed**: The agent must never be port-forwarded to the public internet.
- **Zero-Trust LAN Access**: Unauthenticated remote computer-control endpoints are strictly blocked (`401 Unauthorized`).
- **Pairing Code Verification**: Initial connection requires an explicit, short-lived 6-digit code (`XXX-XXX`) generated on the laptop that expires after 5 minutes and can only be used once.
- **Revocable 256-bit Bearer Tokens**: Successful pairing issues a cryptographically secure token saved in the phone's local storage. This token can be revoked at any time from the phone settings or laptop API.
- **Global Emergency Stop**: The phone companion features a prominent red **STOP** button that immediately halts all active and pending desktop automation.

---

## 2. Windows Firewall Configuration

To allow your Redmi phone to communicate with your laptop over Wi-Fi, Windows Firewall must permit inbound traffic on ports **8765** (FastAPI backend) and **5173** (Vite companion frontend) on **Private networks only**.

### Step 1: Ensure Your Wi-Fi is Set to "Private"
Open PowerShell as Administrator and run:
```powershell
Get-NetConnectionProfile
```
If your Wi-Fi network profile shows `NetworkCategory: Public`, change it to Private:
```powershell
Set-NetConnectionProfile -Name "Your-WiFi-Name" -NetworkCategory Private
```

### Step 2: Create Firewall Inbound Rules
Run the following PowerShell commands as Administrator:

```powershell
# 1. Allow Flash Desktop Agent (Backend API & WebSocket on port 8765)
New-NetFirewallRule -DisplayName "Flash Desktop Agent (Local LAN)" `
    -Direction Inbound `
    -LocalPort 8765 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private

# 2. Allow Flash Phone Companion (Vite PWA on port 5173)
New-NetFirewallRule -DisplayName "Flash Phone Companion PWA" `
    -Direction Inbound `
    -LocalPort 5173 `
    -Protocol TCP `
    -Action Allow `
    -Profile Private
```

> **Security Note**: Notice the `-Profile Private` flag. This ensures that if your laptop connects to a public Wi-Fi network (coffee shop, airport), these ports remain completely closed and protected.

---

## 3. Step-by-Step Setup & Redmi Android Pairing

### Step 1: Install Frontend Dependencies (Laptop)
From the repository root `c:\Keerthu\flash`:
```powershell
cd companion
npm install
cd ..
```

### Step 2: Start the Windows Desktop Agent (Laptop)
In your first PowerShell terminal, run:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-agent.ps1
```
The console will display:
```text
==========================================================
      Starting Flash Windows Desktop Agent (Local & LAN)   
==========================================================
Local Host:        http://127.0.0.1:8765
Wi-Fi LAN IP(s):   192.168.1.15
Phone Companion:   http://192.168.1.15:8765  (or ws://192.168.1.15:8765/ws/v1/companion)
Pairing Code API:  http://127.0.0.1:8765/api/v1/auth/pair-code
```
*(Note down your Wi-Fi LAN IP, e.g. `192.168.1.15`).*

### Step 3: Start the Phone Companion Frontend (Laptop)
In a second PowerShell terminal, run:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-companion.ps1
```
The console will display:
```text
==========================================================
       Starting Flash Phone Companion (Vite PWA)          
==========================================================
Local Laptop URL:    http://localhost:5173
Redmi Phone URL(s):
  -> http://192.168.1.15:5173
```

### Step 4: Open Companion on Your Redmi Phone
1. Ensure your Redmi phone is connected to the **same Wi-Fi network**.
2. Open **Google Chrome** on your Redmi phone.
3. In the address bar, type:
   ```
   http://<YOUR-LAPTOP-IP>:5173
   ```
   *(e.g., `http://192.168.1.15:5173`)*.

### Step 5: Install the Progressive Web App (PWA)
1. In Chrome on your phone, tap the **three dots menu (⋮)** in the top right corner.
2. Tap **"Install app"** or **"Add to Home screen"**.
3. Confirm the prompt: Flash will be installed as a native-like standalone app on your Redmi home screen with the sloth icon!
4. Launch Flash from your home screen.

### Step 6: Pair Your Redmi Phone with the Laptop
1. When the Flash app opens, the **Pair Device** sheet will automatically appear (or tap the **Pair Device** pill in the top header).
2. The **Laptop Wi-Fi IP** will automatically populate with your laptop IP (`192.168.1.15`).
3. Enter the **6-Digit Pairing Code** displayed in your browser at `http://127.0.0.1:8765/api/v1/auth/pair-code` (or run `Invoke-RestMethod http://127.0.0.1:8765/api/v1/auth/pair-code` in PowerShell).
4. Tap **"Pair With Flash"**.
5. You will see: *"Successfully paired with Flash! Connecting..."*
6. The header status pill will turn **Green ("Connected")**, and Flash's avatar will show **"Flash is ready"** with a warm golden aura!

---

## 4. Testing Real Commands from the Phone

### Option A: Voice (Push-to-Talk)
1. Tap the large microphone button in the center.
2. Speak clearly into your Redmi phone:
   > *"Flash, make a grocery list with apples, bananas, and milk"*
3. Tap the microphone again (or release) to finish speaking.
4. Watch the live execution stream:
   - **Transcript Preview**: Shows what Flash heard.
   - **Flash State**: Avatar turns to **Thinking** (`💭`) while local Gemma interprets the command.
   - **Task Progress**: Shows intent and real-time execution steps (`create_grocery_list`).
   - **Avatar Celebration**: Avatar squints with happy eyes and celebratory stars (`Done!`).
   - The file is created locally on your laptop in `%USERPROFILE%\Documents\Flash Workspace\lists\`.

### Option B: Text Fallback (Keyboard)
1. Tap the **Keyboard icon** to the left of the mic button.
2. Type any automation request:
   > `Create an excel file with Name, Quantity, and Price`
   > `Type this into Notepad: Hello from my Redmi phone!`
   > `Open https://news.ycombinator.com`
3. Tap the **Send button**.
4. The real task status and output path will be rendered in real-time.

---

## 5. Emergency Controls & Privacy Settings

- **Emergency Stop**: Tap the red **STOP** pill in the header at any time. The laptop agent halts immediately, stops all file modifications, and locks into the safe `stopped` state. Tap **Resume** to restore normal operation.
- **Task History**: Tap the **History** button at the bottom to inspect previous tasks, prompts, step counts, and execution times.
- **Unpair Companion**: Open **Settings** (gear icon) -> **Unpair Companion**. This revokes your token on the laptop agent and disconnects the phone immediately.
