"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              ⚡ ElAnswer                                       ║
║           AI-Powered Screen Capture & Question Solver                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Description:  Captures screen content and uses Google Gemini AI to          ║
║                analyze and solve questions, problems, or code snippets.      ║
║                                                                               ║
║  Version:      1.3.0                                                          ║
║  Created:      December 2025                                                  ║
║  License:      MIT                                                            ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                              DEVELOPERS                                        ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  👤 Nanda Kumaran G                                                           ║
║     GitHub: @XploitGh0st                                                      ║
║     Role: Lead Developer                                                      ║
║                                                                               ║
║  👤 Saffron Zen                                                               ║
║     GitHub: @Saffronzen005                                                    ║
║     Role: Co-Developer                                                        ║
║                                                                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Repository: https://github.com/XploitGh0st/ElAnswer                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import logging
import platform
import subprocess
import webbrowser
import base64
import io
from datetime import datetime
import keyboard  # For detecting key presses
import mouse  # For mouse button detection
import google.generativeai as genai
from PIL import Image, ImageTk  # For image handling
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import pystray  # For system tray icon
import requests  # For Ollama API calls

# Platform detection
IS_WINDOWS = sys.platform == 'win32'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')

# Import platform-specific modules
if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes
else:
    ctypes = None

# Windows Display Affinity constants for screen capture protection
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 2004+ (Build 19041+)

# Additional Windows style constants for stealth
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
GWL_EXSTYLE = -20
LWA_ALPHA = 0x00000002
LWA_COLORKEY = 0x00000001

# Cross-platform screenshot capture
def capture_screenshot():
    """Capture screenshot in a cross-platform manner."""
    try:
        # Try PIL ImageGrab first (works on Windows and macOS)
        from PIL import ImageGrab
        return ImageGrab.grab()
    except Exception as e:
        logger.warning(f"ImageGrab failed: {e}")
        # Fallback for Linux - try pyscreenshot
        try:
            import pyscreenshot as ImageGrab
            return ImageGrab.grab()
        except ImportError:
            logger.error("pyscreenshot not installed. Install with: pip install pyscreenshot")
            return None
        except Exception as e2:
            logger.error(f"Screenshot capture failed: {e2}")
            return None

# Cross-platform URL opener
def open_url(url):
    """Open URL in default browser (cross-platform)."""
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(f"Failed to open URL: {e}")

def get_windows_build_number():
    """Get Windows build number for feature detection."""
    if not IS_WINDOWS:
        return 0
    try:
        version = sys.getwindowsversion()
        return version.build
    except Exception:
        return 0

def set_window_display_affinity(hwnd, affinity):
    """
    Set window display affinity to exclude from screen capture.
    WDA_EXCLUDEFROMCAPTURE (0x11) - Excludes window from screen capture (Win10 2004+)
    WDA_MONITOR (0x01) - Shows black in screen captures (older Windows)
    """
    if not IS_WINDOWS or not ctypes:
        return False
    try:
        # SetWindowDisplayAffinity function
        result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, affinity)
        return result != 0
    except Exception as e:
        logger.debug(f"SetWindowDisplayAffinity failed: {e}")
        return False

def make_window_stealth(window, allow_input=False):
    """
    Apply stealth mode to window - makes it invisible to screen capture,
    screen sharing software, and proctoring applications.
    
    allow_input: if True, don't apply WS_EX_NOACTIVATE (allows keyboard/mouse input)
    """
    if not IS_WINDOWS or not ctypes:
        return False
    
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        
        if not hwnd:
            hwnd = window.winfo_id()
        
        build_number = get_windows_build_number()
        
        # Apply extended window styles for stealth
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        # Add stealth styles:
        # WS_EX_TOOLWINDOW - No taskbar button
        # WS_EX_LAYERED - Required for transparency and some capture exclusion
        ex_style = ex_style | WS_EX_TOOLWINDOW | WS_EX_LAYERED
        
        # Only add WS_EX_NOACTIVATE if we don't need keyboard input
        if not allow_input:
            ex_style = ex_style | WS_EX_NOACTIVATE
        
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        
        # Set layered window attributes for proper rendering
        ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
        
        # Apply display affinity to exclude from capture
        # Windows 10 2004+ (Build 19041+) supports WDA_EXCLUDEFROMCAPTURE
        if build_number >= 19041:
            # Use WDA_EXCLUDEFROMCAPTURE - completely invisible to capture
            success = set_window_display_affinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if success:
                logger.debug(f"Applied WDA_EXCLUDEFROMCAPTURE to window (Build {build_number})")
            else:
                # Fallback to WDA_MONITOR (shows black in captures)
                set_window_display_affinity(hwnd, WDA_MONITOR)
                logger.debug("Fallback to WDA_MONITOR")
        else:
            # Older Windows - use WDA_MONITOR (shows black in screen capture)
            set_window_display_affinity(hwnd, WDA_MONITOR)
            logger.debug(f"Applied WDA_MONITOR for older Windows (Build {build_number})")
        
        return True
    except Exception as e:
        logger.debug(f"Could not apply stealth mode: {e}")
        return False

# Cross-platform window styling helper
def apply_window_style(window, style='tool', stealth=True, allow_input=False):
    """
    Apply platform-specific window styling.
    style: 'tool' (no taskbar), 'popup' (no taskbar, no activate)
    stealth: if True, apply screen capture exclusion (Windows 10 2004+)
    allow_input: if True, allow keyboard/mouse input (don't apply WS_EX_NOACTIVATE)
    """
    try:
        if IS_WINDOWS and ctypes:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            
            if not hwnd:
                hwnd = window.winfo_id()
            
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            if style == 'tool' or allow_input:
                # Tool style allows input
                ex_style = ex_style | WS_EX_TOOLWINDOW | WS_EX_LAYERED
            elif style == 'popup':
                # Popup style blocks input (for display-only windows)
                ex_style = ex_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED
            
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            # Set layered window attributes
            ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
            
            # Apply stealth mode if requested (pass allow_input to preserve input capability)
            if stealth:
                make_window_stealth(window, allow_input=allow_input)
                
        elif IS_MACOS:
            # macOS-specific styling (limited options with tkinter)
            # Note: macOS has different screen sharing APIs
            pass
        else:
            # Linux - try to set window type hint via wm attributes
            try:
                window.attributes('-type', 'utility')
            except tk.TclError:
                pass
    except Exception as e:
        logger.debug(f"Could not apply window style: {e}")

# Cross-platform transparent color support
def apply_transparency(window, bg_color='#000000'):
    """
    Apply transparency for rounded corners (platform-specific).
    Returns True if transparency is supported.
    """
    try:
        if IS_WINDOWS:
            window.configure(bg=bg_color)
            window.wm_attributes('-transparentcolor', bg_color)
            return True
        elif IS_MACOS:
            # macOS doesn't support transparentcolor the same way
            # Use a solid background instead
            window.configure(bg=bg_color)
            return False
        else:
            # Linux - transparency support varies by compositor
            try:
                window.configure(bg=bg_color)
                window.wm_attributes('-transparentcolor', bg_color)
                return True
            except tk.TclError:
                window.configure(bg=bg_color)
                return False
    except Exception:
        return False

# Cross-platform font helper
def get_system_font():
    """Get the appropriate system font for the platform."""
    if IS_WINDOWS:
        return 'Segoe UI'
    elif IS_MACOS:
        return 'SF Pro Display'
    else:
        return 'DejaVu Sans'

# Application version
APP_VERSION = "1.3.0"
APP_NAME = "ElAnswer"

