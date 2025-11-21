# WYAO Habit Tracker

A dedicated hardware device designed to help you build habits through positive reinforcement and friction-free tracking.

## Use Case
Building a habit requires consistency and accountability. This device sits on your desk or wall, displaying a simple challenge: **"WYAO"** (Work Your A** Off). When you complete your habit (e.g., a workout, a study session, a task), you press the button. The screen rewards you with your current statistics, reinforcing your progress, before silently reverting to its challenge mode.

## Features
*   **Zero Distraction**: The default "WYAO" screen is static and consumes zero power.
*   **Instant Feedback**: Displays "Keep it up!" and your stats upon interaction.
*   **Smart Metrics**:
    *   **Week**: Number of times you've completed the habit this week.
    *   **Streak**: Number of consecutive weeks you've been active.
    *   **Total**: Lifetime completion count.
*   **Auto-Reset**: The display automatically reverts to the "WYAO" screen after 60 seconds.
*   **Persistent Storage**: All data is saved locally in `stats.json`.

## Hardware Requirements
*   **Raspberry Pi Zero 2 W** (or any Raspberry Pi with GPIO headers).
*   **Waveshare 2.13inch E-Paper HAT (B)** (Red/Black/White version).
*   MicroSD Card (with Raspberry Pi OS / Trixie).
*   Power Supply.

## Installation

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd habit-tracker
    ```

2.  **Enable SPI**
    Run `sudo raspi-config`, navigate to **Interface Options** > **SPI**, and enable it.

3.  **Install Dependencies**
    ```bash
    pip3 install -r requirements.txt
    ```
    *Note: You may need to install system libraries for Pillow (e.g., `libopenjp2-7`, `libtiff5`).*

## Usage

### Initialization
Before first use, initialize the display to the default state:
```bash
python3 tracker.py --init
```

### Tracking
To log a habit completion (simulate a button press):
```bash
python3 tracker.py
```

### Physical Button Setup
To use a physical button, wire it to a GPIO pin and configure a system service or script to run `python3 tracker.py` when the button is pressed.

## Run on Boot (Systemd)

To have the habit tracker run automatically when the Raspberry Pi starts:

1.  **Copy the service file:**
    ```bash
    sudo cp habit-tracker.service /etc/systemd/system/
    ```

2.  **Reload systemd:**
    ```bash
    sudo systemctl daemon-reload
    ```

3.  **Enable and Start the service:**
    ```bash
    sudo systemctl enable habit-tracker.service
    sudo systemctl start habit-tracker.service
    ```

4.  **Check Status:**
    ```bash
    sudo systemctl status habit-tracker.service
    ```

## Companion API Setup

To enable the HTTP API for companion apps:

1.  **Install System Dependencies**:
    ```bash
    sudo apt update
    sudo apt install -y swig python3-dev python3-setuptools liblgpio-dev
    ```

2.  **Set up Virtual Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip3 install -r requirements.txt
    ```

3.  **Migrate Data** (One-time):
    ```bash
    python3 migrate.py
    ```

4.  **Install Services**:
    ```bash
    # Copy service files
    sudo cp habit-tracker.service /etc/systemd/system/
    sudo cp habit-api.service /etc/systemd/system/
    
    # Reload and enable
    sudo systemctl daemon-reload
    sudo systemctl enable --now habit-tracker.service
    sudo systemctl enable --now habit-api.service
    ```

5.  **Access API**:
    -   Stats: `http://<PI_IP>:8000/stats`
    -   Docs: `http://<PI_IP>:8000/docs`

## Troubleshooting
*   **Display not updating?** Check SPI connections and ensure `epdconfig.py` is using the correct SPI device.
*   **Slow updates?** E-Paper displays take ~15 seconds to refresh. This is normal hardware behavior.