# Determine if running as frozen executable (PyInstaller)
def is_frozen():
    """Check if the application is running as a frozen executable."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

# Get the correct base path for resources
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if is_frozen():
        # Running as compiled executable
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Get the correct path for user data (config, history)
def get_data_path(filename):
    """Get path for user data files (config, history) in app directory."""
    if is_frozen():
        # Store data next to the executable
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

# Setup logging
def setup_logging():
    """Configure logging for production use."""
    log_file = get_data_path("elanswer.log")
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (rotates at 5MB)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
    except Exception:
        file_handler = None
    
    # Console handler (only if not frozen or debug mode)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if not is_frozen() else logging.WARNING)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    if file_handler:
        logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logging
logger = setup_logging()

# Enable High DPI awareness (Windows only)
if IS_WINDOWS and ctypes:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Fallback for older Windows
        except Exception:
            pass

# ---------------- CONFIGURATION ---------------- #

# API Key will be loaded from config.json
# Users can set it in settings or as environment variable: os.environ["GEMINI_API_KEY"]
API_KEY = None  # Will be loaded from config

# The Hotkey combination to trigger the capture
HOTKEY = "ctrl+alt+s"

# The Hotkey combination to quit the application
QUIT_HOTKEY = "ctrl+alt+q"

# The Hotkey combination to hide/unhide the popup
HIDE_HOTKEY = "ctrl+alt+i"

# The Hotkey combination to toggle theme (dark/light)
THEME_HOTKEY = "ctrl+alt+t"

# The Hotkey combination to show history
HISTORY_HOTKEY = "ctrl+alt+h"

# The Hotkey combination to open settings
SETTINGS_HOTKEY = "ctrl+alt+p"

# The Hotkey combination to toggle question mode (MCQ/Coding)
MODE_HOTKEY = "ctrl+alt+m"

# The Hotkey combination to copy the last response
COPY_HOTKEY = "ctrl+alt+c"

# The Hotkey combination to start auto-typing the last response
AUTO_TYPE_HOTKEY = "ctrl+alt+a"

# The Hotkey combination to pause/resume auto-typing
PAUSE_TYPE_HOTKEY = "right-click"

# The Hotkey combination to open chat window
CHAT_HOTKEY = "ctrl+alt+g"

# Maximum number of history items to keep
MAX_HISTORY_ITEMS = 10

# ----------------------------------------------- #

# Global variable for the popup window
popup_window = None
popup_hidden = False  # Track if popup is hidden
loading_indicator = None  # Loading indicator window
logo_image = None  # Store logo image reference
tray_icon = None  # System tray icon
settings_window = None  # Settings window
chat_window = None  # Chat window
available_models = []  # Available Gemini models
model = None  # Current Gemini model instance

# Ollama globals
ollama_available_models = []  # Available Ollama models
ollama_connected = False  # Track Ollama connection status

# Qwen globals
qwen_available_models = []  # Available Qwen models
qwen_connected = False  # Track Qwen connection status

# Auto-type globals
auto_type_active = False  # Is auto-typing currently in progress
auto_type_paused = False  # Is auto-typing paused
auto_type_thread = None  # Thread running auto-type
auto_type_stop_event = None  # Event to stop auto-typing
auto_type_pause_event = None  # Event to pause auto-typing

# Get paths using the helper functions for proper executable support
LOGO_PATH = get_resource_path(os.path.join("assets", "logo.png"))
CONFIG_PATH = get_data_path("config.json")
HISTORY_PATH = get_data_path("history.json")

# History storage
answer_history = []

# Theme definitions
THEMES = {
    "light": {
        "card_bg": '#ffffff',
        "text_color": '#1a1a1a',
        "secondary_text": '#6b7280',
        "border_color": '#e5e7eb',
        "accent_color": '#18181b',
        "green_accent": '#22c55e',
        "light_gray": '#f9fafb',
        "close_btn_fg": '#9ca3af',
        "close_btn_hover": '#374151',
        "btn_hover": '#374151',
        "pulse_color": '#4ade80',
    },
    "dark": {
        "card_bg": '#1f2937',
        "text_color": '#f9fafb',
        "secondary_text": '#9ca3af',
        "border_color": '#374151',
        "accent_color": '#3b82f6',
        "green_accent": '#22c55e',
        "light_gray": '#111827',
        "close_btn_fg": '#6b7280',
        "close_btn_hover": '#d1d5db',
        "btn_hover": '#2563eb',
        "pulse_color": '#4ade80',
    }
}

def load_config():
    """Load configuration from file."""
    default_config = {
        "popup_x": 200,
        "popup_y": 80,
        "theme": "light",
        "model": "models/gemini-2.0-flash",
        "max_history": 10,
        "auto_copy": False,
        "show_explanation": True,
        "compact_mode": False,
        "stealth_mode": True,  # Hide from screen capture/sharing by default
        "question_mode": "mcq",  # "mcq" or "coding"
        "programming_language": "Python",  # Default language for coding mode
        # Auto-type settings
        "auto_type_enabled": True,
        "auto_type_wpm": 150,  # Words per minute for auto-typing
        # Ollama settings
        "ollama_enabled": False,
        "ollama_url": "http://localhost:11434",
        "ollama_model": "",
        # Qwen settings
        "qwen_enabled": False,
        "qwen_api_key": "",
        "qwen_model": "qwen3-coder-plus"
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**default_config, **config}
    except Exception as e:
        logger.warning(f"Could not load config: {e}")
    return default_config

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save config: {e}")

def load_history():
    """Load answer history from file."""
    global answer_history
    try:
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                answer_history = json.load(f)
                # Trim to max items
                answer_history = answer_history[:MAX_HISTORY_ITEMS]
    except Exception as e:
        logger.warning(f"Could not load history: {e}")
        answer_history = []

def save_history():
    """Save answer history to file."""
    try:
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(answer_history[:MAX_HISTORY_ITEMS], f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Could not save history: {e}")

def add_to_history(answer_text):
    """Add a new answer to history."""
    global answer_history
    
    # Create history entry
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "preview": extract_preview(answer_text),
        "answer": answer_text
    }
    
    # Add to beginning of list
    answer_history.insert(0, entry)
    
    # Trim to max items
    answer_history = answer_history[:MAX_HISTORY_ITEMS]
    
    # Save to file
    save_history()
    
    # Update tray menu if available (pystray auto-updates dynamic menus)
    # Note: pystray dynamically rebuilds menu on each click, no explicit update needed

def extract_preview(answer_text):
    """Extract a short preview from the answer text."""
    # Try to find the QUESTION section
    lines = answer_text.split('\n')
    for i, line in enumerate(lines):
        if 'QUESTION:' in line:
            # Get the next non-empty line as preview
            for j in range(i + 1, min(i + 3, len(lines))):
                preview_line = lines[j].strip()
                if preview_line and not preview_line.startswith('['):
                    # Truncate if too long
                    if len(preview_line) > 50:
                        return preview_line[:47] + "..."
                    return preview_line
    
    # Fallback: use first non-empty line
    for line in lines:
        line = line.strip()
        if line and not line.startswith('📋') and not line.startswith('✅') and not line.startswith('💡'):
            if len(line) > 50:
                return line[:47] + "..."
            return line
    
    return "Answer captured"

# Load saved configuration
app_config = load_config()

# Load API key from config or environment
API_KEY = app_config.get("api_key", "") or os.environ.get("GEMINI_API_KEY", "")

# Load answer history
load_history()

def configure_genai():
    """Configures the Gemini API."""
    global available_models, API_KEY, model
    
    # Skip Gemini configuration if Ollama or Qwen is enabled
    if app_config.get("ollama_enabled", False):
        logger.info("Ollama is enabled, skipping Gemini configuration.")
        return None
    if app_config.get("qwen_enabled", False):
        logger.info("Qwen is enabled, skipping Gemini configuration.")
        return None
    
    # Reload API key from config in case it was updated
    API_KEY = app_config.get("api_key", "") or os.environ.get("GEMINI_API_KEY", "")
    
    if not API_KEY or API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        logger.warning("No API key configured. Please set it in Settings (Ctrl+Alt+P).")
        return None
    
    try:
        genai.configure(api_key=API_KEY)
        
        # Fetch available models in background
        threading.Thread(target=fetch_available_models, daemon=True).start()
        
        # Use saved model or default
        selected_model = app_config.get("model", "models/gemini-2.0-flash")
        model = genai.GenerativeModel(selected_model)
        return model
    except Exception as e:
        logger.error(f"Failed to configure API: {e}")
        return None


def fetch_available_models():
    """Fetch available models from the API."""
    global available_models
    
    # Don't fetch if no API key is configured or if using Ollama/Qwen
    if app_config.get("ollama_enabled", False) or app_config.get("qwen_enabled", False):
        return
    
    api_key = app_config.get("api_key", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        # Use fallback models when no API key is set
        available_models = [
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
            "models/gemini-pro"
        ]
        return
    
    try:
        models_list = genai.list_models()
        # Filter for models that support generateContent
        available_models = []
        for m in models_list:
            try:
                # Check if model supports generateContent
                if hasattr(m, 'supported_generation_methods'):
                    methods = [method.name if hasattr(method, 'name') else str(method) 
                              for method in m.supported_generation_methods]
                    if 'generateContent' in methods:
                        model_name = m.name if hasattr(m, 'name') else str(m)
                        available_models.append(model_name)
            except Exception:
                continue
        
        # Sort with preferred models first
        preferred_order = ['gemini-2', 'gemini-1.5', 'gemini-pro']
        def sort_key(name):
            for i, pref in enumerate(preferred_order):
                if pref in name:
                    return (i, name)
            return (len(preferred_order), name)
        available_models.sort(key=sort_key)
    except Exception as e:
        logger.warning(f"Could not fetch models: {e}")
        # Fallback models
        available_models = [
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
            "models/gemini-pro"
        ]


def reload_model():
    """Reload the model with current settings."""
    global model
    
    # Skip if using Ollama/Qwen or no API key
    if app_config.get("ollama_enabled", False) or app_config.get("qwen_enabled", False):
        return
    
    api_key = app_config.get("api_key", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return
    
    selected_model = app_config.get("model", "models/gemini-2.0-flash")
    try:
        model = genai.GenerativeModel(selected_model)
        logger.info(f"Model changed to: {selected_model}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")


# ============== OLLAMA FUNCTIONS ============== #

def fetch_ollama_models(ollama_url=None):
    """Fetch available models from Ollama server."""
    global ollama_available_models, ollama_connected
    
    if ollama_url is None:
        ollama_url = app_config.get("ollama_url", "http://localhost:11434")
    
    # Ensure URL doesn't have trailing slash
    ollama_url = ollama_url.rstrip('/')
    
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            ollama_available_models = [m.get("name", "") for m in models if m.get("name")]
            ollama_connected = True
            logger.info(f"Ollama connected. Found {len(ollama_available_models)} models.")
            return ollama_available_models
        else:
            logger.warning(f"Ollama returned status {response.status_code}")
            ollama_connected = False
            return []
    except requests.exceptions.ConnectionError:
        logger.warning(f"Could not connect to Ollama at {ollama_url}")
        ollama_connected = False
        return []
    except requests.exceptions.Timeout:
        logger.warning(f"Ollama connection timed out at {ollama_url}")
        ollama_connected = False
        return []
    except Exception as e:
        logger.warning(f"Error fetching Ollama models: {e}")
        ollama_connected = False
        return []


def query_ollama(image, prompt):
    """Send an image and prompt to Ollama for analysis."""
    global app_config
    
    ollama_url = app_config.get("ollama_url", "http://localhost:11434").rstrip('/')
    ollama_model = app_config.get("ollama_model", "")
    
    if not ollama_model:
        raise Exception("No Ollama model selected. Please select a model in Settings.")
    
    try:
        # Convert PIL Image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Prepare the request payload
        payload = {
            "model": ollama_model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        }
        
        # Send request to Ollama
        response = requests.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=120  # 2 minute timeout for generation
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "No response received from Ollama")
        else:
            error_msg = f"Ollama returned status {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = f"Ollama error: {error_data['error']}"
            except:
                pass
            raise Exception(error_msg)
            
    except requests.exceptions.ConnectionError:
        raise Exception(f"Could not connect to Ollama at {ollama_url}. Make sure Ollama is running.")
    except requests.exceptions.Timeout:
        raise Exception("Ollama request timed out. The model may be taking too long to respond.")
    except Exception as e:
        raise Exception(f"Ollama error: {str(e)}")


# ============== QWEN FUNCTIONS ============== #

def fetch_qwen_models(qwen_api_key=None):
    """Fetch available models from Qwen API."""
    global qwen_available_models, qwen_connected
    
    if qwen_api_key is None:
        qwen_api_key = app_config.get("qwen_api_key", "")
    
    if not qwen_api_key:
        logger.warning("No Qwen API key provided")
        qwen_connected = False
        return []
    
    try:
        # Qwen/DashScope models API
        headers = {
            "Authorization": f"Bearer {qwen_api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://dashscope.aliyuncs.com/api/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            # Filter for vision models (qwen-vl)
            qwen_available_models = [
                m.get("id", "") for m in models 
                if m.get("id") and ("qwen-vl" in m.get("id", "").lower() or "qwen2-vl" in m.get("id", "").lower())
            ]
            
            # If no vision models found, provide common defaults
            if not qwen_available_models:
                qwen_available_models = [
                    "qwen-vl-max",
                    "qwen-vl-plus", 
                    "qwen2-vl-7b-instruct",
                    "qwen-vl-max-latest",
                    "Qwen3-Coder-Plus"
                ]
            
            qwen_connected = True
            logger.info(f"Qwen connected. Found {len(qwen_available_models)} vision models.")
            return qwen_available_models
        elif response.status_code == 401:
            logger.warning("Qwen API key is invalid")
            qwen_connected = False
            return []
        else:
            logger.warning(f"Qwen returned status {response.status_code}")
            # Return default models even if API call fails
            qwen_available_models = [
                "qwen-vl-max",
                "qwen-vl-plus",
                "qwen2-vl-7b-instruct",
                "qwen-vl-max-latest",
                "Qwen3-Coder-Plus"
            ]
            qwen_connected = True
            return qwen_available_models
    except requests.exceptions.ConnectionError:
        logger.warning("Could not connect to Qwen API")
        qwen_connected = False
        # Return default models for offline selection
        qwen_available_models = [
            "qwen-vl-max",
            "qwen-vl-plus",
            "qwen2-vl-7b-instruct",
            "qwen-vl-max-latest",
            "Qwen3-Coder-Plus"
        ]
        return qwen_available_models
    except requests.exceptions.Timeout:
        logger.warning("Qwen API connection timed out")
        qwen_connected = False
        qwen_available_models = [
            "qwen-vl-max",
            "qwen-vl-plus",
            "qwen2-vl-7b-instruct",
            "qwen-vl-max-latest",
            "Qwen3-Coder-Plus"
        ]
        return qwen_available_models
    except Exception as e:
        logger.warning(f"Error fetching Qwen models: {e}")
        qwen_connected = False
        qwen_available_models = [
            "qwen-vl-max",
            "qwen-vl-plus",
            "qwen2-vl-7b-instruct",
            "qwen-vl-max-latest",
            "Qwen3-Coder-Plus"
        ]
        return qwen_available_models


def query_qwen(image, prompt):
    """Send an image and/or prompt to Qwen for analysis. Image is optional for text-only models."""
    global app_config
    
    qwen_api_key = app_config.get("qwen_api_key", "")
    qwen_model = app_config.get("qwen_model", "qwen-vl-max")
    
    if not qwen_api_key:
        raise Exception("No Qwen API key configured. Please add your API key in Settings.")
    
    if not qwen_model:
        raise Exception("No Qwen model selected. Please select a model in Settings.")
    
    # Check if this is a vision model (requires image)
    is_vision_model = "vl" in qwen_model.lower()
    
    try:
        # Prepare the request headers
        headers = {
            "Authorization": f"Bearer {qwen_api_key}",
            "Content-Type": "application/json"
        }
        
        if is_vision_model and image:
            # Vision model with image - use multimodal endpoint
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            payload = {
                "model": qwen_model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "image": f"data:image/png;base64,{image_base64}"
                                },
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
                "parameters": {}
            }
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        elif is_vision_model and not image:
            raise Exception(f"Model {qwen_model} requires an image. Please attach a screenshot.")
        else:
            # Text-only models (including Qwen3-Coder-Plus) - use text generation endpoint
            # Normalize model name to lowercase
            model_name = qwen_model.lower()
            payload = {
                "model": model_name,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {}
            }
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        # Send request to Qwen DashScope API
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=120  # 2 minute timeout for generation
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Handle OpenAI-compatible format (Qwen3 models)
            if "choices" in data:
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        return content
                return "No response received from Qwen"
            
            # Handle DashScope format
            output = data.get("output", {})
            
            # Text generation format
            if "text" in output:
                return output["text"]
            
            # Multimodal format
            choices = output.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", [])
                if isinstance(content, str):
                    return content
                if content:
                    # Content can be a list of text/image parts
                    text_parts = [c.get("text", "") for c in content if c.get("text")]
                    return " ".join(text_parts) if text_parts else "No response received from Qwen"
            return "No response received from Qwen"
        elif response.status_code == 401:
            raise Exception("Invalid Qwen API key. Please check your API key in Settings.")
        elif response.status_code == 429:
            raise Exception("Qwen API rate limit exceeded. Please try again later.")
        else:
            error_msg = f"Qwen returned status {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = f"Qwen error: {error_data['message']}"
            except:
                pass
            raise Exception(error_msg)
            
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to Qwen API. Please check your internet connection.")
    except requests.exceptions.Timeout:
        raise Exception("Qwen request timed out. The model may be taking too long to respond.")
    except Exception as e:
        if "Qwen" in str(e):
            raise
        raise Exception(f"Qwen error: {str(e)}")


def show_loading_indicator():
    """Shows a small blinking logo at the bottom left while Gemini is processing."""
    global loading_indicator, logo_image, app_config
    
    # Close existing indicator if any
    if loading_indicator and loading_indicator.winfo_exists():
        loading_indicator.destroy()
    
    # Create loading indicator window
    loading_indicator = tk.Toplevel()
    loading_indicator.title("")
    loading_indicator.overrideredirect(True)
    
    # Get screen dimensions for bottom-left positioning
    screen_width = loading_indicator.winfo_screenwidth()
    screen_height = loading_indicator.winfo_screenheight()
    
    # Small size - 48x48 logo
    indicator_size = 48
    padding = 20
    x_pos = padding
    y_pos = screen_height - indicator_size - padding - 40  # 40px above taskbar
    
    loading_indicator.geometry(f"{indicator_size}x{indicator_size}+{x_pos}+{y_pos}")
    
    # Make it always on top
    loading_indicator.attributes('-topmost', True)
    loading_indicator.attributes('-alpha', 0.95)
    
    # Apply stealth mode based on settings
    stealth_enabled = app_config.get("stealth_mode", True)
    
    # Make window undetectable (tool window style) - cross-platform with stealth
    apply_window_style(loading_indicator, 'popup', stealth=stealth_enabled)
    
    # Transparent background - cross-platform
    apply_transparency(loading_indicator, '#000000')
    
    # Load and resize logo
    try:
        img = Image.open(LOGO_PATH)
        img = img.resize((indicator_size, indicator_size), Image.Resampling.LANCZOS)
        logo_image = ImageTk.PhotoImage(img)
        
        logo_label = tk.Label(loading_indicator, image=logo_image, bg='#000000', borderwidth=0)
        logo_label.pack()
        
        # Blinking animation
        blink_state = [True]
        def blink():
            if not loading_indicator or not loading_indicator.winfo_exists():
                return
            if blink_state[0]:
                loading_indicator.attributes('-alpha', 0.3)
            else:
                loading_indicator.attributes('-alpha', 0.95)
            blink_state[0] = not blink_state[0]
            loading_indicator.after(400, blink)
        
        # Start blinking
        loading_indicator.after(100, blink)
        
    except Exception as e:
        # Fallback to text if logo not found
        logger.debug(f"Could not load logo: {e}")
        fallback_label = tk.Label(
            loading_indicator,
            text="⚡",
            font=(get_system_font(), 24),
            bg='#1a1a1a',
            fg='#fbbf24'
        )
        fallback_label.pack(expand=True, fill=tk.BOTH)
        
        # Blinking for fallback
        blink_state = [True]
        def blink():
            if not loading_indicator or not loading_indicator.winfo_exists():
                return
            if blink_state[0]:
                fallback_label.config(fg='#fbbf24')
            else:
                fallback_label.config(fg='#78350f')
            blink_state[0] = not blink_state[0]
            loading_indicator.after(400, blink)
        
        loading_indicator.after(100, blink)

def hide_loading_indicator():
    """Hides and destroys the loading indicator."""
    global loading_indicator
    
    if loading_indicator and loading_indicator.winfo_exists():
        # Fade out animation
        def fade_out(alpha=0.95):
            if not loading_indicator or not loading_indicator.winfo_exists():
                return
            if alpha > 0:
                alpha -= 0.15
                loading_indicator.attributes('-alpha', max(0, alpha))
                loading_indicator.after(20, lambda: fade_out(alpha))
            else:
                loading_indicator.destroy()
        
        fade_out()

def show_answer_popup(answer_text):
    """Creates a clean, professional popup window matching the reference design."""
    global popup_window, app_config
    
    # Close existing popup if any
    if popup_window and popup_window.winfo_exists():
        popup_window.destroy()
    
    # Get saved position and theme
    popup_x = app_config.get("popup_x", 200)
    popup_y = app_config.get("popup_y", 80)
    current_theme = app_config.get("theme", "light")
    theme = THEMES[current_theme]
    stealth_enabled = app_config.get("stealth_mode", True)
    
    # Create new popup window
    popup_window = tk.Toplevel()
    popup_window.title("")
    popup_window.geometry(f"480x520+{popup_x}+{popup_y}")
    popup_window.overrideredirect(True)
    
    # Make it always on top
    popup_window.attributes('-topmost', True)
    popup_window.attributes('-alpha', 0.0)
    
    # Prevent window from stealing focus
    popup_window.focus_set = lambda: None
    
    # Make window undetectable - cross-platform with stealth mode
    apply_window_style(popup_window, 'popup', stealth=stealth_enabled)
    
    # Get colors from current theme
    card_bg = theme['card_bg']
    text_color = theme['text_color']
    secondary_text = theme['secondary_text']
    border_color = theme['border_color']
    accent_color = theme['accent_color']
    green_accent = theme['green_accent']
    light_gray = theme['light_gray']
    
    # Make window transparent for rounded corners - cross-platform
    apply_transparency(popup_window, '#000000')
    
    # Main canvas for rounded corners
    canvas = tk.Canvas(popup_window, width=480, height=520, bg='#000000', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Draw rounded rectangle background
    radius = 16
    x1, y1, x2, y2 = 0, 0, 480, 520
    
    # Create rounded rectangle with shadow effect
    canvas.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
    
    # Main card frame on top of canvas
    main_card = tk.Frame(canvas, bg=card_bg)
    canvas.create_window(240, 260, window=main_card, width=476, height=516)
    
    # Top bar with window controls
    top_bar = tk.Frame(main_card, bg=card_bg, height=50)
    top_bar.pack(fill=tk.X)
    top_bar.pack_propagate(False)
    
    # Close button (right side)
    close_btn = tk.Label(
        top_bar,
        text="×",
        font=(get_system_font(), 22),
        bg=card_bg,
        fg='#9ca3af',
        cursor='hand2'
    )
    close_btn.pack(side=tk.RIGHT, padx=16)
    close_btn.bind('<Enter>', lambda e: close_btn.config(fg=theme['close_btn_hover']))
    close_btn.bind('<Leave>', lambda e: close_btn.config(fg=theme['close_btn_fg']))
    close_btn.bind('<Button-1>', lambda e: fade_out_window())
    
    # Separator
    sep1 = tk.Frame(main_card, bg=border_color, height=1)
    sep1.pack(fill=tk.X)
    
    # Header section
    header_section = tk.Frame(main_card, bg=card_bg)
    header_section.pack(fill=tk.X, padx=24, pady=(20, 16))
    
    # Title with icon
    title_row = tk.Frame(header_section, bg=card_bg)
    title_row.pack(fill=tk.X)
    
    # Icon (sparkle/bolt)
    icon_label = tk.Label(
        title_row,
        text="⚡",
        font=(get_system_font(), 16),
        bg=card_bg,
        fg=text_color
    )
    icon_label.pack(side=tk.LEFT, padx=(0, 8))
    
    title_label = tk.Label(
        title_row,
        text="ElAnswer",
        font=(get_system_font(), 15, 'bold'),
        bg=card_bg,
        fg=text_color
    )
    title_label.pack(side=tk.LEFT)
    
    # Subtitle
    subtitle_label = tk.Label(
        header_section,
        text="AI-powered answer to your screen capture",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=secondary_text
    )
    subtitle_label.pack(anchor='w', pady=(6, 0))
    
    # Content section with steps/answer
    content_section = tk.Frame(main_card, bg=card_bg)
    content_section.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 16))
    
    # Answer container with border
    answer_container = tk.Frame(content_section, bg=border_color)
    answer_container.pack(fill=tk.BOTH, expand=True)
    
    answer_inner = tk.Frame(answer_container, bg=light_gray)
    answer_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    
    # Scrollable text area
    text_area = scrolledtext.ScrolledText(
        answer_inner,
        wrap=tk.WORD,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        relief=tk.FLAT,
        padx=16,
        pady=14,
        borderwidth=0,
        highlightthickness=0,
        spacing1=2,
        spacing2=4,
        spacing3=2
    )
    text_area.pack(fill=tk.BOTH, expand=True)
    
    # Insert formatted answer
    text_area.insert(tk.END, answer_text)
    text_area.config(state=tk.NORMAL)
    
    # Store answer text for theme refresh
    popup_window._answer_text = answer_text
    
    # Footer section
    footer_section = tk.Frame(main_card, bg=card_bg)
    footer_section.pack(fill=tk.X, padx=24, pady=(0, 20))
    
    # Status indicator
    status_frame = tk.Frame(footer_section, bg=card_bg)
    status_frame.pack(fill=tk.X, pady=(0, 14))
    
    status_dot = tk.Canvas(status_frame, width=8, height=8, bg=card_bg, highlightthickness=0)
    status_dot.pack(side=tk.LEFT, padx=(0, 6))
    status_dot.create_oval(0, 0, 8, 8, fill=green_accent, outline='')
    
    status_text = tk.Label(
        status_frame,
        text="Response generated successfully",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    status_text.pack(side=tk.LEFT)
    
    # Buttons row
    buttons_frame = tk.Frame(footer_section, bg=card_bg)
    buttons_frame.pack(fill=tk.X)
    
    # Extract code from answer (for Copy Code button)
    def extract_code_from_answer(text):
        """Extract code blocks from the answer text."""
        import re
        # Match code between ``` markers
        code_blocks = re.findall(r'```(?:\w*\n)?(.*?)```', text, re.DOTALL)
        if code_blocks:
            return '\n\n'.join(block.strip() for block in code_blocks)
        # Fallback: return the full text if no code blocks found
        return text
    
    # Copy Code button - extracts code from code blocks, or copies full text if no code blocks
    def copy_code_to_clipboard():
        code = extract_code_from_answer(answer_text)
        popup_window.clipboard_clear()
        popup_window.clipboard_append(code)
        copy_code_btn.config(text="✓ Copied")
        popup_window.after(2000, lambda: copy_code_btn.config(text="📋 Copy Code"))
    
    copy_code_btn = tk.Button(
        buttons_frame,
        text="📋 Copy Code",
        command=copy_code_to_clipboard,
        font=(get_system_font(), 10),
        bg=green_accent,
        fg='white',
        relief=tk.FLAT,
        padx=16,
        pady=8,
        cursor='hand2',
        borderwidth=0,
        activebackground='#16a34a',
        activeforeground='white'
    )
    copy_code_btn.pack(side=tk.LEFT, padx=(0, 8))
    copy_code_btn.bind('<Enter>', lambda e: copy_code_btn.config(bg='#16a34a'))
    copy_code_btn.bind('<Leave>', lambda e: copy_code_btn.config(bg=green_accent))
    
    # Auto-type button - types the response automatically
    auto_type_btn_state = {'typing': False}
    
    def on_auto_type_click():
        if auto_type_btn_state['typing']:
            # Stop typing
            stop_auto_type()
            auto_type_btn.config(text="⌨️ Auto-Type", bg='#6366f1')
            auto_type_btn_state['typing'] = False
        else:
            # Start typing
            start_auto_type(answer_text)
            auto_type_btn.config(text="⏹️ Stop", bg='#ef4444')
            auto_type_btn_state['typing'] = True
            # Reset button after typing completes (check periodically)
            def check_typing():
                if not auto_type_active:
                    auto_type_btn.config(text="⌨️ Auto-Type", bg='#6366f1')
                    auto_type_btn_state['typing'] = False
                elif popup_window and popup_window.winfo_exists():
                    popup_window.after(500, check_typing)
            popup_window.after(1000, check_typing)
    
    auto_type_btn = tk.Button(
        buttons_frame,
        text="⌨️ Auto-Type",
        command=on_auto_type_click,
        font=(get_system_font(), 10),
        bg='#6366f1',
        fg='white',
        relief=tk.FLAT,
        padx=16,
        pady=8,
        cursor='hand2',
        borderwidth=0,
        activebackground='#4f46e5',
        activeforeground='white'
    )
    auto_type_btn.pack(side=tk.LEFT, padx=(0, 8))
    auto_type_btn.bind('<Enter>', lambda e: auto_type_btn.config(bg='#4f46e5' if not auto_type_btn_state['typing'] else '#dc2626'))
    auto_type_btn.bind('<Leave>', lambda e: auto_type_btn.config(bg='#6366f1' if not auto_type_btn_state['typing'] else '#ef4444'))
    
    # Copy button (primary - dark)
    def copy_to_clipboard():
        popup_window.clipboard_clear()
        popup_window.clipboard_append(answer_text)
        copy_btn.config(text="✓ Copied")
        popup_window.after(2000, lambda: copy_btn.config(text="Copy All"))
    
    copy_btn = tk.Button(
        buttons_frame,
        text="Copy All",
        command=copy_to_clipboard,
        font=(get_system_font(), 10),
        bg=accent_color,
        fg='white',
        relief=tk.FLAT,
        padx=20,
        pady=8,
        cursor='hand2',
        borderwidth=0,
        activebackground='#374151',
        activeforeground='white'
    )
    copy_btn.pack(side=tk.LEFT, padx=(0, 8))
    copy_btn.bind('<Enter>', lambda e: copy_btn.config(bg=theme['btn_hover']))
    copy_btn.bind('<Leave>', lambda e: copy_btn.config(bg=accent_color))
    
    # Close button (secondary - outline style)
    close_main_btn = tk.Button(
        buttons_frame,
        text="Close",
        command=lambda: fade_out_window(),
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=text_color,
        relief=tk.SOLID,
        padx=20,
        pady=8,
        cursor='hand2',
        borderwidth=1,
        activebackground=light_gray,
        activeforeground=text_color
    )
    close_main_btn.pack(side=tk.LEFT)
    close_main_btn.bind('<Enter>', lambda e: close_main_btn.config(bg=light_gray))
    close_main_btn.bind('<Leave>', lambda e: close_main_btn.config(bg=card_bg))
    
    # ESC hint
    hint_label = tk.Label(
        buttons_frame,
        text="ESC to close",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg='#9ca3af'
    )
    hint_label.pack(side=tk.RIGHT)
    
    # Animations
    def fade_in(alpha=0.0):
        if alpha < 0.98:
            alpha += 0.1
            popup_window.attributes('-alpha', alpha)
            popup_window.after(15, lambda: fade_in(alpha))
        else:
            popup_window.attributes('-alpha', 0.98)
    
    def save_popup_position():
        """Save current popup position to config."""
        if popup_window and popup_window.winfo_exists():
            app_config["popup_x"] = popup_window.winfo_x()
            app_config["popup_y"] = popup_window.winfo_y()
            save_config(app_config)
    
    def fade_out_window(alpha=0.98):
        if not popup_window or not popup_window.winfo_exists():
            return
        if alpha > 0:
            alpha -= 0.12
            popup_window.attributes('-alpha', alpha)
            popup_window.after(12, lambda: fade_out_window(alpha))
        else:
            save_popup_position()  # Save position before destroying
            popup_window.destroy()
    
    # Status dot pulse
    pulse_state = [True]
    def pulse_status():
        if not popup_window.winfo_exists():
            return
        if pulse_state[0]:
            status_dot.itemconfig(1, fill=theme['pulse_color'])
        else:
            status_dot.itemconfig(1, fill=green_accent)
        pulse_state[0] = not pulse_state[0]
        popup_window.after(1000, pulse_status)
    
    # Bind ESC
    popup_window.bind('<Escape>', lambda e: fade_out_window())
    
    # Draggable window
    def start_move(event):
        popup_window.x = event.x
        popup_window.y = event.y
    
    def do_move(event):
        x = popup_window.winfo_x() + (event.x - popup_window.x)
        y = popup_window.winfo_y() + (event.y - popup_window.y)
        popup_window.geometry(f"+{x}+{y}")
    
    def end_move(event):
        """Save position after drag ends."""
        save_popup_position()
    
    for widget in [top_bar, header_section, title_row, title_label]:
        widget.bind('<Button-1>', start_move)
        widget.bind('<B1-Motion>', do_move)
        widget.bind('<ButtonRelease-1>', end_move)
    
    # Start animations
    popup_window.after(10, fade_in)
    popup_window.after(500, pulse_status)
    
def analyze_screen():
    """Captures screen, sends to Gemini, Ollama, or Qwen, and displays answer in popup."""
    global app_config, model
    
    # Check which provider is enabled
    use_ollama = app_config.get("ollama_enabled", False)
    use_qwen = app_config.get("qwen_enabled", False)
    
    if use_qwen:
        # Validate Qwen configuration
        qwen_api_key = app_config.get("qwen_api_key", "")
        qwen_model = app_config.get("qwen_model", "")
        if not qwen_api_key:
            logger.warning("No Qwen API key configured. Opening settings...")
            root.after(0, show_settings_popup)
            return
        if not qwen_model:
            logger.warning("No Qwen model selected. Opening settings...")
            root.after(0, show_settings_popup)
            return
        backend_name = "Qwen"
    elif use_ollama:
        # Validate Ollama configuration
        ollama_model = app_config.get("ollama_model", "")
        if not ollama_model:
            logger.warning("No Ollama model selected. Opening settings...")
            root.after(0, show_settings_popup)
            return
        backend_name = "Ollama"
    else:
        # Check if API key is configured for Gemini
        if not API_KEY:
            logger.warning("No API key configured. Opening settings...")
            root.after(0, show_settings_popup)
            return
        
        # Check if model is configured
        selected_model = app_config.get("model", "models/gemini-2.0-flash")
        current_model_name = getattr(model, "model_name", None) or getattr(model, "_model", None)
        if (not model) or (current_model_name and current_model_name != selected_model):
            logger.info(f"Model not configured or outdated. Loading: {selected_model}")
            model = genai.GenerativeModel(selected_model)
        if not model:
            logger.error("Failed to configure model. Please check your API key and model.")
            root.after(0, show_settings_popup)
            return
        backend_name = "Gemini"
    
    logger.info(f"Hotkey detected! Capturing screen (using {backend_name})...")
    
    # Show loading indicator on main thread
    root.after(0, show_loading_indicator)
    
    def process_and_display():
        try:
            # 1. Capture the entire screen using cross-platform function
            screenshot = capture_screenshot()
            
            if screenshot is None:
                raise Exception("Failed to capture screenshot")
            
            # 2. visual feedback
            logger.debug(f"Screen captured. Sending to {backend_name}...")
            
            # 3. Prepare the prompt based on settings
            question_mode = app_config.get("question_mode", "mcq")
            show_explanation = app_config.get("show_explanation", True)
            
            if question_mode == "coding":
                # Coding mode - just return the code solution
                prog_lang = app_config.get("programming_language", "Python")
                prompt = (
                    f"Analyze this image containing a coding problem (e.g., LeetCode, HackerRank, etc.).\n\n"
                    f"Provide ONLY the complete, working code solution in {prog_lang}. No explanation needed.\n\n"
                    f"Format your response as:\n\n"
                    f"```{prog_lang.lower()}\n"
                    f"[Your complete code solution here]\n"
                    f"```\n\n"
                    f"Requirements:\n"
                    f"- Provide clean, efficient, and correct {prog_lang} code\n"
                    f"- Include all necessary imports\n"
                    f"- Handle edge cases\n"
                    f"- Note: Do NOT include any comments in the code"
                    f"- Focus on providing a direct code solution without any additional text or explanation"
                    f"- The code tshould satisfy all the sample test cases shown in the image (if any)"
                )
            elif show_explanation:
                prompt = (
                    "Analyze this image. Identify the main question, problem, or code snippet present on the screen.\n\n"
                    "Format your response EXACTLY as follows:\n\n"
                    "📋 QUESTION:\n"
                    "[State the question or problem identified]\n\n"
                    "✅ ANSWER:\n"
                    "[Provide the direct answer. If multiple choice, state the correct option letter and full text]\n\n"
                    "💡 EXPLANATION:\n"
                    "[Provide a clear, concise explanation of why this is correct]\n\n"
                    "Specify any test cases you can identify from the image and whether the answer satisfies them.\n\n"
                    "Keep the response well-organized and easy to read."
                    
                )
            else:
                prompt = (
                    "Analyze this image. Identify the main question, problem, or code snippet present on the screen.\n\n"
                    "Format your response EXACTLY as follows:\n\n"
                    "📋 QUESTION:\n"
                    "[State the question or problem identified]\n\n"
                    "✅ ANSWER:\n"
                    "[Provide the direct answer. If multiple choice, state the correct option letter and full text]\n\n"
                    "Keep the response brief and to the point."
                )

            # 4. Send to appropriate backend
            if use_qwen:
                answer = query_qwen(screenshot, prompt)
            elif use_ollama:
                answer = query_ollama(screenshot, prompt)
            else:
                response = model.generate_content([prompt, screenshot])
                answer = response.text
            
            # 5. Hide loading indicator and display result in popup
            logger.info("Answer received. Displaying popup...")
            
            # Add to history
            add_to_history(answer)
            
            # Auto-copy if enabled
            if app_config.get("auto_copy", False):
                root.after(0, lambda: auto_copy_answer(answer))
            
            # Hide loading indicator and show popup on main thread
            root.after(0, hide_loading_indicator)
            root.after(50, lambda: show_answer_popup(answer))
            
            logger.debug(f"Ready for next query. Press {HOTKEY}...")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            # Hide loading indicator and show error
            root.after(0, hide_loading_indicator)
            root.after(50, lambda: show_answer_popup(error_msg))
    
    # Run analysis in separate thread to avoid blocking
    threading.Thread(target=process_and_display, daemon=True).start()


def auto_copy_answer(answer_text):
    """Auto-copy answer to clipboard."""
    try:
        root.clipboard_clear()
        root.clipboard_append(answer_text)
        logger.debug("Answer auto-copied to clipboard")
    except Exception:
        pass


def quit_application():
    """Gracefully quit the application."""
    global tray_icon, root

    # Stop the tray icon if running
    try:
        if tray_icon:
            tray_icon.stop()
    except Exception as e:
        logger.warning(f"Failed to stop tray icon cleanly: {e}")

    # Safely close the Tk root if it still exists
    if root:
        try:
            if root.winfo_exists():
                try:
                    root.quit()
                except tk.TclError:
                    pass
                try:
                    root.destroy()
                except tk.TclError:
                    pass
        except tk.TclError:
            pass
        except Exception as e:
            logger.warning(f"Error while closing root window: {e}")

    os._exit(0)

def toggle_popup_visibility():
    """Toggle the visibility of the popup window and loading indicator."""
    global popup_window, popup_hidden, loading_indicator
    
    has_popup = popup_window and popup_window.winfo_exists()
    has_loading = loading_indicator and loading_indicator.winfo_exists()
    
    if has_popup or has_loading:
        if popup_hidden:
            # Show the windows
            if has_popup:
                popup_window.deiconify()
                popup_window.attributes('-alpha', 0.98)
            if has_loading:
                loading_indicator.deiconify()
                loading_indicator.attributes('-alpha', 0.95)
            popup_hidden = False
            logger.debug("UI shown")
        else:
            # Hide the windows
            if has_popup:
                popup_window.withdraw()
            if has_loading:
                loading_indicator.withdraw()
            popup_hidden = True
            logger.debug("UI hidden")
    else:
        logger.debug("No UI elements to hide/show")

def show_history_popup():
    """Show the history popup with recent answers."""
    global popup_window, app_config
    
    if not answer_history:
        # Show message if no history
        show_answer_popup("📚 History is empty\n\nCapture some screens first!\nPress Ctrl+Alt+S to start.")
        return
    
    # Close existing popup if any
    if popup_window and popup_window.winfo_exists():
        popup_window.destroy()
    
    # Get saved position and theme
    popup_x = app_config.get("popup_x", 200)
    popup_y = app_config.get("popup_y", 80)
    current_theme = app_config.get("theme", "light")
    theme = THEMES[current_theme]
    stealth_enabled = app_config.get("stealth_mode", True)
    
    # Create new popup window
    popup_window = tk.Toplevel()
    popup_window.title("")
    popup_window.geometry(f"400x450+{popup_x}+{popup_y}")
    popup_window.overrideredirect(True)
    
    # Make it always on top
    popup_window.attributes('-topmost', True)
    popup_window.attributes('-alpha', 0.0)
    
    # Make window undetectable - cross-platform with stealth mode
    apply_window_style(popup_window, 'popup', stealth=stealth_enabled)
    
    # Get colors from current theme
    card_bg = theme['card_bg']
    text_color = theme['text_color']
    secondary_text = theme['secondary_text']
    border_color = theme['border_color']
    accent_color = theme['accent_color']
    light_gray = theme['light_gray']
    
    # Make window transparent for rounded corners - cross-platform
    apply_transparency(popup_window, '#000000')
    
    # Main canvas for rounded corners
    canvas = tk.Canvas(popup_window, width=400, height=450, bg='#000000', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Draw rounded rectangle background
    radius = 16
    x1, y1, x2, y2 = 0, 0, 400, 450
    
    canvas.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
    
    # Main card frame
    main_card = tk.Frame(canvas, bg=card_bg)
    canvas.create_window(200, 225, window=main_card, width=396, height=446)
    
    # Top bar
    top_bar = tk.Frame(main_card, bg=card_bg, height=50)
    top_bar.pack(fill=tk.X)
    top_bar.pack_propagate(False)
    
    # Close button
    close_btn = tk.Label(
        top_bar,
        text="×",
        font=(get_system_font(), 22),
        bg=card_bg,
        fg=theme['close_btn_fg'],
        cursor='hand2'
    )
    close_btn.pack(side=tk.RIGHT, padx=16)
    close_btn.bind('<Enter>', lambda e: close_btn.config(fg=theme['close_btn_hover']))
    close_btn.bind('<Leave>', lambda e: close_btn.config(fg=theme['close_btn_fg']))
    close_btn.bind('<Button-1>', lambda e: fade_out())
    
    # Separator
    sep1 = tk.Frame(main_card, bg=border_color, height=1)
    sep1.pack(fill=tk.X)
    
    # Header
    header_section = tk.Frame(main_card, bg=card_bg)
    header_section.pack(fill=tk.X, padx=20, pady=(16, 12))
    
    title_row = tk.Frame(header_section, bg=card_bg)
    title_row.pack(fill=tk.X)
    
    icon_label = tk.Label(title_row, text="📚", font=(get_system_font(), 14), bg=card_bg, fg=text_color)
    icon_label.pack(side=tk.LEFT, padx=(0, 8))
    
    title_label = tk.Label(title_row, text="Recent Answers", font=(get_system_font(), 14, 'bold'), bg=card_bg, fg=text_color)
    title_label.pack(side=tk.LEFT)
    
    count_label = tk.Label(title_row, text=f"({len(answer_history)})", font=(get_system_font(), 10), bg=card_bg, fg=secondary_text)
    count_label.pack(side=tk.LEFT, padx=(8, 0))
    
    # Scrollable list container
    list_container = tk.Frame(main_card, bg=card_bg)
    list_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))
    
    # Create canvas for scrolling
    list_canvas = tk.Canvas(list_container, bg=card_bg, highlightthickness=0)
    scrollbar = tk.Scrollbar(list_container, orient="vertical", command=list_canvas.yview)
    scrollable_frame = tk.Frame(list_canvas, bg=card_bg)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all"))
    )
    
    list_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=340)
    list_canvas.configure(yscrollcommand=scrollbar.set)
    
    list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Mouse wheel scrolling
    def on_mousewheel(event):
        list_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    list_canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    # Add history items
    for i, entry in enumerate(answer_history):
        item_frame = tk.Frame(scrollable_frame, bg=light_gray, cursor='hand2')
        item_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Inner padding
        inner_frame = tk.Frame(item_frame, bg=light_gray)
        inner_frame.pack(fill=tk.X, padx=12, pady=10)
        
        # Timestamp
        time_label = tk.Label(
            inner_frame,
            text=entry['timestamp'],
            font=(get_system_font(), 8),
            bg=light_gray,
            fg=secondary_text
        )
        time_label.pack(anchor='w')
        
        # Preview
        preview_label = tk.Label(
            inner_frame,
            text=entry['preview'],
            font=(get_system_font(), 10),
            bg=light_gray,
            fg=text_color,
            anchor='w',
            justify='left'
        )
        preview_label.pack(anchor='w', pady=(4, 0))
        
        # Click handler
        answer_text = entry['answer']
        def make_click_handler(text):
            return lambda e: (popup_window.destroy(), root.after(50, lambda: show_answer_popup(text)))
        
        for widget in [item_frame, inner_frame, time_label, preview_label]:
            widget.bind('<Button-1>', make_click_handler(answer_text))
            widget.bind('<Enter>', lambda e, f=item_frame: f.config(bg=border_color) or [w.config(bg=border_color) for w in f.winfo_children()] or [w.config(bg=border_color) for c in f.winfo_children() for w in c.winfo_children()])
            widget.bind('<Leave>', lambda e, f=item_frame: f.config(bg=light_gray) or [w.config(bg=light_gray) for w in f.winfo_children()] or [w.config(bg=light_gray) for c in f.winfo_children() for w in c.winfo_children()])
    
    # Footer with clear button
    footer = tk.Frame(main_card, bg=card_bg)
    footer.pack(fill=tk.X, padx=20, pady=(0, 16))
    
    def clear_history():
        global answer_history
        answer_history = []
        save_history()
        # pystray dynamically rebuilds menu, no explicit update needed
        fade_out()
    
    clear_btn = tk.Button(
        footer,
        text="Clear History",
        command=clear_history,
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text,
        relief=tk.SOLID,
        padx=12,
        pady=4,
        cursor='hand2',
        borderwidth=1
    )
    clear_btn.pack(side=tk.LEFT)
    
    hint_label = tk.Label(footer, text="Click to view", font=(get_system_font(), 9), bg=card_bg, fg='#9ca3af')
    hint_label.pack(side=tk.RIGHT)
    
    # Animations
    def fade_in(alpha=0.0):
        if not popup_window or not popup_window.winfo_exists():
            return
        if alpha < 0.98:
            alpha += 0.1
            popup_window.attributes('-alpha', alpha)
            popup_window.after(15, lambda: fade_in(alpha))
        else:
            popup_window.attributes('-alpha', 0.98)
    
    def fade_out(alpha=0.98):
        if not popup_window or not popup_window.winfo_exists():
            return
        if alpha > 0:
            alpha -= 0.12
            popup_window.attributes('-alpha', alpha)
            popup_window.after(12, lambda: fade_out(alpha))
        else:
            try:
                list_canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            popup_window.destroy()
    
    popup_window.bind('<Escape>', lambda e: fade_out())
    
    # Draggable
    def start_move(event):
        popup_window.x = event.x
        popup_window.y = event.y
    
    def do_move(event):
        x = popup_window.winfo_x() + (event.x - popup_window.x)
        y = popup_window.winfo_y() + (event.y - popup_window.y)
        popup_window.geometry(f"+{x}+{y}")
    
    for widget in [top_bar, header_section, title_row, title_label]:
        widget.bind('<Button-1>', start_move)
        widget.bind('<B1-Motion>', do_move)
    
    popup_window.after(10, fade_in)

def toggle_theme():
    """Toggle between dark and light themes."""
    global app_config, popup_window
    
    current_theme = app_config.get("theme", "light")
    new_theme = "dark" if current_theme == "light" else "light"
    app_config["theme"] = new_theme
    save_config(app_config)
    
    theme_icon = "🌙" if new_theme == "dark" else "☀️"
    logger.info(f"Theme switched to {new_theme} mode {theme_icon}")
    
    # If popup is open, refresh it with the new theme
    if popup_window and popup_window.winfo_exists():
        # Store current answer text and position before destroying
        try:
            # Find the text widget to get current content
            answer_text = getattr(popup_window, '_answer_text', None)
            if answer_text:
                show_answer_popup(answer_text)
        except Exception:
            pass


def toggle_question_mode():
    """Toggle between MCQ and Coding question modes."""
    global app_config
    
    current_mode = app_config.get("question_mode", "mcq")
    new_mode = "coding" if current_mode == "mcq" else "mcq"
    app_config["question_mode"] = new_mode
    save_config(app_config)
    
    mode_icon = "💻" if new_mode == "coding" else "📝"
    mode_name = "Coding" if new_mode == "coding" else "MCQ"
    logger.info(f"Question mode switched to {mode_name} {mode_icon}")
    
    # Show a quick notification popup with language info for coding mode
    if new_mode == "coding":
        lang = app_config.get("programming_language", "Python")
        show_answer_popup(f"{mode_icon} Mode: {mode_name} ({lang})\n\nPress {HOTKEY} to capture screen.")
    else:
        show_answer_popup(f"{mode_icon} Mode: {mode_name}\n\nPress {HOTKEY} to capture screen.")


def copy_last_response():
    """Copy the last response to clipboard."""
    global answer_history, root
    
    if answer_history and len(answer_history) > 0:
        last_answer = answer_history[0].get("answer", "")
        if last_answer:
            try:
                root.clipboard_clear()
                root.clipboard_append(last_answer)
                logger.info("Last response copied to clipboard")
            except Exception as e:
                logger.error(f"Failed to copy to clipboard: {e}")
    else:
        logger.debug("No response to copy")


def start_auto_type(text=None):
    """Start auto-typing the given text or last response at configured WPM."""
    global auto_type_active, auto_type_paused, auto_type_thread, auto_type_stop_event, auto_type_pause_event, answer_history, app_config
    
    # Check if auto-type is enabled
    if not app_config.get("auto_type_enabled", True):
        logger.debug("Auto-type is disabled in settings")
        return
    
    # If already typing, stop it first
    if auto_type_active:
        stop_auto_type()
        return
    
    # Get text to type
    if text is None:
        if answer_history and len(answer_history) > 0:
            text = answer_history[0].get("answer", "")
        else:
            logger.debug("No text to auto-type")
            return
    
    if not text:
        logger.debug("Empty text to auto-type")
        return
    
    # Set up events
    auto_type_stop_event = threading.Event()
    auto_type_pause_event = threading.Event()
    auto_type_pause_event.set()  # Not paused initially
    
    auto_type_active = True
    auto_type_paused = False
    
    # Get WPM from settings
    wpm = app_config.get("auto_type_wpm", 30)
    
    # Calculate delay between characters
    # Average word is 5 characters, so chars per minute = WPM * 5
    # Delay per char = 60 / (WPM * 5) seconds
    char_delay = 60.0 / (wpm * 5)
    
    def type_worker():
        global auto_type_active, auto_type_paused
        
        logger.info(f"Auto-typing started at {wpm} WPM ({len(text)} characters)")
        
        try:
            i = 0
            while i < len(text):
                char = text[i]
                
                # Check if we should stop
                if auto_type_stop_event.is_set():
                    logger.info("Auto-typing stopped by user")
                    break
                
                # Wait if paused
                while not auto_type_pause_event.is_set():
                    if auto_type_stop_event.is_set():
                        break
                    auto_type_stop_event.wait(0.1)
                
                if auto_type_stop_event.is_set():
                    break
                
                # Type the character
                try:
                    if char == '\n':
                        # Type the newline
                        keyboard.press_and_release('enter')
                        auto_type_stop_event.wait(char_delay)
                        
                        # After newline, IDE may auto-indent. Clear any auto-inserted content.
                        # Press Home to go to start of line, then Shift+End to select all, then Delete
                        keyboard.press_and_release('home')
                        auto_type_stop_event.wait(0.01)
                        keyboard.press_and_release('shift+end')
                        auto_type_stop_event.wait(0.01)
                        keyboard.press_and_release('delete')
                        auto_type_stop_event.wait(0.01)
                    else:
                        keyboard.write(char, delay=0)
                except Exception as e:
                    logger.debug(f"Error typing character: {e}")
                
                # Wait for the delay (skip for newline as we already waited)
                if char != '\n':
                    auto_type_stop_event.wait(char_delay)
                
                i += 1
            
            logger.info("Auto-typing completed")
        except Exception as e:
            logger.error(f"Auto-type error: {e}")
        finally:
            auto_type_active = False
            auto_type_paused = False
    
    # Start the typing thread
    auto_type_thread = threading.Thread(target=type_worker, daemon=True)
    auto_type_thread.start()
    
    logger.info(f"Auto-type started. Press {PAUSE_TYPE_HOTKEY} to pause/resume, {AUTO_TYPE_HOTKEY} to stop.")


def stop_auto_type():
    """Stop the currently running auto-type."""
    global auto_type_active, auto_type_paused, auto_type_stop_event
    
    if auto_type_stop_event:
        auto_type_stop_event.set()
    
    auto_type_active = False
    auto_type_paused = False
    logger.info("Auto-type stopped")


def toggle_auto_type_pause(*args):
    """Pause or resume the currently running auto-type."""
    global auto_type_active, auto_type_paused, auto_type_pause_event
    
    if not auto_type_active:
        logger.debug("No auto-type in progress to pause/resume")
        return
    
    if auto_type_pause_event is None:
        logger.debug("Pause event not initialized")
        return
    
    if auto_type_paused:
        # Resume
        auto_type_pause_event.set()
        auto_type_paused = False
        logger.info("Auto-type RESUMED")
    else:
        # Pause
        auto_type_pause_event.clear()
        auto_type_paused = True
        logger.info("Auto-type PAUSED - Right-click to resume")


def auto_type_last_response():
    """Hotkey handler to auto-type the last response."""
    start_auto_type()


def show_settings_popup():
    """Show the settings popup with model selection and other options."""
    global settings_window, app_config, available_models
    
    # Close existing settings window if any
    if settings_window and settings_window.winfo_exists():
        settings_window.destroy()
    
    # Get theme
    current_theme = app_config.get("theme", "light")
    theme = THEMES[current_theme]
    stealth_enabled = app_config.get("stealth_mode", True)
    
    # Create settings window
    settings_window = tk.Toplevel()
    settings_window.title("")
    settings_window.geometry("450x750+250+50")  # Taller for Ollama section
    settings_window.overrideredirect(True)
    
    # Make it always on top
    settings_window.attributes('-topmost', True)
    settings_window.attributes('-alpha', 0.0)
    
    # Make window tool-style (no taskbar), allow input for text fields - with stealth mode
    apply_window_style(settings_window, 'tool', stealth=stealth_enabled, allow_input=True)
    
    # Force focus to allow keyboard input
    settings_window.focus_force()
    
    # Get colors from current theme
    card_bg = theme['card_bg']
    text_color = theme['text_color']
    secondary_text = theme['secondary_text']
    border_color = theme['border_color']
    accent_color = theme['accent_color']
    light_gray = theme['light_gray']
    green_accent = theme['green_accent']

    # Widgets that participate in theme updates
    themed_widgets = []
    
    # Make window transparent for rounded corners - cross-platform
    apply_transparency(settings_window, '#000000')
    
    # Main canvas for rounded corners
    canvas = tk.Canvas(settings_window, width=450, height=750, bg='#000000', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Draw rounded rectangle background
    radius = 16
    x1, y1, x2, y2 = 0, 0, 450, 750
    
    canvas.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
    
    # Main card frame
    main_card = tk.Frame(canvas, bg=card_bg)
    canvas.create_window(225, 375, window=main_card, width=446, height=746)
    
    # Top bar
    top_bar = tk.Frame(main_card, bg=card_bg, height=50)
    top_bar.pack(fill=tk.X)
    top_bar.pack_propagate(False)
    
    # Close button
    close_btn = tk.Label(
        top_bar,
        text="×",
        font=(get_system_font(), 22),
        bg=card_bg,
        fg=theme['close_btn_fg'],
        cursor='hand2'
    )
    close_btn.pack(side=tk.RIGHT, padx=16)
    close_btn.bind('<Enter>', lambda e: close_btn.config(fg=theme['close_btn_hover']))
    close_btn.bind('<Leave>', lambda e: close_btn.config(fg=theme['close_btn_fg']))
    close_btn.bind('<Button-1>', lambda e: fade_out())
    
    # Separator
    sep1 = tk.Frame(main_card, bg=border_color, height=1)
    sep1.pack(fill=tk.X)
    
    # Header
    header_section = tk.Frame(main_card, bg=card_bg)
    header_section.pack(fill=tk.X, padx=24, pady=(20, 16))
    
    title_row = tk.Frame(header_section, bg=card_bg)
    title_row.pack(fill=tk.X)
    
    icon_label = tk.Label(title_row, text="⚙️", font=(get_system_font(), 16), bg=card_bg, fg=text_color)
    icon_label.pack(side=tk.LEFT, padx=(0, 10))
    
    title_label = tk.Label(title_row, text="Settings", font=(get_system_font(), 16, 'bold'), bg=card_bg, fg=text_color)
    title_label.pack(side=tk.LEFT)
    
    # Scrollable content container
    scroll_container = tk.Frame(main_card, bg=card_bg)
    scroll_container.pack(fill=tk.BOTH, expand=True, padx=(24, 4), pady=(0, 16))
    
    # Create canvas and scrollbar
    scroll_canvas = tk.Canvas(scroll_container, bg=card_bg, highlightthickness=0)
    scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=scroll_canvas.yview)
    content_frame = tk.Frame(scroll_canvas, bg=card_bg)
    
    # Configure scroll region
    content_frame.bind(
        "<Configure>",
        lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
    )
    
    scroll_canvas.create_window((0, 0), window=content_frame, anchor="nw")
    scroll_canvas.configure(yscrollcommand=scrollbar.set)
    
    # Pack canvas and scrollbar
    scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 20))
    
    # Enable mousewheel scrolling
    def on_mousewheel(event):
        scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    scroll_canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    # === API KEY SECTION ===
    api_section = tk.Frame(content_frame, bg=card_bg)
    api_section.pack(fill=tk.X, pady=(0, 20))
    
    api_header = tk.Frame(api_section, bg=card_bg)
    api_header.pack(fill=tk.X)
    
    api_icon = tk.Label(api_header, text="🔑", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    api_icon.pack(side=tk.LEFT)
    
    api_title = tk.Label(api_header, text="API Key", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    api_title.pack(side=tk.LEFT, padx=(6, 0))
    
    api_desc = tk.Label(
        api_section,
        text="Enter your Google Gemini API key",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    api_desc.pack(anchor='w', pady=(4, 8))
    
    # API key input frame
    api_input_frame = tk.Frame(api_section, bg=border_color)
    api_input_frame.pack(fill=tk.X)
    
    api_input_inner = tk.Frame(api_input_frame, bg=light_gray)
    api_input_inner.pack(fill=tk.X, padx=1, pady=1)
    
    # Get current API key (masked)
    current_api_key = app_config.get("api_key", "")
    api_key_var = tk.StringVar(value=current_api_key)
    show_key_var = tk.BooleanVar(value=False)
    
    api_entry = tk.Entry(
        api_input_inner,
        textvariable=api_key_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        relief=tk.FLAT,
        show="•"
    )
    api_entry.pack(fill=tk.X, padx=12, pady=10)
    api_entry.focus_set()
    
    # Show/hide toggle
    def toggle_show_key():
        if show_key_var.get():
            api_entry.config(show="")
            show_key_btn.config(text="🙈")
        else:
            api_entry.config(show="•")
            show_key_btn.config(text="👁")
        show_key_var.set(not show_key_var.get())
    
    show_key_btn = tk.Label(
        api_header,
        text="👁",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=secondary_text,
        cursor='hand2'
    )
    show_key_btn.pack(side=tk.RIGHT)
    show_key_btn.bind('<Button-1>', lambda e: toggle_show_key())
    show_key_btn.bind('<Enter>', lambda e: show_key_btn.config(fg=text_color))
    show_key_btn.bind('<Leave>', lambda e: show_key_btn.config(fg=secondary_text))
    
    # Get API key link
    api_link = tk.Label(
        api_section,
        text="Get your API key from Google AI Studio →",
        font=(get_system_font(), 9, 'underline'),
        bg=card_bg,
        fg=accent_color,
        cursor='hand2'
    )
    api_link.pack(anchor='w', pady=(4, 0))
    api_link.bind('<Button-1>', lambda e: open_url("https://makersuite.google.com/app/apikey"))
    
    # Status indicator
    api_status_frame = tk.Frame(api_section, bg=card_bg)
    api_status_frame.pack(fill=tk.X, pady=(8, 0))
    
    if current_api_key:
        api_status = tk.Label(
            api_status_frame,
            text="✓ API key configured",
            font=(get_system_font(), 9),
            bg=card_bg,
            fg=green_accent
        )
    else:
        api_status = tk.Label(
            api_status_frame,
            text="⚠ No API key set",
            font=(get_system_font(), 9),
            bg=card_bg,
            fg='#f59e0b'
        )
    api_status.pack(anchor='w')

    # Save API key button (quick action)
    def save_api_key():
        global API_KEY, app_config
        new_key = api_key_var.get().strip()
        app_config["api_key"] = new_key
        API_KEY = new_key
        save_config(app_config)
        if new_key:
            api_status.config(text="✓ API key saved", fg=green_accent)
            if configure_genai():
                reload_model()
        else:
            api_status.config(text="⚠ No API key set", fg='#f59e0b')

    save_key_btn = tk.Button(
        api_section,
        text="Save API Key",
        command=save_api_key,
        font=(get_system_font(), 10),
        bg=accent_color,
        fg='white',
        relief=tk.FLAT,
        padx=14,
        pady=8,
        cursor='hand2',
        borderwidth=0,
        activebackground=theme['btn_hover'],
        activeforeground='white'
    )
    save_key_btn.pack(anchor='w', pady=(8, 0))
    
    # Register API section widgets for theme updates
    themed_widgets.extend([
        {'widget': api_section, 'type': 'bg_only'},
        {'widget': api_header, 'type': 'bg_only'},
        {'widget': api_icon, 'type': 'text'},
        {'widget': api_title, 'type': 'text'},
        {'widget': api_desc, 'type': 'secondary'},
        {'widget': api_input_inner, 'type': 'light'},
        {'widget': api_entry, 'type': 'dropdown_text'},
        {'widget': show_key_btn, 'type': 'secondary'},
        {'widget': api_status_frame, 'type': 'bg_only'},
        {'widget': save_key_btn, 'type': 'button_accent'},
    ])
    
    # === AI PROVIDER TOGGLE SECTION ===
    provider_section = tk.Frame(content_frame, bg=card_bg)
    provider_section.pack(fill=tk.X, pady=(0, 20))
    
    provider_header = tk.Frame(provider_section, bg=card_bg)
    provider_header.pack(fill=tk.X)
    
    provider_icon = tk.Label(provider_header, text="🤖", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    provider_icon.pack(side=tk.LEFT)
    
    provider_title = tk.Label(provider_header, text="AI Provider", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    provider_title.pack(side=tk.LEFT, padx=(6, 0))
    
    provider_desc = tk.Label(
        provider_section,
        text="Select which AI service to use for analysis",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    provider_desc.pack(anchor='w', pady=(4, 8))
    
    # Provider toggle variable - now uses string for 3-way toggle
    def get_current_provider():
        if app_config.get("qwen_enabled", False):
            return "qwen"
        elif app_config.get("ollama_enabled", False):
            return "ollama"
        return "gemini"
    
    provider_var = tk.StringVar(value=get_current_provider())
    
    # Toggle switch container
    toggle_container = tk.Frame(provider_section, bg=card_bg)
    toggle_container.pack(fill=tk.X, pady=(0, 12))
    
    # Create toggle switch buttons
    toggle_frame = tk.Frame(toggle_container, bg=border_color)
    toggle_frame.pack(anchor='w')
    
    toggle_inner = tk.Frame(toggle_frame, bg=light_gray)
    toggle_inner.pack(padx=1, pady=1)
    
    # Gemini button
    gemini_btn = tk.Frame(toggle_inner, bg=accent_color if provider_var.get() == "gemini" else light_gray, cursor='hand2')
    gemini_btn.pack(side=tk.LEFT)
    
    gemini_content = tk.Frame(gemini_btn, bg=gemini_btn.cget('bg'))
    gemini_content.pack(padx=16, pady=8)
    
    gemini_icon = tk.Label(gemini_content, text="✨", font=(get_system_font(), 10), bg=gemini_btn.cget('bg'), 
                           fg='white' if provider_var.get() == "gemini" else text_color)
    gemini_icon.pack(side=tk.LEFT)
    
    gemini_text = tk.Label(gemini_content, text="Gemini", font=(get_system_font(), 10, 'bold'), 
                           bg=gemini_btn.cget('bg'), fg='white' if provider_var.get() == "gemini" else text_color)
    gemini_text.pack(side=tk.LEFT, padx=(4, 0))
    
    # Ollama button
    ollama_btn = tk.Frame(toggle_inner, bg=accent_color if provider_var.get() == "ollama" else light_gray, cursor='hand2')
    ollama_btn.pack(side=tk.LEFT)
    
    ollama_content = tk.Frame(ollama_btn, bg=ollama_btn.cget('bg'))
    ollama_content.pack(padx=16, pady=8)
    
    ollama_icon_lbl = tk.Label(ollama_content, text="🦙", font=(get_system_font(), 10), bg=ollama_btn.cget('bg'),
                               fg='white' if provider_var.get() == "ollama" else text_color)
    ollama_icon_lbl.pack(side=tk.LEFT)
    
    ollama_text = tk.Label(ollama_content, text="Ollama", font=(get_system_font(), 10, 'bold'),
                           bg=ollama_btn.cget('bg'), fg='white' if provider_var.get() == "ollama" else text_color)
    ollama_text.pack(side=tk.LEFT, padx=(4, 0))
    
    # Qwen button
    qwen_btn = tk.Frame(toggle_inner, bg=accent_color if provider_var.get() == "qwen" else light_gray, cursor='hand2')
    qwen_btn.pack(side=tk.LEFT)
    
    qwen_content = tk.Frame(qwen_btn, bg=qwen_btn.cget('bg'))
    qwen_content.pack(padx=16, pady=8)
    
    qwen_icon_lbl = tk.Label(qwen_content, text="🌟", font=(get_system_font(), 10), bg=qwen_btn.cget('bg'),
                             fg='white' if provider_var.get() == "qwen" else text_color)
    qwen_icon_lbl.pack(side=tk.LEFT)
    
    qwen_text = tk.Label(qwen_content, text="Qwen", font=(get_system_font(), 10, 'bold'),
                         bg=qwen_btn.cget('bg'), fg='white' if provider_var.get() == "qwen" else text_color)
    qwen_text.pack(side=tk.LEFT, padx=(4, 0))
    
    def update_provider_toggle():
        """Update toggle switch visual state for 3-way toggle."""
        current = provider_var.get()
        
        # Reset all to inactive
        for btn, content, icon, text_lbl in [
            (gemini_btn, gemini_content, gemini_icon, gemini_text),
            (ollama_btn, ollama_content, ollama_icon_lbl, ollama_text),
            (qwen_btn, qwen_content, qwen_icon_lbl, qwen_text)
        ]:
            btn.config(bg=light_gray)
            content.config(bg=light_gray)
            icon.config(bg=light_gray, fg=text_color)
            text_lbl.config(bg=light_gray, fg=text_color)
        
        # Activate selected
        if current == "gemini":
            gemini_btn.config(bg=accent_color)
            gemini_content.config(bg=accent_color)
            gemini_icon.config(bg=accent_color, fg='white')
            gemini_text.config(bg=accent_color, fg='white')
        elif current == "ollama":
            ollama_btn.config(bg=accent_color)
            ollama_content.config(bg=accent_color)
            ollama_icon_lbl.config(bg=accent_color, fg='white')
            ollama_text.config(bg=accent_color, fg='white')
        elif current == "qwen":
            qwen_btn.config(bg=accent_color)
            qwen_content.config(bg=accent_color)
            qwen_icon_lbl.config(bg=accent_color, fg='white')
            qwen_text.config(bg=accent_color, fg='white')
    
    def select_gemini(e=None):
        provider_var.set("gemini")
        update_provider_toggle()
    
    def select_ollama(e=None):
        provider_var.set("ollama")
        update_provider_toggle()
    
    def select_qwen(e=None):
        provider_var.set("qwen")
        update_provider_toggle()
    
    # Bind click events
    for widget in [gemini_btn, gemini_content, gemini_icon, gemini_text]:
        widget.bind('<Button-1>', select_gemini)
    
    for widget in [ollama_btn, ollama_content, ollama_icon_lbl, ollama_text]:
        widget.bind('<Button-1>', select_ollama)
    
    for widget in [qwen_btn, qwen_content, qwen_icon_lbl, qwen_text]:
        widget.bind('<Button-1>', select_qwen)
    
    # Register provider toggle widgets for theme updates
    themed_widgets.extend([
        {'widget': provider_section, 'type': 'bg_only'},
        {'widget': provider_header, 'type': 'bg_only'},
        {'widget': provider_icon, 'type': 'text'},
        {'widget': provider_title, 'type': 'text'},
        {'widget': provider_desc, 'type': 'secondary'},
        {'widget': toggle_container, 'type': 'bg_only'},
        {'widget': toggle_inner, 'type': 'light'},
    ])
    
    # === OLLAMA SETTINGS SECTION ===
    ollama_section = tk.Frame(content_frame, bg=card_bg)
    ollama_section.pack(fill=tk.X, pady=(0, 20))
    
    ollama_header = tk.Frame(ollama_section, bg=card_bg)
    ollama_header.pack(fill=tk.X)
    
    ollama_icon = tk.Label(ollama_header, text="⚙️", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    ollama_icon.pack(side=tk.LEFT)
    
    ollama_title = tk.Label(ollama_header, text="Ollama Settings", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    ollama_title.pack(side=tk.LEFT, padx=(6, 0))
    
    ollama_desc = tk.Label(
        ollama_section,
        text="Configure Ollama server connection (local or remote)",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    ollama_desc.pack(anchor='w', pady=(4, 8))
    
    # Ollama URL input
    ollama_url_label = tk.Label(
        ollama_section,
        text="Ollama Server URL:",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    ollama_url_label.pack(anchor='w', pady=(4, 4))
    
    ollama_url_frame = tk.Frame(ollama_section, bg=border_color)
    ollama_url_frame.pack(fill=tk.X)
    
    ollama_url_inner = tk.Frame(ollama_url_frame, bg=light_gray)
    ollama_url_inner.pack(fill=tk.X, padx=1, pady=1)
    
    ollama_url_var = tk.StringVar(value=app_config.get("ollama_url", "http://localhost:11434"))
    
    ollama_url_entry = tk.Entry(
        ollama_url_inner,
        textvariable=ollama_url_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        relief=tk.FLAT
    )
    ollama_url_entry.pack(fill=tk.X, padx=12, pady=10)
    
    ollama_url_hint = tk.Label(
        ollama_section,
        text="e.g., http://your-aws-ip:11434 or http://localhost:11434",
        font=(get_system_font(), 8),
        bg=card_bg,
        fg=secondary_text
    )
    ollama_url_hint.pack(anchor='w', pady=(2, 8))
    
    # Ollama model selection
    ollama_model_label = tk.Label(
        ollama_section,
        text="Ollama Model:",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    ollama_model_label.pack(anchor='w', pady=(4, 4))
    
    ollama_model_frame = tk.Frame(ollama_section, bg=border_color)
    ollama_model_frame.pack(fill=tk.X)
    
    ollama_model_inner = tk.Frame(ollama_model_frame, bg=light_gray)
    ollama_model_inner.pack(fill=tk.X, padx=1, pady=1)
    
    ollama_model_listbox_frame = tk.Frame(ollama_model_inner, bg=light_gray)
    ollama_model_listbox_frame.pack(fill=tk.X)
    
    ollama_current_model_var = tk.StringVar(value=app_config.get("ollama_model", "Select a model..."))
    
    ollama_model_display = tk.Label(
        ollama_model_listbox_frame,
        textvariable=ollama_current_model_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        anchor='w',
        padx=12,
        pady=10,
        cursor='hand2'
    )
    ollama_model_display.pack(fill=tk.X)
    
    ollama_arrow_label = tk.Label(
        ollama_model_listbox_frame,
        text="▼",
        font=(get_system_font(), 8),
        bg=light_gray,
        fg=secondary_text
    )
    ollama_arrow_label.place(relx=0.95, rely=0.5, anchor='center')
    
    # Dropdown list for Ollama models
    ollama_dropdown_list_frame = tk.Frame(ollama_section, bg=border_color)
    ollama_dropdown_listbox = tk.Listbox(
        ollama_dropdown_list_frame,
        font=(get_system_font(), 9),
        bg=light_gray,
        fg=text_color,
        selectbackground=accent_color,
        selectforeground='white',
        relief=tk.FLAT,
        highlightthickness=0,
        height=5,
        activestyle='none'
    )
    
    ollama_dropdown_scrollbar = tk.Scrollbar(ollama_dropdown_list_frame, orient="vertical", command=ollama_dropdown_listbox.yview)
    ollama_dropdown_listbox.configure(yscrollcommand=ollama_dropdown_scrollbar.set)
    
    ollama_dropdown_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
    ollama_dropdown_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    ollama_dropdown_visible = [False]
    
    def populate_ollama_models():
        ollama_dropdown_listbox.delete(0, tk.END)
        if ollama_available_models:
            for m in ollama_available_models:
                ollama_dropdown_listbox.insert(tk.END, m)
        else:
            ollama_dropdown_listbox.insert(tk.END, "No models found - Click refresh")
    
    def toggle_ollama_dropdown(e=None):
        if ollama_dropdown_visible[0]:
            ollama_dropdown_list_frame.pack_forget()
            ollama_dropdown_visible[0] = False
        else:
            ollama_dropdown_list_frame.pack(fill=tk.X, pady=(2, 0))
            ollama_dropdown_visible[0] = True
    
    def select_ollama_model(e=None):
        selection = ollama_dropdown_listbox.curselection()
        if selection:
            selected = ollama_dropdown_listbox.get(selection[0])
            if selected != "No models found - Click refresh":
                ollama_current_model_var.set(selected)
                toggle_ollama_dropdown()
    
    ollama_model_display.bind('<Button-1>', toggle_ollama_dropdown)
    ollama_arrow_label.bind('<Button-1>', toggle_ollama_dropdown)
    ollama_dropdown_listbox.bind('<Double-1>', select_ollama_model)
    ollama_dropdown_listbox.bind('<Return>', select_ollama_model)
    
    # Status and refresh buttons
    ollama_btn_frame = tk.Frame(ollama_section, bg=card_bg)
    ollama_btn_frame.pack(fill=tk.X, pady=(8, 0))
    
    ollama_status = tk.Label(
        ollama_btn_frame,
        text="",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    ollama_status.pack(side=tk.LEFT)
    
    def test_ollama_connection():
        """Test connection to Ollama and fetch models."""
        ollama_refresh_btn.config(text="⏳ Connecting...")
        settings_window.update()
        
        url = ollama_url_var.get().strip()
        models = fetch_ollama_models(url)
        
        if models:
            ollama_status.config(text=f"✓ Connected - {len(models)} models found", fg=green_accent)
            populate_ollama_models()
            # Auto-select first model if none selected
            current = ollama_current_model_var.get()
            if not current or current == "Select a model..." or current not in models:
                ollama_current_model_var.set(models[0])
        else:
            ollama_status.config(text="✗ Connection failed", fg='#ef4444')
            ollama_dropdown_listbox.delete(0, tk.END)
            ollama_dropdown_listbox.insert(tk.END, "No models found - Click refresh")
        
        ollama_refresh_btn.config(text="🔄 Refresh Models")
    
    ollama_refresh_btn = tk.Button(
        ollama_btn_frame,
        text="🔄 Refresh Models",
        command=test_ollama_connection,
        font=(get_system_font(), 9),
        bg=accent_color,
        fg='white',
        relief=tk.FLAT,
        padx=10,
        pady=4,
        cursor='hand2',
        borderwidth=0,
        activebackground=theme['btn_hover'],
        activeforeground='white'
    )
    ollama_refresh_btn.pack(side=tk.RIGHT)
    
    # Populate with existing models if any
    if ollama_available_models:
        populate_ollama_models()
    
    # Register Ollama widgets for theme updates
    themed_widgets.extend([
        {'widget': ollama_section, 'type': 'bg_only'},
        {'widget': ollama_header, 'type': 'bg_only'},
        {'widget': ollama_icon, 'type': 'text'},
        {'widget': ollama_title, 'type': 'text'},
        {'widget': ollama_desc, 'type': 'secondary'},
        {'widget': ollama_url_label, 'type': 'secondary'},
        {'widget': ollama_url_inner, 'type': 'light'},
        {'widget': ollama_url_entry, 'type': 'dropdown_text'},
        {'widget': ollama_url_hint, 'type': 'secondary'},
        {'widget': ollama_model_label, 'type': 'secondary'},
        {'widget': ollama_model_inner, 'type': 'light'},
        {'widget': ollama_model_listbox_frame, 'type': 'light'},
        {'widget': ollama_model_display, 'type': 'dropdown_text'},
        {'widget': ollama_arrow_label, 'type': 'secondary'},
        {'widget': ollama_btn_frame, 'type': 'bg_only'},
        {'widget': ollama_status, 'type': 'secondary'},
        {'widget': ollama_refresh_btn, 'type': 'button_accent'},
    ])
    
    # === QWEN SETTINGS SECTION ===
    qwen_section = tk.Frame(content_frame, bg=card_bg)
    qwen_section.pack(fill=tk.X, pady=(0, 20))
    
    qwen_header = tk.Frame(qwen_section, bg=card_bg)
    qwen_header.pack(fill=tk.X)
    
    qwen_icon = tk.Label(qwen_header, text="🌟", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    qwen_icon.pack(side=tk.LEFT)
    
    qwen_title = tk.Label(qwen_header, text="Qwen Settings", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    qwen_title.pack(side=tk.LEFT, padx=(6, 0))
    
    qwen_desc = tk.Label(
        qwen_section,
        text="Configure Qwen API (Alibaba Cloud DashScope)",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    qwen_desc.pack(anchor='w', pady=(4, 8))
    
    # Qwen API Key input
    qwen_api_label = tk.Label(
        qwen_section,
        text="Qwen API Key:",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    qwen_api_label.pack(anchor='w', pady=(4, 4))
    
    qwen_api_frame = tk.Frame(qwen_section, bg=border_color)
    qwen_api_frame.pack(fill=tk.X)
    
    qwen_api_inner = tk.Frame(qwen_api_frame, bg=light_gray)
    qwen_api_inner.pack(fill=tk.X, padx=1, pady=1)
    
    qwen_api_key_var = tk.StringVar(value=app_config.get("qwen_api_key", ""))
    qwen_show_key_var = tk.BooleanVar(value=False)
    
    qwen_api_entry = tk.Entry(
        qwen_api_inner,
        textvariable=qwen_api_key_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        relief=tk.FLAT,
        show="•"
    )
    qwen_api_entry.pack(fill=tk.X, padx=12, pady=10)
    
    # Show/hide toggle for Qwen API key
    def toggle_qwen_show_key():
        if qwen_show_key_var.get():
            qwen_api_entry.config(show="")
            qwen_show_key_btn.config(text="🙈")
        else:
            qwen_api_entry.config(show="•")
            qwen_show_key_btn.config(text="👁")
        qwen_show_key_var.set(not qwen_show_key_var.get())
    
    qwen_show_key_btn = tk.Label(
        qwen_header,
        text="👁",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=secondary_text,
        cursor='hand2'
    )
    qwen_show_key_btn.pack(side=tk.RIGHT)
    qwen_show_key_btn.bind('<Button-1>', lambda e: toggle_qwen_show_key())
    qwen_show_key_btn.bind('<Enter>', lambda e: qwen_show_key_btn.config(fg=text_color))
    qwen_show_key_btn.bind('<Leave>', lambda e: qwen_show_key_btn.config(fg=secondary_text))
    
    qwen_api_link = tk.Label(
        qwen_section,
        text="Get your API key from Alibaba Cloud DashScope →",
        font=(get_system_font(), 9, 'underline'),
        bg=card_bg,
        fg=accent_color,
        cursor='hand2'
    )
    qwen_api_link.pack(anchor='w', pady=(4, 8))
    qwen_api_link.bind('<Button-1>', lambda e: open_url("https://dashscope.console.aliyun.com/apiKey"))
    
    # Qwen model selection
    qwen_model_label = tk.Label(
        qwen_section,
        text="Qwen Model:",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    qwen_model_label.pack(anchor='w', pady=(4, 4))
    
    qwen_model_frame = tk.Frame(qwen_section, bg=border_color)
    qwen_model_frame.pack(fill=tk.X)
    
    qwen_model_inner = tk.Frame(qwen_model_frame, bg=light_gray)
    qwen_model_inner.pack(fill=tk.X, padx=1, pady=1)
    
    qwen_model_listbox_frame = tk.Frame(qwen_model_inner, bg=light_gray)
    qwen_model_listbox_frame.pack(fill=tk.X)
    
    qwen_current_model_var = tk.StringVar(value=app_config.get("qwen_model", "qwen-vl-max"))
    
    qwen_model_display = tk.Label(
        qwen_model_listbox_frame,
        textvariable=qwen_current_model_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        anchor='w',
        padx=12,
        pady=10,
        cursor='hand2'
    )
    qwen_model_display.pack(fill=tk.X)
    
    qwen_arrow_label = tk.Label(
        qwen_model_listbox_frame,
        text="▼",
        font=(get_system_font(), 8),
        bg=light_gray,
        fg=secondary_text
    )
    qwen_arrow_label.place(relx=0.95, rely=0.5, anchor='center')
    
    # Dropdown list for Qwen models
    qwen_dropdown_list_frame = tk.Frame(qwen_section, bg=border_color)
    qwen_dropdown_listbox = tk.Listbox(
        qwen_dropdown_list_frame,
        font=(get_system_font(), 9),
        bg=light_gray,
        fg=text_color,
        selectbackground=accent_color,
        selectforeground='white',
        relief=tk.FLAT,
        highlightthickness=0,
        height=5,
        activestyle='none'
    )
    
    qwen_dropdown_scrollbar = tk.Scrollbar(qwen_dropdown_list_frame, orient="vertical", command=qwen_dropdown_listbox.yview)
    qwen_dropdown_listbox.configure(yscrollcommand=qwen_dropdown_scrollbar.set)
    
    qwen_dropdown_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
    qwen_dropdown_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    qwen_dropdown_visible = [False]
    
    def populate_qwen_models():
        qwen_dropdown_listbox.delete(0, tk.END)
        if qwen_available_models:
            for m in qwen_available_models:
                qwen_dropdown_listbox.insert(tk.END, m)
        else:
            # Default models
            default_qwen_models = ["qwen-vl-max", "qwen-vl-plus", "qwen2-vl-7b-instruct", "qwen-vl-max-latest", "Qwen3-Coder-Plus"]
            for m in default_qwen_models:
                qwen_dropdown_listbox.insert(tk.END, m)
    
    def toggle_qwen_dropdown(e=None):
        if qwen_dropdown_visible[0]:
            qwen_dropdown_list_frame.pack_forget()
            qwen_dropdown_visible[0] = False
        else:
            qwen_dropdown_list_frame.pack(fill=tk.X, pady=(2, 0))
            qwen_dropdown_visible[0] = True
    
    def select_qwen_model(e=None):
        selection = qwen_dropdown_listbox.curselection()
        if selection:
            selected = qwen_dropdown_listbox.get(selection[0])
            qwen_current_model_var.set(selected)
            toggle_qwen_dropdown()
    
    qwen_model_display.bind('<Button-1>', toggle_qwen_dropdown)
    qwen_arrow_label.bind('<Button-1>', toggle_qwen_dropdown)
    qwen_dropdown_listbox.bind('<Double-1>', select_qwen_model)
    qwen_dropdown_listbox.bind('<Return>', select_qwen_model)
    
    # Status and refresh buttons for Qwen
    qwen_btn_frame = tk.Frame(qwen_section, bg=card_bg)
    qwen_btn_frame.pack(fill=tk.X, pady=(8, 0))
    
    qwen_status = tk.Label(
        qwen_btn_frame,
        text="",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    qwen_status.pack(side=tk.LEFT)
    
    def test_qwen_connection():
        """Test connection to Qwen API and fetch models."""
        qwen_refresh_btn.config(text="⏳ Connecting...")
        settings_window.update()
        
        api_key = qwen_api_key_var.get().strip()
        if not api_key:
            qwen_status.config(text="⚠ Please enter API key first", fg='#f59e0b')
            qwen_refresh_btn.config(text="🔄 Refresh Models")
            return
        
        models = fetch_qwen_models(api_key)
        
        if models:
            qwen_status.config(text=f"✓ Connected - {len(models)} models found", fg=green_accent)
            populate_qwen_models()
            # Auto-select first model if none selected
            current = qwen_current_model_var.get()
            if not current or current not in models:
                qwen_current_model_var.set(models[0])
        else:
            qwen_status.config(text="✗ Connection failed - using defaults", fg='#f59e0b')
            populate_qwen_models()
        
        qwen_refresh_btn.config(text="🔄 Refresh Models")
    
    qwen_refresh_btn = tk.Button(
        qwen_btn_frame,
        text="🔄 Refresh Models",
        command=test_qwen_connection,
        font=(get_system_font(), 9),
        bg=accent_color,
        fg='white',
        relief=tk.FLAT,
        padx=10,
        pady=4,
        cursor='hand2',
        borderwidth=0,
        activebackground=theme['btn_hover'],
        activeforeground='white'
    )
    qwen_refresh_btn.pack(side=tk.RIGHT)
    
    # Populate with default/existing models
    populate_qwen_models()
    
    # Register Qwen widgets for theme updates
    themed_widgets.extend([
        {'widget': qwen_section, 'type': 'bg_only'},
        {'widget': qwen_header, 'type': 'bg_only'},
        {'widget': qwen_icon, 'type': 'text'},
        {'widget': qwen_title, 'type': 'text'},
        {'widget': qwen_desc, 'type': 'secondary'},
        {'widget': qwen_api_label, 'type': 'secondary'},
        {'widget': qwen_api_inner, 'type': 'light'},
        {'widget': qwen_api_entry, 'type': 'dropdown_text'},
        {'widget': qwen_show_key_btn, 'type': 'secondary'},
        {'widget': qwen_api_link, 'type': 'secondary'},
        {'widget': qwen_model_label, 'type': 'secondary'},
        {'widget': qwen_model_inner, 'type': 'light'},
        {'widget': qwen_model_listbox_frame, 'type': 'light'},
        {'widget': qwen_model_display, 'type': 'dropdown_text'},
        {'widget': qwen_arrow_label, 'type': 'secondary'},
        {'widget': qwen_btn_frame, 'type': 'bg_only'},
        {'widget': qwen_status, 'type': 'secondary'},
        {'widget': qwen_refresh_btn, 'type': 'button_accent'},
    ])
    
    # === MODEL SELECTION SECTION ===
    model_section = tk.Frame(content_frame, bg=card_bg)
    model_section.pack(fill=tk.X, pady=(0, 20))
    
    model_header = tk.Frame(model_section, bg=card_bg)
    model_header.pack(fill=tk.X)
    
    model_icon = tk.Label(model_header, text="🤖", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    model_icon.pack(side=tk.LEFT)
    
    model_title = tk.Label(model_header, text="AI Model", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    model_title.pack(side=tk.LEFT, padx=(6, 0))
    
    model_desc = tk.Label(
        model_section,
        text="Select the Gemini model to use for analysis",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    model_desc.pack(anchor='w', pady=(4, 8))
    
    # Model dropdown
    model_var = tk.StringVar(value=app_config.get("model", "models/gemini-2.0-flash"))
    
    # Create a styled frame for the dropdown
    dropdown_frame = tk.Frame(model_section, bg=border_color)
    dropdown_frame.pack(fill=tk.X)
    
    dropdown_inner = tk.Frame(dropdown_frame, bg=light_gray)
    dropdown_inner.pack(fill=tk.X, padx=1, pady=1)
    
    # Get display names for models
    def get_model_display_name(model_name):
        """Convert model path to display name."""
        name = model_name.replace("models/", "")
        return name
    
    # Create listbox for model selection
    model_listbox_frame = tk.Frame(dropdown_inner, bg=light_gray)
    model_listbox_frame.pack(fill=tk.X)
    
    # Current selection display
    current_model_var = tk.StringVar(value=get_model_display_name(app_config.get("model", "models/gemini-2.0-flash")))
    
    model_display = tk.Label(
        model_listbox_frame,
        textvariable=current_model_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        anchor='w',
        padx=12,
        pady=10,
        cursor='hand2'
    )
    model_display.pack(fill=tk.X)
    
    # Dropdown arrow
    arrow_label = tk.Label(
        model_listbox_frame,
        text="▼",
        font=(get_system_font(), 8),
        bg=light_gray,
        fg=secondary_text
    )
    arrow_label.place(relx=0.95, rely=0.5, anchor='center')
    
    # Dropdown list (hidden by default)
    dropdown_list_frame = tk.Frame(model_section, bg=border_color)
    dropdown_listbox = tk.Listbox(
        dropdown_list_frame,
        font=(get_system_font(), 9),
        bg=light_gray,
        fg=text_color,
        selectbackground=accent_color,
        selectforeground='white',
        relief=tk.FLAT,
        highlightthickness=0,
        height=6,
        activestyle='none'
    )
    
    dropdown_scrollbar = tk.Scrollbar(dropdown_list_frame, orient="vertical", command=dropdown_listbox.yview)
    dropdown_listbox.configure(yscrollcommand=dropdown_scrollbar.set)
    
    dropdown_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
    dropdown_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Populate with models
    def populate_models():
        dropdown_listbox.delete(0, tk.END)
        models_to_show = available_models if available_models else [
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro"
        ]
        for m in models_to_show:
            dropdown_listbox.insert(tk.END, get_model_display_name(m))
    
    populate_models()
    
    # Refresh models button
    def refresh_models():
        refresh_btn.config(text="⏳")
        settings_window.update()
        fetch_available_models()
        settings_window.after(1500, lambda: (populate_models(), refresh_btn.config(text="🔄")))
    
    refresh_btn = tk.Label(
        model_header,
        text="🔄",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=secondary_text,
        cursor='hand2'
    )
    refresh_btn.pack(side=tk.RIGHT)
    refresh_btn.bind('<Button-1>', lambda e: refresh_models())
    refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(fg=text_color))
    refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(fg=secondary_text))
    
    dropdown_visible = [False]
    
    def toggle_dropdown(e=None):
        if dropdown_visible[0]:
            dropdown_list_frame.pack_forget()
            dropdown_visible[0] = False
        else:
            dropdown_list_frame.pack(fill=tk.X, pady=(2, 0))
            dropdown_visible[0] = True
    
    def select_model(e=None):
        selection = dropdown_listbox.curselection()
        if selection:
            selected = dropdown_listbox.get(selection[0])
            current_model_var.set(selected)
            model_var.set(f"models/{selected}")
            toggle_dropdown()
    
    model_display.bind('<Button-1>', toggle_dropdown)
    arrow_label.bind('<Button-1>', toggle_dropdown)
    dropdown_listbox.bind('<Double-1>', select_model)
    dropdown_listbox.bind('<Return>', select_model)

    # Apply model button
    def apply_model():
        global app_config
        selected = model_var.get().strip()
        if selected:
            app_config["model"] = selected
            save_config(app_config)
            reload_model()
            model_status.config(text=f"✓ Model set to {get_model_display_name(selected)}", fg=green_accent)

    model_status = tk.Label(
        model_section,
        text="",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text,
        anchor='w'
    )
    model_status.pack(fill=tk.X, pady=(6, 4))

    apply_model_btn = tk.Button(
        model_section,
        text="Set Model",
        command=apply_model,
        font=(get_system_font(), 10),
        bg=accent_color,
        fg='white',
        relief=tk.FLAT,
        padx=14,
        pady=8,
        cursor='hand2',
        borderwidth=0,
        activebackground=theme['btn_hover'],
        activeforeground='white'
    )
    apply_model_btn.pack(anchor='w')
    
    # === THEME SECTION ===
    theme_section = tk.Frame(content_frame, bg=card_bg)
    theme_section.pack(fill=tk.X, pady=(0, 20))
    
    theme_header = tk.Frame(theme_section, bg=card_bg)
    theme_header.pack(fill=tk.X)
    
    theme_icon_lbl = tk.Label(theme_header, text="🎨", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    theme_icon_lbl.pack(side=tk.LEFT)
    
    theme_title = tk.Label(theme_header, text="Appearance", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    theme_title.pack(side=tk.LEFT, padx=(6, 0))
    
    theme_options = tk.Frame(theme_section, bg=card_bg)
    theme_options.pack(fill=tk.X, pady=(10, 0))
    
    theme_var = tk.StringVar(value=app_config.get("theme", "light"))
    
    def apply_theme_realtime(new_theme_name):
        """Apply theme changes in real-time without closing the window."""
        nonlocal card_bg, text_color, secondary_text, border_color, accent_color, light_gray, green_accent
        
        # Update app config
        app_config["theme"] = new_theme_name
        save_config(app_config)
        
        # Get new theme colors
        new_theme = THEMES[new_theme_name]
        card_bg = new_theme['card_bg']
        text_color = new_theme['text_color']
        secondary_text = new_theme['secondary_text']
        border_color = new_theme['border_color']
        accent_color = new_theme['accent_color']
        light_gray = new_theme['light_gray']
        green_accent = new_theme['green_accent']
        
        # Update all themed widgets
        for widget_info in themed_widgets:
            widget = widget_info['widget']
            if not widget.winfo_exists():
                continue
            widget_type = widget_info['type']
            
            if widget_type == 'bg_only':
                widget.config(bg=card_bg)
            elif widget_type == 'text':
                widget.config(bg=card_bg, fg=text_color)
            elif widget_type == 'secondary':
                widget.config(bg=card_bg, fg=secondary_text)
            elif widget_type == 'border':
                widget.config(bg=border_color)
            elif widget_type == 'light':
                widget.config(bg=light_gray)
            elif widget_type == 'spinbox':
                widget.config(bg=light_gray, fg=text_color, buttonbackground=light_gray, highlightbackground=border_color)
            elif widget_type == 'button_accent':
                widget.config(bg=accent_color, activebackground=new_theme['btn_hover'])
            elif widget_type == 'button_secondary':
                widget.config(bg=card_bg, fg=text_color, activebackground=light_gray, activeforeground=text_color)
            elif widget_type == 'main_canvas':
                # Redraw main canvas background with rounded corners
                widget.delete("all")
                radius = 16
                x1, y1, x2, y2 = 0, 0, 450, 750
                widget.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
                widget.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
                widget.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
                widget.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
                widget.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
                widget.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
                # Recreate the main card window
                widget.create_window(225, 375, window=main_card, width=446, height=746)
            elif widget_type == 'canvas':
                widget.config(bg=card_bg)
            elif widget_type == 'dropdown_text':
                widget.config(bg=light_gray, fg=text_color)
            elif widget_type == 'close_btn':
                widget.config(bg=card_bg, fg=new_theme['close_btn_fg'])
    
    def create_theme_button(parent, text, value, icon):
        btn_frame = tk.Frame(parent, bg=accent_color if theme_var.get() == value else light_gray, cursor='hand2')
        btn_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        btn_inner = tk.Frame(btn_frame, bg=light_gray)
        btn_inner.pack(padx=2, pady=2)
        
        btn_content = tk.Frame(btn_inner, bg=light_gray)
        btn_content.pack(padx=16, pady=10)
        
        btn_icon = tk.Label(btn_content, text=icon, font=(get_system_font(), 14), bg=light_gray, fg=text_color)
        btn_icon.pack()
        
        btn_text = tk.Label(btn_content, text=text, font=(get_system_font(), 9), bg=light_gray, fg=text_color)
        btn_text.pack()
        
        # Store widgets for theme updates
        themed_widgets.append({'widget': btn_inner, 'type': 'light'})
        themed_widgets.append({'widget': btn_content, 'type': 'light'})
        themed_widgets.append({'widget': btn_icon, 'type': 'dropdown_text'})
        themed_widgets.append({'widget': btn_text, 'type': 'dropdown_text'})
        
        def on_click(e=None):
            theme_var.set(value)
            # Update button states
            for child in theme_options.winfo_children():
                child.config(bg=light_gray)
            btn_frame.config(bg=accent_color)
            # Apply theme immediately
            apply_theme_realtime(value)
        
        for widget in [btn_frame, btn_inner, btn_content, btn_icon, btn_text]:
            widget.bind('<Button-1>', on_click)
        
        return btn_frame
    
    light_btn = create_theme_button(theme_options, "Light", "light", "☀️")
    dark_btn = create_theme_button(theme_options, "Dark", "dark", "🌙")
    
    # Register main widgets for theme updates
    themed_widgets.extend([
        {'widget': canvas, 'type': 'main_canvas'},
        {'widget': main_card, 'type': 'bg_only'},
        {'widget': top_bar, 'type': 'bg_only'},
        {'widget': close_btn, 'type': 'close_btn'},
        {'widget': header_section, 'type': 'bg_only'},
        {'widget': title_row, 'type': 'bg_only'},
        {'widget': icon_label, 'type': 'text'},
        {'widget': title_label, 'type': 'text'},
        {'widget': scroll_container, 'type': 'bg_only'},
        {'widget': scroll_canvas, 'type': 'canvas'},
        {'widget': content_frame, 'type': 'bg_only'},
        {'widget': model_section, 'type': 'bg_only'},
        {'widget': model_header, 'type': 'bg_only'},
        {'widget': model_icon, 'type': 'text'},
        {'widget': model_title, 'type': 'text'},
        {'widget': model_desc, 'type': 'secondary'},
        {'widget': dropdown_inner, 'type': 'light'},
        {'widget': model_listbox_frame, 'type': 'light'},
        {'widget': model_display, 'type': 'dropdown_text'},
        {'widget': arrow_label, 'type': 'secondary'},
        {'widget': model_status, 'type': 'secondary'},
        {'widget': apply_model_btn, 'type': 'button_accent'},
        {'widget': theme_section, 'type': 'bg_only'},
        {'widget': theme_header, 'type': 'bg_only'},
        {'widget': theme_icon_lbl, 'type': 'text'},
        {'widget': theme_title, 'type': 'text'},
        {'widget': theme_options, 'type': 'bg_only'},
    ])
    
    # === OPTIONS SECTION ===
    options_section = tk.Frame(content_frame, bg=card_bg)
    options_section.pack(fill=tk.X, pady=(0, 20))
    
    options_header = tk.Frame(options_section, bg=card_bg)
    options_header.pack(fill=tk.X)
    
    options_icon = tk.Label(options_header, text="⚡", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    options_icon.pack(side=tk.LEFT)
    
    options_title = tk.Label(options_header, text="Options", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    options_title.pack(side=tk.LEFT, padx=(6, 0))
    
    # Question Mode selector
    mode_frame = tk.Frame(options_section, bg=card_bg)
    mode_frame.pack(fill=tk.X, pady=(10, 0))
    
    mode_label = tk.Label(mode_frame, text="Question Mode:", font=(get_system_font(), 10), bg=card_bg, fg=text_color)
    mode_label.pack(side=tk.LEFT)
    
    mode_var = tk.StringVar(value=app_config.get("question_mode", "mcq"))
    
    mode_buttons_frame = tk.Frame(mode_frame, bg=card_bg)
    mode_buttons_frame.pack(side=tk.LEFT, padx=(10, 0))
    
    def create_mode_button(parent, text, value, icon):
        is_selected = mode_var.get() == value
        btn_frame = tk.Frame(parent, bg=accent_color if is_selected else light_gray, cursor='hand2')
        btn_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        btn_inner = tk.Frame(btn_frame, bg=light_gray)
        btn_inner.pack(padx=2, pady=2)
        
        btn_content = tk.Frame(btn_inner, bg=light_gray)
        btn_content.pack(padx=12, pady=6)
        
        btn_icon = tk.Label(btn_content, text=icon, font=(get_system_font(), 10), bg=light_gray, fg=text_color)
        btn_icon.pack(side=tk.LEFT)
        
        btn_text = tk.Label(btn_content, text=text, font=(get_system_font(), 9), bg=light_gray, fg=text_color)
        btn_text.pack(side=tk.LEFT, padx=(4, 0))
        
        def on_click(e=None):
            mode_var.set(value)
            # Update all mode button states
            for child in mode_buttons_frame.winfo_children():
                child.config(bg=light_gray)
            btn_frame.config(bg=accent_color)
        
        for widget in [btn_frame, btn_inner, btn_content, btn_icon, btn_text]:
            widget.bind('<Button-1>', on_click)
        
        # Register for theme updates
        themed_widgets.extend([
            {'widget': btn_inner, 'type': 'light'},
            {'widget': btn_content, 'type': 'light'},
            {'widget': btn_icon, 'type': 'dropdown_text'},
            {'widget': btn_text, 'type': 'dropdown_text'},
        ])
        
        return btn_frame
    
    mcq_btn = create_mode_button(mode_buttons_frame, "MCQ", "mcq", "📝")
    coding_btn = create_mode_button(mode_buttons_frame, "Coding", "coding", "💻")
    
    mode_desc = tk.Label(
        options_section,
        text="MCQ: For multiple choice questions | Coding: For LeetCode-style problems (code only)",
        font=(get_system_font(), 8),
        bg=card_bg,
        fg=secondary_text
    )
    mode_desc.pack(anchor='w', padx=(0, 0), pady=(4, 0))
    
    # Programming Language selector (for coding mode)
    lang_frame = tk.Frame(options_section, bg=card_bg)
    lang_frame.pack(fill=tk.X, pady=(10, 0))
    
    lang_label = tk.Label(lang_frame, text="Programming Language:", font=(get_system_font(), 10), bg=card_bg, fg=text_color)
    lang_label.pack(side=tk.LEFT)
    
    LANGUAGES = ["Python", "Java", "C++", "JavaScript", "TypeScript", "Go", "Rust", "C#", "C", "Ruby", "Swift", "Kotlin"]
    lang_var = tk.StringVar(value=app_config.get("programming_language", "Python"))
    
    lang_dropdown_frame = tk.Frame(lang_frame, bg=border_color)
    lang_dropdown_frame.pack(side=tk.LEFT, padx=(10, 0))
    
    lang_dropdown_inner = tk.Frame(lang_dropdown_frame, bg=light_gray)
    lang_dropdown_inner.pack(padx=1, pady=1)
    
    lang_display = tk.Label(
        lang_dropdown_inner,
        textvariable=lang_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        padx=12,
        pady=6,
        cursor='hand2',
        width=12,
        anchor='w'
    )
    lang_display.pack(side=tk.LEFT)
    
    lang_arrow = tk.Label(
        lang_dropdown_inner,
        text="▼",
        font=(get_system_font(), 8),
        bg=light_gray,
        fg=secondary_text
    )
    lang_arrow.pack(side=tk.LEFT, padx=(0, 8))
    
    # Language dropdown list
    lang_dropdown_list = tk.Frame(options_section, bg=border_color)
    lang_listbox = tk.Listbox(
        lang_dropdown_list,
        font=(get_system_font(), 9),
        bg=light_gray,
        fg=text_color,
        selectbackground=accent_color,
        selectforeground='white',
        relief=tk.FLAT,
        highlightthickness=0,
        height=6,
        activestyle='none'
    )
    
    for lang in LANGUAGES:
        lang_listbox.insert(tk.END, lang)
    
    lang_scrollbar = tk.Scrollbar(lang_dropdown_list, orient="vertical", command=lang_listbox.yview)
    lang_listbox.configure(yscrollcommand=lang_scrollbar.set)
    
    lang_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
    lang_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    lang_dropdown_visible = [False]
    
    def toggle_lang_dropdown(e=None):
        if lang_dropdown_visible[0]:
            lang_dropdown_list.pack_forget()
            lang_dropdown_visible[0] = False
        else:
            lang_dropdown_list.pack(fill=tk.X, pady=(2, 0))
            lang_dropdown_visible[0] = True
    
    def select_lang(e=None):
        selection = lang_listbox.curselection()
        if selection:
            selected = lang_listbox.get(selection[0])
            lang_var.set(selected)
            toggle_lang_dropdown()
    
    lang_display.bind('<Button-1>', toggle_lang_dropdown)
    lang_arrow.bind('<Button-1>', toggle_lang_dropdown)
    lang_listbox.bind('<Double-1>', select_lang)
    lang_listbox.bind('<Return>', select_lang)
    
    lang_hint = tk.Label(
        options_section,
        text="Language used when Coding mode is active",
        font=(get_system_font(), 8),
        bg=card_bg,
        fg=secondary_text
    )
    lang_hint.pack(anchor='w', pady=(4, 0))
    
    # Register mode and language widgets for theme updates
    themed_widgets.extend([
        {'widget': mode_frame, 'type': 'bg_only'},
        {'widget': mode_label, 'type': 'text'},
        {'widget': mode_buttons_frame, 'type': 'bg_only'},
        {'widget': mode_desc, 'type': 'secondary'},
        {'widget': lang_frame, 'type': 'bg_only'},
        {'widget': lang_label, 'type': 'text'},
        {'widget': lang_dropdown_inner, 'type': 'light'},
        {'widget': lang_display, 'type': 'dropdown_text'},
        {'widget': lang_arrow, 'type': 'secondary'},
        {'widget': lang_hint, 'type': 'secondary'},
    ])
    
    # Checkboxes
    auto_copy_var = tk.BooleanVar(value=app_config.get("auto_copy", False))
    show_explanation_var = tk.BooleanVar(value=app_config.get("show_explanation", True))
    compact_mode_var = tk.BooleanVar(value=app_config.get("compact_mode", False))
    stealth_mode_var = tk.BooleanVar(value=app_config.get("stealth_mode", True))
    
    def create_checkbox(parent, text, variable, description=""):
        cb_frame = tk.Frame(parent, bg=card_bg)
        cb_frame.pack(fill=tk.X, pady=(10, 0))
        
        cb_row = tk.Frame(cb_frame, bg=card_bg)
        cb_row.pack(fill=tk.X)
        
        # Custom checkbox
        cb_box = tk.Frame(cb_row, bg=border_color, width=20, height=20, cursor='hand2')
        cb_box.pack(side=tk.LEFT)
        cb_box.pack_propagate(False)
        
        cb_inner = tk.Frame(cb_box, bg=light_gray)
        cb_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        cb_check = tk.Label(cb_inner, text="", font=(get_system_font(), 10), bg=light_gray, fg=accent_color)
        cb_check.pack(expand=True)
        
        def update_checkbox():
            if variable.get():
                cb_check.config(text="✓")
                cb_box.config(bg=accent_color)
            else:
                cb_check.config(text="")
                cb_box.config(bg=border_color)
        
        def toggle_cb(e=None):
            variable.set(not variable.get())
            update_checkbox()
        
        update_checkbox()
        
        for widget in [cb_box, cb_inner, cb_check]:
            widget.bind('<Button-1>', toggle_cb)
        
        cb_label = tk.Label(cb_row, text=text, font=(get_system_font(), 10), bg=card_bg, fg=text_color, cursor='hand2')
        cb_label.pack(side=tk.LEFT, padx=(10, 0))
        cb_label.bind('<Button-1>', toggle_cb)
        
        desc_label = None
        if description:
            desc_label = tk.Label(cb_frame, text=description, font=(get_system_font(), 8), bg=card_bg, fg=secondary_text)
            desc_label.pack(anchor='w', padx=(30, 0))
        
        # Register widgets for theme updates
        themed_widgets.extend([
            {'widget': cb_frame, 'type': 'bg_only'},
            {'widget': cb_row, 'type': 'bg_only'},
            {'widget': cb_inner, 'type': 'light'},
            {'widget': cb_check, 'type': 'light'},
            {'widget': cb_label, 'type': 'text'},
        ])
        if desc_label:
            themed_widgets.append({'widget': desc_label, 'type': 'secondary'})
        
        return cb_frame
    
    # Register options section widgets
    themed_widgets.extend([
        {'widget': options_section, 'type': 'bg_only'},
        {'widget': options_header, 'type': 'bg_only'},
        {'widget': options_icon, 'type': 'text'},
        {'widget': options_title, 'type': 'text'},
    ])
    
    create_checkbox(options_section, "Auto-copy answers to clipboard", auto_copy_var, "Automatically copy each answer when received")
    create_checkbox(options_section, "Show detailed explanations", show_explanation_var, "Include step-by-step explanations in answers")
    create_checkbox(options_section, "Compact mode", compact_mode_var, "Use smaller popup windows")
    create_checkbox(options_section, "🔒 Stealth mode (hide from screen share)", stealth_mode_var, "Hide windows from screen capture, sharing, and proctoring software")
    
    # === HISTORY LIMIT SECTION ===
    history_section = tk.Frame(content_frame, bg=card_bg)
    history_section.pack(fill=tk.X, pady=(0, 10))
    
    history_header = tk.Frame(history_section, bg=card_bg)
    history_header.pack(fill=tk.X)
    
    history_icon = tk.Label(history_header, text="📚", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    history_icon.pack(side=tk.LEFT)
    
    history_title = tk.Label(history_header, text="History Limit", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    history_title.pack(side=tk.LEFT, padx=(6, 0))
    
    history_row = tk.Frame(history_section, bg=card_bg)
    history_row.pack(fill=tk.X, pady=(10, 0))
    
    max_history_var = tk.IntVar(value=app_config.get("max_history", 10))
    
    history_label = tk.Label(history_row, text="Maximum items:", font=(get_system_font(), 10), bg=card_bg, fg=text_color)
    history_label.pack(side=tk.LEFT)
    
    history_spinbox = tk.Spinbox(
        history_row,
        from_=5,
        to=50,
        textvariable=max_history_var,
        width=5,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        buttonbackground=light_gray,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=border_color
    )
    history_spinbox.pack(side=tk.LEFT, padx=(10, 0))
    
    # Register history section widgets
    themed_widgets.extend([
        {'widget': history_section, 'type': 'bg_only'},
        {'widget': history_header, 'type': 'bg_only'},
        {'widget': history_icon, 'type': 'text'},
        {'widget': history_title, 'type': 'text'},
        {'widget': history_row, 'type': 'bg_only'},
        {'widget': history_label, 'type': 'text'},
        {'widget': history_spinbox, 'type': 'spinbox'},
    ])
    
    # === AUTO-TYPE SECTION ===
    autotype_section = tk.Frame(content_frame, bg=card_bg)
    autotype_section.pack(fill=tk.X, pady=(0, 20))
    
    autotype_header = tk.Frame(autotype_section, bg=card_bg)
    autotype_header.pack(fill=tk.X)
    
    autotype_icon = tk.Label(autotype_header, text="⌨️", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
    autotype_icon.pack(side=tk.LEFT)
    
    autotype_title = tk.Label(autotype_header, text="Auto-Type", font=(get_system_font(), 11, 'bold'), bg=card_bg, fg=text_color)
    autotype_title.pack(side=tk.LEFT, padx=(6, 0))
    
    autotype_desc = tk.Label(
        autotype_section,
        text="Automatically type responses at a natural speed",
        font=(get_system_font(), 9),
        bg=card_bg,
        fg=secondary_text
    )
    autotype_desc.pack(anchor='w', pady=(4, 8))
    
    # Enable auto-type checkbox
    auto_type_enabled_var = tk.BooleanVar(value=app_config.get("auto_type_enabled", True))
    
    autotype_enable_frame = tk.Frame(autotype_section, bg=card_bg)
    autotype_enable_frame.pack(fill=tk.X, pady=(0, 8))
    
    autotype_cb_box = tk.Frame(autotype_enable_frame, bg=border_color, width=20, height=20, cursor='hand2')
    autotype_cb_box.pack(side=tk.LEFT)
    autotype_cb_box.pack_propagate(False)
    
    autotype_cb_inner = tk.Frame(autotype_cb_box, bg=light_gray)
    autotype_cb_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    
    autotype_cb_check = tk.Label(autotype_cb_inner, text="", font=(get_system_font(), 10), bg=light_gray, fg=accent_color)
    autotype_cb_check.pack(expand=True)
    
    def update_autotype_checkbox():
        if auto_type_enabled_var.get():
            autotype_cb_check.config(text="✓")
            autotype_cb_box.config(bg=accent_color)
        else:
            autotype_cb_check.config(text="")
            autotype_cb_box.config(bg=border_color)
    
    def toggle_autotype_cb(e=None):
        auto_type_enabled_var.set(not auto_type_enabled_var.get())
        update_autotype_checkbox()
    
    update_autotype_checkbox()
    
    for widget in [autotype_cb_box, autotype_cb_inner, autotype_cb_check]:
        widget.bind('<Button-1>', toggle_autotype_cb)
    
    autotype_enable_label = tk.Label(autotype_enable_frame, text="Enable auto-type feature", font=(get_system_font(), 10), bg=card_bg, fg=text_color, cursor='hand2')
    autotype_enable_label.pack(side=tk.LEFT, padx=(10, 0))
    autotype_enable_label.bind('<Button-1>', toggle_autotype_cb)
    
    # WPM setting
    wpm_row = tk.Frame(autotype_section, bg=card_bg)
    wpm_row.pack(fill=tk.X, pady=(4, 0))
    
    auto_type_wpm_var = tk.IntVar(value=app_config.get("auto_type_wpm", 30))
    
    wpm_label = tk.Label(wpm_row, text="Typing speed (WPM):", font=(get_system_font(), 10), bg=card_bg, fg=text_color)
    wpm_label.pack(side=tk.LEFT)
    
    wpm_spinbox = tk.Spinbox(
        wpm_row,
        from_=10,
        to=200,
        textvariable=auto_type_wpm_var,
        width=5,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        buttonbackground=light_gray,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=border_color
    )
    wpm_spinbox.pack(side=tk.LEFT, padx=(10, 0))
    
    wpm_hint = tk.Label(
        autotype_section,
        text=f"Hotkeys: {AUTO_TYPE_HOTKEY} (start/stop), {PAUSE_TYPE_HOTKEY} (pause/resume)",
        font=(get_system_font(), 8),
        bg=card_bg,
        fg=secondary_text
    )
    wpm_hint.pack(anchor='w', pady=(8, 0))
    
    # Register auto-type section widgets
    themed_widgets.extend([
        {'widget': autotype_section, 'type': 'bg_only'},
        {'widget': autotype_header, 'type': 'bg_only'},
        {'widget': autotype_icon, 'type': 'text'},
        {'widget': autotype_title, 'type': 'text'},
        {'widget': autotype_desc, 'type': 'secondary'},
        {'widget': autotype_enable_frame, 'type': 'bg_only'},
        {'widget': autotype_cb_inner, 'type': 'light'},
        {'widget': autotype_cb_check, 'type': 'light'},
        {'widget': autotype_enable_label, 'type': 'text'},
        {'widget': wpm_row, 'type': 'bg_only'},
        {'widget': wpm_label, 'type': 'text'},
        {'widget': wpm_spinbox, 'type': 'spinbox'},
        {'widget': wpm_hint, 'type': 'secondary'},
    ])
    
    # === FOOTER WITH SAVE BUTTON ===
    footer = tk.Frame(main_card, bg=card_bg)
    footer.pack(fill=tk.X, padx=24, pady=(0, 20))
    
    def save_settings():
        global app_config, MAX_HISTORY_ITEMS, API_KEY
        
        # Update API key
        new_api_key = api_key_var.get().strip()
        api_key_changed = new_api_key != app_config.get("api_key", "")
        app_config["api_key"] = new_api_key
        API_KEY = new_api_key
        
        # Update provider config based on 3-way toggle
        current_provider = provider_var.get()
        app_config["ollama_enabled"] = (current_provider == "ollama")
        app_config["qwen_enabled"] = (current_provider == "qwen")
        
        # Update Ollama config
        app_config["ollama_url"] = ollama_url_var.get().strip()
        ollama_model_selected = ollama_current_model_var.get()
        if ollama_model_selected and ollama_model_selected != "Select a model...":
            app_config["ollama_model"] = ollama_model_selected
        
        # Update Qwen config
        app_config["qwen_api_key"] = qwen_api_key_var.get().strip()
        qwen_model_selected = qwen_current_model_var.get()
        if qwen_model_selected:
            app_config["qwen_model"] = qwen_model_selected
        
        # Update config
        app_config["model"] = model_var.get()
        app_config["theme"] = theme_var.get()
        app_config["auto_copy"] = auto_copy_var.get()
        app_config["show_explanation"] = show_explanation_var.get()
        app_config["compact_mode"] = compact_mode_var.get()
        app_config["stealth_mode"] = stealth_mode_var.get()
        app_config["question_mode"] = mode_var.get()
        app_config["programming_language"] = lang_var.get()
        app_config["max_history"] = max_history_var.get()
        
        # Update auto-type settings
        app_config["auto_type_enabled"] = auto_type_enabled_var.get()
        app_config["auto_type_wpm"] = auto_type_wpm_var.get()
        
        # Update MAX_HISTORY_ITEMS
        MAX_HISTORY_ITEMS = max_history_var.get()
        
        # Save to file
        save_config(app_config)
        
        # Reconfigure API if key changed (only if using Gemini)
        if current_provider == "gemini":
            if api_key_changed and new_api_key:
                configure_genai()
            else:
                # Reload model if changed
                reload_model()
        
        # pystray dynamically rebuilds menu on each click, no explicit update needed
        
        # Show confirmation
        save_btn.config(text="✓ Saved!")
        settings_window.after(1500, lambda: fade_out())
    
    save_btn = tk.Button(
        footer,
        text="Save Settings",
        command=save_settings,
        font=(get_system_font(), 11),
        bg=accent_color,
        fg='white',
        relief=tk.FLAT,
        padx=24,
        pady=10,
        cursor='hand2',
        borderwidth=0,
        activebackground=theme['btn_hover'],
        activeforeground='white'
    )
    save_btn.pack(side=tk.LEFT)
    
    # Store original hover handlers for save button
    def save_btn_enter(e):
        current_theme = app_config.get("theme", "light")
        save_btn.config(bg=THEMES[current_theme]['btn_hover'])
    
    def save_btn_leave(e):
        current_theme = app_config.get("theme", "light")
        save_btn.config(bg=THEMES[current_theme]['accent_color'])
    
    save_btn.bind('<Enter>', save_btn_enter)
    save_btn.bind('<Leave>', save_btn_leave)
    
    cancel_btn = tk.Button(
        footer,
        text="Cancel",
        command=lambda: fade_out(),
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=text_color,
        relief=tk.SOLID,
        padx=16,
        pady=8,
        cursor='hand2',
        borderwidth=1,
        activebackground=light_gray,
        activeforeground=text_color
    )
    cancel_btn.pack(side=tk.LEFT, padx=(10, 0))
    
    # Register button widgets
    themed_widgets.extend([
        {'widget': save_btn, 'type': 'button_accent'},
        {'widget': cancel_btn, 'type': 'button_secondary'},
    ])
    
    # ESC hint
    hint_label = tk.Label(footer, text="ESC to close", font=(get_system_font(), 9), bg=card_bg, fg='#9ca3af')
    hint_label.pack(side=tk.RIGHT)
    
    # Register footer widgets
    themed_widgets.extend([
        {'widget': footer, 'type': 'bg_only'},
        {'widget': hint_label, 'type': 'secondary'},
    ])
    
    # Animations
    def fade_in(alpha=0.0):
        if not settings_window or not settings_window.winfo_exists():
            return
        if alpha < 0.98:
            alpha += 0.1
            settings_window.attributes('-alpha', alpha)
            settings_window.after(15, lambda: fade_in(alpha))
        else:
            settings_window.attributes('-alpha', 0.98)
    
    def fade_out(alpha=0.98):
        if not settings_window or not settings_window.winfo_exists():
            return
        if alpha > 0:
            alpha -= 0.12
            settings_window.attributes('-alpha', alpha)
            settings_window.after(12, lambda: fade_out(alpha))
        else:
            try:
                scroll_canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            settings_window.destroy()
    
    settings_window.bind('<Escape>', lambda e: fade_out())
    
    # Draggable
    def start_move(event):
        settings_window.x = event.x
        settings_window.y = event.y
    
    def do_move(event):
        x = settings_window.winfo_x() + (event.x - settings_window.x)
        y = settings_window.winfo_y() + (event.y - settings_window.y)
        settings_window.geometry(f"+{x}+{y}")
    
    for widget in [top_bar, header_section, title_row, title_label]:
        widget.bind('<Button-1>', start_move)
        widget.bind('<B1-Motion>', do_move)
    
    settings_window.after(10, fade_in)


def show_chat_window():
    """Show a ChatGPT-style interface for custom prompts with screenshot support."""
    global chat_window, app_config, available_models, qwen_available_models
    
    # Close existing chat window if any
    if chat_window and chat_window.winfo_exists():
        chat_window.destroy()
    
    # Get theme
    current_theme = app_config.get("theme", "light")
    theme = THEMES[current_theme]
    stealth_enabled = app_config.get("stealth_mode", True)
    
    # Create chat window
    chat_window = tk.Toplevel()
    chat_window.title("")
    chat_window.geometry("700x800+100+50")
    chat_window.overrideredirect(True)
    
    # Make it always on top
    chat_window.attributes('-topmost', True)
    chat_window.attributes('-alpha', 0.0)
    
    # Apply window style with stealth mode
    apply_window_style(chat_window, 'tool', stealth=stealth_enabled, allow_input=True)
    
    # Force focus
    chat_window.focus_force()
    
    # Get colors from current theme
    card_bg = theme['card_bg']
    text_color = theme['text_color']
    secondary_text = theme['secondary_text']
    border_color = theme['border_color']
    accent_color = theme['accent_color']
    light_gray = theme['light_gray']
    green_accent = theme['green_accent']
    
    # Chat state
    chat_messages = []  # List of {"role": "user"/"assistant", "content": str, "image": PIL.Image or None}
    attached_screenshot = [None]  # Mutable container for attached screenshot
    
    # Apply transparency
    apply_transparency(chat_window, '#000000')
    
    # Main canvas for rounded corners
    canvas = tk.Canvas(chat_window, width=700, height=800, bg='#000000', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Draw rounded rectangle background
    radius = 16
    x1, y1, x2, y2 = 0, 0, 700, 800
    
    canvas.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
    
    # Main card frame
    main_card = tk.Frame(canvas, bg=card_bg)
    canvas.create_window(350, 400, window=main_card, width=696, height=796)
    
    # Top bar
    top_bar = tk.Frame(main_card, bg=card_bg, height=50)
    top_bar.pack(fill=tk.X)
    top_bar.pack_propagate(False)
    
    # Title
    title_row = tk.Frame(top_bar, bg=card_bg)
    title_row.pack(side=tk.LEFT, padx=16, pady=12)
    
    title_icon = tk.Label(title_row, text="💬", font=(get_system_font(), 14), bg=card_bg, fg=text_color)
    title_icon.pack(side=tk.LEFT)
    
    title_label = tk.Label(title_row, text="ElAnswer Chat", font=(get_system_font(), 14, 'bold'), bg=card_bg, fg=text_color)
    title_label.pack(side=tk.LEFT, padx=(8, 0))
    
    # Close button
    def fade_out(alpha=0.98):
        if not chat_window or not chat_window.winfo_exists():
            return
        if alpha > 0:
            alpha -= 0.12
            chat_window.attributes('-alpha', alpha)
            chat_window.after(12, lambda: fade_out(alpha))
        else:
            chat_window.destroy()
    
    close_btn = tk.Label(
        top_bar,
        text="×",
        font=(get_system_font(), 22),
        bg=card_bg,
        fg=theme['close_btn_fg'],
        cursor='hand2'
    )
    close_btn.pack(side=tk.RIGHT, padx=16)
    close_btn.bind('<Enter>', lambda e: close_btn.config(fg=theme['close_btn_hover']))
    close_btn.bind('<Leave>', lambda e: close_btn.config(fg=theme['close_btn_fg']))
    close_btn.bind('<Button-1>', lambda e: fade_out())
    
    # Separator
    sep1 = tk.Frame(main_card, bg=border_color, height=1)
    sep1.pack(fill=tk.X)
    
    # === MODEL SELECTOR ===
    model_bar = tk.Frame(main_card, bg=card_bg)
    model_bar.pack(fill=tk.X, padx=16, pady=8)
    
    model_label = tk.Label(model_bar, text="Model:", font=(get_system_font(), 10), bg=card_bg, fg=text_color)
    model_label.pack(side=tk.LEFT)
    
    # Combine Gemini, Qwen, and Ollama models
    def get_all_models():
        models = []
        # Add Gemini models
        gemini_models = available_models if available_models else [
            "models/gemini-2.0-flash",
            "models/gemini-2.0-flash-lite",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro"
        ]
        for m in gemini_models:
            display_name = m.replace("models/", "")
            models.append(("gemini", m, f"✨ {display_name}"))
        
        # Add Ollama models if available
        if ollama_available_models:
            for m in ollama_available_models:
                models.append(("ollama", m, f"🦙 {m}"))
        
        # Add Qwen models
        qwen_models = qwen_available_models if qwen_available_models else [
            "qwen-vl-max",
            "qwen-vl-plus",
            "qwen2-vl-7b-instruct",
            "Qwen3-Coder-Plus"
        ]
        for m in qwen_models:
            models.append(("qwen", m, f"🌟 {m}"))
        
        return models
    
    all_models = get_all_models()
    
    # Get default model based on current config
    def get_default_model():
        if app_config.get("ollama_enabled", False):
            return app_config.get("ollama_model", "")
        elif app_config.get("qwen_enabled", False):
            return app_config.get("qwen_model", "qwen-vl-max")
        else:
            return app_config.get("model", "models/gemini-2.0-flash")
    
    def get_default_provider():
        if app_config.get("ollama_enabled", False):
            return "ollama"
        elif app_config.get("qwen_enabled", False):
            return "qwen"
        else:
            return "gemini"
    
    current_model_var = tk.StringVar(value=get_default_model())
    current_provider_var = tk.StringVar(value=get_default_provider())
    
    # Model dropdown frame
    model_dropdown_frame = tk.Frame(model_bar, bg=border_color)
    model_dropdown_frame.pack(side=tk.LEFT, padx=(10, 0))
    
    model_dropdown_inner = tk.Frame(model_dropdown_frame, bg=light_gray)
    model_dropdown_inner.pack(padx=1, pady=1)
    
    # Find display name for current model
    def get_display_for_model(model_id):
        for provider, mid, display in all_models:
            if mid == model_id:
                return display
        return model_id
    
    model_display_var = tk.StringVar(value=get_display_for_model(get_default_model()))
    
    model_display = tk.Label(
        model_dropdown_inner,
        textvariable=model_display_var,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        padx=12,
        pady=6,
        cursor='hand2',
        width=25,
        anchor='w'
    )
    model_display.pack(side=tk.LEFT)
    
    model_arrow = tk.Label(
        model_dropdown_inner,
        text="▼",
        font=(get_system_font(), 8),
        bg=light_gray,
        fg=secondary_text
    )
    model_arrow.pack(side=tk.LEFT, padx=(0, 8))
    
    # Model dropdown list
    model_list_frame = tk.Frame(main_card, bg=border_color)
    model_listbox = tk.Listbox(
        model_list_frame,
        font=(get_system_font(), 9),
        bg=light_gray,
        fg=text_color,
        selectbackground=accent_color,
        selectforeground='white',
        relief=tk.FLAT,
        highlightthickness=0,
        height=8,
        activestyle='none'
    )
    
    for provider, model_id, display_name in all_models:
        model_listbox.insert(tk.END, display_name)
    
    model_scrollbar = tk.Scrollbar(model_list_frame, orient="vertical", command=model_listbox.yview)
    model_listbox.configure(yscrollcommand=model_scrollbar.set)
    
    model_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
    model_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    model_dropdown_visible = [False]
    
    def toggle_model_dropdown(e=None):
        if model_dropdown_visible[0]:
            model_list_frame.pack_forget()
            model_dropdown_visible[0] = False
        else:
            model_list_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
            model_dropdown_visible[0] = True
    
    def select_chat_model(e=None):
        selection = model_listbox.curselection()
        if selection:
            idx = selection[0]
            provider, model_id, display_name = all_models[idx]
            current_model_var.set(model_id)
            current_provider_var.set(provider)
            model_display_var.set(display_name)
            toggle_model_dropdown()
    
    model_display.bind('<Button-1>', toggle_model_dropdown)
    model_arrow.bind('<Button-1>', toggle_model_dropdown)
    model_listbox.bind('<Double-1>', select_chat_model)
    model_listbox.bind('<Return>', select_chat_model)
    
    # Refresh models button
    def refresh_all_models():
        refresh_btn.config(text="⏳")
        chat_window.update()
        # Fetch Gemini models
        threading.Thread(target=fetch_available_models, daemon=True).start()
        # Fetch Ollama models if enabled
        ollama_url = app_config.get("ollama_url", "http://localhost:11434")
        if ollama_url:
            threading.Thread(target=lambda: fetch_ollama_models(ollama_url), daemon=True).start()
        # Fetch Qwen models if API key exists
        qwen_key = app_config.get("qwen_api_key", "")
        if qwen_key:
            threading.Thread(target=lambda: fetch_qwen_models(qwen_key), daemon=True).start()
        
        def update_list():
            nonlocal all_models
            all_models = get_all_models()
            model_listbox.delete(0, tk.END)
            for provider, model_id, display_name in all_models:
                model_listbox.insert(tk.END, display_name)
            refresh_btn.config(text="🔄")
        
        chat_window.after(2000, update_list)
    
    refresh_btn = tk.Label(
        model_bar,
        text="🔄",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=secondary_text,
        cursor='hand2'
    )
    refresh_btn.pack(side=tk.LEFT, padx=(8, 0))
    refresh_btn.bind('<Button-1>', lambda e: refresh_all_models())
    refresh_btn.bind('<Enter>', lambda e: refresh_btn.config(fg=text_color))
    refresh_btn.bind('<Leave>', lambda e: refresh_btn.config(fg=secondary_text))
    
    # === CHAT DISPLAY AREA ===
    chat_container = tk.Frame(main_card, bg=card_bg)
    chat_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
    
    chat_canvas = tk.Canvas(chat_container, bg=card_bg, highlightthickness=0)
    chat_scrollbar = tk.Scrollbar(chat_container, orient="vertical", command=chat_canvas.yview)
    chat_frame = tk.Frame(chat_canvas, bg=card_bg)
    
    chat_frame.bind(
        "<Configure>",
        lambda e: chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
    )
    
    chat_canvas.create_window((0, 0), window=chat_frame, anchor="nw", width=650)
    chat_canvas.configure(yscrollcommand=chat_scrollbar.set)
    
    chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def on_chat_mousewheel(event):
        chat_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    chat_canvas.bind_all("<MouseWheel>", on_chat_mousewheel)
    
    # Welcome message
    welcome_frame = tk.Frame(chat_frame, bg=card_bg)
    welcome_frame.pack(fill=tk.X, pady=20)
    
    welcome_icon = tk.Label(welcome_frame, text="🤖", font=(get_system_font(), 32), bg=card_bg, fg=text_color)
    welcome_icon.pack()
    
    welcome_text = tk.Label(
        welcome_frame,
        text="How can I help you today?",
        font=(get_system_font(), 14),
        bg=card_bg,
        fg=text_color
    )
    welcome_text.pack(pady=(8, 0))
    
    welcome_hint = tk.Label(
        welcome_frame,
        text="Type a message or attach a screenshot to analyze",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg=secondary_text
    )
    welcome_hint.pack(pady=(4, 0))
    
    def add_message_to_chat(role, content, image=None):
        """Add a message bubble to the chat display."""
        msg_container = tk.Frame(chat_frame, bg=card_bg)
        msg_container.pack(fill=tk.X, pady=8)
        
        if role == "user":
            # User message - right aligned with accent color
            msg_bubble = tk.Frame(msg_container, bg=accent_color)
            msg_bubble.pack(side=tk.RIGHT, padx=8)
            
            msg_inner = tk.Frame(msg_bubble, bg=accent_color)
            msg_inner.pack(padx=12, pady=8)
            
            # Show image if attached
            if image:
                try:
                    # Resize image for display
                    display_img = image.copy()
                    display_img.thumbnail((200, 150), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(display_img)
                    img_label = tk.Label(msg_inner, image=photo, bg=accent_color)
                    img_label.image = photo  # Keep reference
                    img_label.pack(pady=(0, 8))
                except Exception as e:
                    logger.debug(f"Could not display image: {e}")
            
            msg_text = tk.Label(
                msg_inner,
                text=content,
                font=(get_system_font(), 10),
                bg=accent_color,
                fg='white',
                wraplength=400,
                justify=tk.LEFT
            )
            msg_text.pack()
            
        else:
            # Assistant message - left aligned with light bg
            msg_row = tk.Frame(msg_container, bg=card_bg)
            msg_row.pack(side=tk.LEFT, padx=8)
            
            # Assistant icon
            icon_label = tk.Label(msg_row, text="🤖", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
            icon_label.pack(side=tk.LEFT, anchor='n', padx=(0, 8))
            
            msg_bubble = tk.Frame(msg_row, bg=light_gray)
            msg_bubble.pack(side=tk.LEFT)
            
            msg_inner = tk.Frame(msg_bubble, bg=light_gray)
            msg_inner.pack(padx=12, pady=8)
            
            msg_text = tk.Label(
                msg_inner,
                text=content,
                font=(get_system_font(), 10),
                bg=light_gray,
                fg=text_color,
                wraplength=500,
                justify=tk.LEFT
            )
            msg_text.pack()
        
        # Scroll to bottom
        chat_canvas.update_idletasks()
        chat_canvas.yview_moveto(1.0)
        
        return msg_container
    
    # === INPUT AREA ===
    input_section = tk.Frame(main_card, bg=card_bg)
    input_section.pack(fill=tk.X, padx=16, pady=(8, 16))
    
    # Screenshot preview area
    preview_frame = tk.Frame(input_section, bg=card_bg)
    preview_frame.pack(fill=tk.X, pady=(0, 8))
    
    preview_label = tk.Label(preview_frame, text="", bg=card_bg, fg=text_color)
    preview_label.pack(side=tk.LEFT)
    
    def update_preview():
        if attached_screenshot[0]:
            try:
                # Create thumbnail
                img = attached_screenshot[0].copy()
                img.thumbnail((80, 60), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                preview_label.config(image=photo, text="")
                preview_label.image = photo
                remove_btn.pack(side=tk.LEFT, padx=(8, 0))
            except Exception as e:
                preview_label.config(text="📷 Screenshot attached", image='')
                remove_btn.pack(side=tk.LEFT, padx=(8, 0))
        else:
            preview_label.config(image='', text="")
            preview_label.image = None
            remove_btn.pack_forget()
    
    def remove_screenshot():
        attached_screenshot[0] = None
        update_preview()
    
    remove_btn = tk.Label(
        preview_frame,
        text="✕",
        font=(get_system_font(), 10),
        bg=card_bg,
        fg='#ef4444',
        cursor='hand2'
    )
    remove_btn.bind('<Button-1>', lambda e: remove_screenshot())
    
    # Input row
    input_row = tk.Frame(input_section, bg=border_color)
    input_row.pack(fill=tk.X)
    
    input_inner = tk.Frame(input_row, bg=light_gray)
    input_inner.pack(fill=tk.X, padx=1, pady=1)
    
    # Screenshot button
    def capture_for_chat():
        """Capture screenshot and attach to chat."""
        # Temporarily hide chat window
        chat_window.withdraw()
        chat_window.update()
        
        # Small delay to ensure window is hidden
        import time
        time.sleep(0.2)
        
        # Capture screenshot
        screenshot = capture_screenshot()
        
        # Show chat window again
        chat_window.deiconify()
        chat_window.focus_force()
        
        if screenshot:
            attached_screenshot[0] = screenshot
            update_preview()
            logger.info("Screenshot attached to chat")
    
    screenshot_btn = tk.Label(
        input_inner,
        text="📷",
        font=(get_system_font(), 14),
        bg=light_gray,
        fg=secondary_text,
        cursor='hand2',
        padx=8,
        pady=8
    )
    screenshot_btn.pack(side=tk.LEFT)
    screenshot_btn.bind('<Button-1>', lambda e: capture_for_chat())
    screenshot_btn.bind('<Enter>', lambda e: screenshot_btn.config(fg=text_color))
    screenshot_btn.bind('<Leave>', lambda e: screenshot_btn.config(fg=secondary_text))
    
    # Text input
    input_text = tk.Text(
        input_inner,
        font=(get_system_font(), 10),
        bg=light_gray,
        fg=text_color,
        relief=tk.FLAT,
        height=3,
        wrap=tk.WORD,
        padx=8,
        pady=8
    )
    input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    input_text.insert("1.0", "")
    input_text.focus_set()
    
    # Placeholder
    def on_focus_in(e):
        if input_text.get("1.0", "end-1c") == "Type your message...":
            input_text.delete("1.0", tk.END)
            input_text.config(fg=text_color)
    
    def on_focus_out(e):
        if not input_text.get("1.0", "end-1c").strip():
            input_text.insert("1.0", "Type your message...")
            input_text.config(fg=secondary_text)
    
    # Send message function
    def send_message(e=None):
        """Send the current message to the AI."""
        message = input_text.get("1.0", "end-1c").strip()
        
        if not message and not attached_screenshot[0]:
            return "break"
        
        if message == "Type your message...":
            message = ""
        
        # Clear welcome message on first send
        for widget in chat_frame.winfo_children():
            widget.destroy()
        
        # Add user message to chat
        user_img = attached_screenshot[0]
        display_msg = message if message else "(Screenshot)"
        add_message_to_chat("user", display_msg, image=user_img)
        
        # Clear input
        input_text.delete("1.0", tk.END)
        screenshot_copy = attached_screenshot[0]
        attached_screenshot[0] = None
        update_preview()
        
        # Add loading indicator
        loading_frame = tk.Frame(chat_frame, bg=card_bg)
        loading_frame.pack(fill=tk.X, pady=8)
        
        loading_row = tk.Frame(loading_frame, bg=card_bg)
        loading_row.pack(side=tk.LEFT, padx=8)
        
        loading_icon = tk.Label(loading_row, text="🤖", font=(get_system_font(), 12), bg=card_bg, fg=text_color)
        loading_icon.pack(side=tk.LEFT, padx=(0, 8))
        
        loading_text = tk.Label(loading_row, text="Thinking...", font=(get_system_font(), 10), bg=card_bg, fg=secondary_text)
        loading_text.pack(side=tk.LEFT)
        
        chat_canvas.update_idletasks()
        chat_canvas.yview_moveto(1.0)
        
        # Query AI in background
        def query_ai():
            try:
                provider = current_provider_var.get()
                model_id = current_model_var.get()
                
                prompt = message if message else "Analyze this image and describe what you see."
                
                if provider == "ollama":
                    # Ollama - requires image for vision models
                    if not screenshot_copy:
                        raise Exception("Ollama vision models require an image. Please attach a screenshot.")
                    old_model = app_config.get("ollama_model", "")
                    app_config["ollama_model"] = model_id
                    response = query_ollama(screenshot_copy, prompt)
                    app_config["ollama_model"] = old_model
                elif provider == "qwen":
                    # Temporarily set the model
                    old_model = app_config.get("qwen_model", "")
                    app_config["qwen_model"] = model_id
                    # query_qwen handles whether image is required based on model type
                    response = query_qwen(screenshot_copy, prompt)
                    app_config["qwen_model"] = old_model
                else:
                    # Gemini
                    temp_model = genai.GenerativeModel(model_id)
                    if screenshot_copy:
                        result = temp_model.generate_content([prompt, screenshot_copy])
                    else:
                        result = temp_model.generate_content(prompt)
                    response = result.text
                
                # Update UI on main thread
                def show_response():
                    loading_frame.destroy()
                    add_message_to_chat("assistant", response)
                    # Add to history
                    add_to_history(response)
                
                chat_window.after(0, show_response)
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                logger.error(error_msg)
                
                def show_error():
                    loading_frame.destroy()
                    add_message_to_chat("assistant", f"❌ {error_msg}")
                
                chat_window.after(0, show_error)
        
        threading.Thread(target=query_ai, daemon=True).start()
        
        return "break"
    
    # Bind Enter to send (Shift+Enter for newline)
    def handle_enter(e):
        if e.state & 0x1:  # Shift key pressed
            return  # Allow newline
        return send_message()
    
    input_text.bind('<Return>', handle_enter)
    
    # Send button
    send_btn = tk.Label(
        input_inner,
        text="➤",
        font=(get_system_font(), 16),
        bg=accent_color,
        fg='white',
        cursor='hand2',
        padx=12,
        pady=8
    )
    send_btn.pack(side=tk.RIGHT)
    send_btn.bind('<Button-1>', send_message)
    send_btn.bind('<Enter>', lambda e: send_btn.config(bg=theme['btn_hover']))
    send_btn.bind('<Leave>', lambda e: send_btn.config(bg=accent_color))
    
    # Bottom hint
    hint_frame = tk.Frame(main_card, bg=card_bg)
    hint_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
    
    hint_text = tk.Label(
        hint_frame,
        text=f"📷 Click camera to attach screenshot | Enter to send | Shift+Enter for new line | ESC to close",
        font=(get_system_font(), 8),
        bg=card_bg,
        fg=secondary_text
    )
    hint_text.pack()
    
    # Animations
    def fade_in(alpha=0.0):
        if not chat_window or not chat_window.winfo_exists():
            return
        if alpha < 0.98:
            alpha += 0.1
            chat_window.attributes('-alpha', alpha)
            chat_window.after(15, lambda: fade_in(alpha))
        else:
            chat_window.attributes('-alpha', 0.98)
    
    chat_window.bind('<Escape>', lambda e: fade_out())
    
    # Draggable
    def start_move(event):
        chat_window.x = event.x
        chat_window.y = event.y
    
    def do_move(event):
        x = chat_window.winfo_x() + (event.x - chat_window.x)
        y = chat_window.winfo_y() + (event.y - chat_window.y)
        chat_window.geometry(f"+{x}+{y}")
    
    for widget in [top_bar, title_row, title_label, title_icon]:
        widget.bind('<Button-1>', start_move)
        widget.bind('<B1-Motion>', do_move)
    
    chat_window.after(10, fade_in)


def create_tray_icon():
    """Creates and returns the system tray icon with menu."""
    global tray_icon
    
    # Load the icon image
    try:
        icon_image = Image.open(LOGO_PATH)
        icon_image = icon_image.resize((64, 64), Image.Resampling.LANCZOS)
    except Exception:
        # Create a simple fallback icon if logo not found
        icon_image = Image.new('RGB', (64, 64), color='#fbbf24')
    
    def on_capture(icon, item):
        """Trigger screen capture from tray menu."""
        root.after(0, analyze_screen)
    
    def on_toggle_theme(icon, item):
        """Toggle theme from tray menu."""
        root.after(0, toggle_theme)
        icon.update_menu()
    
    def on_hide_ui(icon, item):
        """Toggle UI visibility from tray menu."""
        root.after(0, toggle_popup_visibility)
    
    def on_show_history(icon, item):
        """Show history popup from tray menu."""
        root.after(0, show_history_popup)
    
    def on_show_settings(icon, item):
        """Show settings popup from tray menu."""
        root.after(0, show_settings_popup)
    
    def on_show_chat(icon, item):
        """Show chat window from tray menu."""
        root.after(0, show_chat_window)
    
    def on_quit(icon, item):
        """Quit from tray menu."""
        root.after(0, quit_application)
    
    def is_dark_theme():
        """Check if dark theme is active."""
        return app_config.get("theme", "light") == "dark"
    
    def is_coding_mode():
        """Check if coding mode is active."""
        return app_config.get("question_mode", "mcq") == "coding"
    
    def on_toggle_mode(icon, item):
        """Toggle question mode from tray menu."""
        root.after(0, toggle_question_mode)
        icon.update_menu()
    
    def get_history_items():
        """Generate history submenu items."""
        if not answer_history:
            return [pystray.MenuItem("No history yet", None, enabled=False)]
        
        items = []
        for i, entry in enumerate(answer_history[:5]):  # Show last 5 in tray
            preview = entry['preview'][:30] + "..." if len(entry['preview']) > 30 else entry['preview']
            def make_handler(text):
                return lambda icon, item: root.after(0, lambda: show_answer_popup(text))
            items.append(pystray.MenuItem(preview, make_handler(entry['answer'])))
        
        if len(answer_history) > 5:
            items.append(pystray.Menu.SEPARATOR)
            items.append(pystray.MenuItem(f"View all ({len(answer_history)})...", lambda icon, item: root.after(0, show_history_popup)))
        
        return items
    
    # Create the menu
    menu = pystray.Menu(
        pystray.MenuItem(
            f"Capture Screen ({HOTKEY})",
            on_capture,
            default=True  # Double-click action
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Recent Answers",
            pystray.Menu(lambda: get_history_items())
        ),
        pystray.MenuItem(
            f"View History ({HISTORY_HOTKEY})",
            on_show_history
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Dark Mode",
            on_toggle_theme,
            checked=lambda item: is_dark_theme()
        ),
        pystray.MenuItem(
            f"Coding Mode ({MODE_HOTKEY})",
            on_toggle_mode,
            checked=lambda item: is_coding_mode()
        ),
        pystray.MenuItem(
            f"Hide/Show UI ({HIDE_HOTKEY})",
            on_hide_ui
        ),
        pystray.MenuItem(
            f"ElAnswer Chat ({CHAT_HOTKEY})",
            on_show_chat
        ),
        pystray.MenuItem(
            f"Settings ({SETTINGS_HOTKEY})",
            on_show_settings
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            f"Quit ({QUIT_HOTKEY})",
            on_quit
        )
    )
    
    # Create the icon
    tray_icon = pystray.Icon(
        "ElAnswer",
        icon_image,
        "ElAnswer - AI Screen Solver",
        menu
    )
    
    return tray_icon


def run_tray_icon():
    """Run the system tray icon in a separate thread."""
    icon = create_tray_icon()
    icon.run()


# Hide console window (Windows only, no-op on other platforms)
def hide_console():
    """Hide the console window on Windows."""
    if IS_WINDOWS and ctypes:
        try:
            # Get the console window handle
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        except Exception:
            pass
    # On macOS and Linux, the console is handled differently
    # (typically launched from terminal or as a background process)


def check_linux_permissions():
    """Check if we have the required permissions on Linux."""
    if not IS_LINUX:
        return True
    
    import os
    if os.geteuid() == 0:
        return True
    
    # Check if we can access input devices
    try:
        # Try to find readable input devices
        input_dir = '/dev/input'
        if os.path.exists(input_dir):
            for device in os.listdir(input_dir):
                if device.startswith('event'):
                    device_path = os.path.join(input_dir, device)
                    if os.access(device_path, os.R_OK):
                        return True
    except Exception:
        pass
    
    return False


# Main Execution
if __name__ == "__main__":
    # Check Linux permissions before initializing keyboard
    if IS_LINUX and not check_linux_permissions():
        print("")
        print("=" * 60)
        print("  ElAnswer - Root Permission Required on Linux")
        print("=" * 60)
        print("")
        print("  The 'keyboard' library requires root access to capture")
        print("  global hotkeys on Linux.")
        print("")
        print("  Please run ElAnswer with sudo:")
        print("")
        print("    sudo ./ElAnswer")
        print("")
        print("  Or add your user to the 'input' group:")
        print("")
        print("    sudo usermod -aG input $USER")
        print("    # Then log out and log back in")
        print("")
        print("=" * 60)
        sys.exit(1)
    
    model = configure_genai()
    
    # Create hidden root window for tkinter
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Add the hotkey listeners
    keyboard.add_hotkey(HOTKEY, analyze_screen)
    keyboard.add_hotkey(HIDE_HOTKEY, toggle_popup_visibility)
    keyboard.add_hotkey(THEME_HOTKEY, toggle_theme)
    keyboard.add_hotkey(HISTORY_HOTKEY, show_history_popup)
    keyboard.add_hotkey(SETTINGS_HOTKEY, show_settings_popup)
    keyboard.add_hotkey(MODE_HOTKEY, toggle_question_mode)
    keyboard.add_hotkey(COPY_HOTKEY, copy_last_response)
    keyboard.add_hotkey(AUTO_TYPE_HOTKEY, auto_type_last_response)
    # Right-click to pause/resume auto-typing
    mouse.on_right_click(toggle_auto_type_pause)
    keyboard.add_hotkey(CHAT_HOTKEY, show_chat_window)
    keyboard.add_hotkey(QUIT_HOTKEY, quit_application)
    
    # Start system tray icon in separate thread
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()
    
    # Hide console window (runs minimized in system tray)
    hide_console()
    
    # If no API key is set and neither Ollama nor Qwen is enabled, show settings on first run
    ollama_enabled = app_config.get("ollama_enabled", False)
    qwen_enabled = app_config.get("qwen_enabled", False)
    qwen_api_key = app_config.get("qwen_api_key", "")
    if not API_KEY and not ollama_enabled and not (qwen_enabled and qwen_api_key):
        logger.warning("No API key found. Opening settings...")
        root.after(500, show_settings_popup)
    
    # Run tkinter main loop (keeps GUI responsive)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        quit_application()