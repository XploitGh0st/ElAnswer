"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              ⚡ ElAnswer                                       ║
║           AI-Powered Screen Capture & Question Solver                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Description:  Captures screen content and uses Google Gemini AI to          ║
║                analyze and solve questions, problems, or code snippets.      ║
║                                                                               ║
║  Version:      1.2.0                                                          ║
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
from datetime import datetime
import keyboard  # For detecting key presses
import google.generativeai as genai
from PIL import ImageGrab, Image, ImageTk  # For taking screenshots and image handling
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import ctypes
import pystray  # For system tray icon

# Application version
APP_VERSION = "1.2.0"
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

# Enable High DPI awareness for crisp rendering
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Fallback for older Windows
    except:
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
available_models = []  # Available Gemini models
model = None  # Current Gemini model instance

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
        "model": "models/gemini-2.5-flash",
        "max_history": 10,
        "auto_copy": False,
        "show_explanation": True,
        "compact_mode": False
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
    
    # Update tray menu if available
    if tray_icon:
        tray_icon.update_menu()

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
        selected_model = app_config.get("model", "models/gemini-2.5-flash")
        model = genai.GenerativeModel(selected_model)
        return model
    except Exception as e:
        logger.error(f"Failed to configure API: {e}")
        return None


def fetch_available_models():
    """Fetch available models from the API."""
    global available_models
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
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro-preview-05-06",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
            "models/gemini-pro",
            "models/gemini-pro-vision"
        ]


def reload_model():
    """Reload the model with current settings."""
    global model
    selected_model = app_config.get("model", "models/gemini-2.5-flash")
    try:
        model = genai.GenerativeModel(selected_model)
        logger.info(f"Model changed to: {selected_model}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")

def show_loading_indicator():
    """Shows a small blinking logo at the bottom left while Gemini is processing."""
    global loading_indicator, logo_image
    
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
    
    # Make window undetectable (tool window style)
    loading_indicator.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(loading_indicator.winfo_id())
    GWL_EXSTYLE = -20
    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    ex_style = ex_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    
    # Transparent background
    loading_indicator.configure(bg='#000000')
    loading_indicator.wm_attributes('-transparentcolor', '#000000')
    
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
            font=('Segoe UI', 24),
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
    
    # Make window undetectable
    popup_window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(popup_window.winfo_id())
    GWL_EXSTYLE = -20
    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    ex_style = ex_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    
    # Get colors from current theme
    card_bg = theme['card_bg']
    text_color = theme['text_color']
    secondary_text = theme['secondary_text']
    border_color = theme['border_color']
    accent_color = theme['accent_color']
    green_accent = theme['green_accent']
    light_gray = theme['light_gray']
    
    # Make window transparent for rounded corners
    popup_window.configure(bg='#000000')
    popup_window.wm_attributes('-transparentcolor', '#000000')
    
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
        font=('Segoe UI', 22),
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
        font=('Segoe UI', 16),
        bg=card_bg,
        fg=text_color
    )
    icon_label.pack(side=tk.LEFT, padx=(0, 8))
    
    title_label = tk.Label(
        title_row,
        text="ElAnswer",
        font=('Segoe UI', 15, 'bold'),
        bg=card_bg,
        fg=text_color
    )
    title_label.pack(side=tk.LEFT)
    
    # Subtitle
    subtitle_label = tk.Label(
        header_section,
        text="AI-powered answer to your screen capture",
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 9),
        bg=card_bg,
        fg=secondary_text
    )
    status_text.pack(side=tk.LEFT)
    
    # Buttons row
    buttons_frame = tk.Frame(footer_section, bg=card_bg)
    buttons_frame.pack(fill=tk.X)
    
    # Copy button (primary - dark)
    def copy_to_clipboard():
        popup_window.clipboard_clear()
        popup_window.clipboard_append(answer_text)
        copy_btn.config(text="✓ Copied")
        popup_window.after(2000, lambda: copy_btn.config(text="Copy"))
    
    copy_btn = tk.Button(
        buttons_frame,
        text="Copy",
        command=copy_to_clipboard,
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 9),
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
    """Captures screen, sends to Gemini, and displays answer in popup."""
    global app_config, model
    
    # Check if API key is configured
    if not API_KEY:
        logger.warning("No API key configured. Opening settings...")
        root.after(0, show_settings_popup)
        return
    
    # Check if model is configured
    selected_model = app_config.get("model", "models/gemini-2.5-flash")
    current_model_name = getattr(model, "model_name", None) or getattr(model, "_model", None)
    if (not model) or (current_model_name and current_model_name != selected_model):
        logger.info(f"Model not configured or outdated. Loading: {selected_model}")
        model = genai.GenerativeModel(selected_model)
    if not model:
        logger.error("Failed to configure model. Please check your API key and model.")
        root.after(0, show_settings_popup)
        return
    
    logger.info("Hotkey detected! Capturing screen...")
    
    # Show loading indicator on main thread
    root.after(0, show_loading_indicator)
    
    def process_and_display():
        try:
            # 1. Capture the entire screen
            screenshot = ImageGrab.grab()
            
            # 2. visual feedback
            logger.debug("Screen captured. Sending to Gemini...")
            
            # 3. Prepare the prompt based on settings
            show_explanation = app_config.get("show_explanation", True)
            
            if show_explanation:
                prompt = (
                    "Analyze this image. Identify the main question, problem, or code snippet present on the screen.\n\n"
                    "Format your response EXACTLY as follows:\n\n"
                    "📋 QUESTION:\n"
                    "[State the question or problem identified]\n\n"
                    "✅ ANSWER:\n"
                    "[Provide the direct answer. If multiple choice, state the correct option letter and full text]\n\n"
                    "💡 EXPLANATION:\n"
                    "[Provide a clear, concise explanation of why this is correct]\n\n"
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

            # 4. Send to Gemini
            response = model.generate_content([prompt, screenshot])
            
            # 5. Hide loading indicator and display result in popup
            answer = response.text
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
    global tray_icon
    
    # Stop the tray icon if running
    if tray_icon:
        tray_icon.stop()
    
    root.quit()
    root.destroy()
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
    
    # Create new popup window
    popup_window = tk.Toplevel()
    popup_window.title("")
    popup_window.geometry(f"400x450+{popup_x}+{popup_y}")
    popup_window.overrideredirect(True)
    
    # Make it always on top
    popup_window.attributes('-topmost', True)
    popup_window.attributes('-alpha', 0.0)
    
    # Make window undetectable
    popup_window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(popup_window.winfo_id())
    GWL_EXSTYLE = -20
    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    ex_style = ex_style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    
    # Get colors from current theme
    card_bg = theme['card_bg']
    text_color = theme['text_color']
    secondary_text = theme['secondary_text']
    border_color = theme['border_color']
    accent_color = theme['accent_color']
    light_gray = theme['light_gray']
    
    # Make window transparent for rounded corners
    popup_window.configure(bg='#000000')
    popup_window.wm_attributes('-transparentcolor', '#000000')
    
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
        font=('Segoe UI', 22),
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
    
    icon_label = tk.Label(title_row, text="📚", font=('Segoe UI', 14), bg=card_bg, fg=text_color)
    icon_label.pack(side=tk.LEFT, padx=(0, 8))
    
    title_label = tk.Label(title_row, text="Recent Answers", font=('Segoe UI', 14, 'bold'), bg=card_bg, fg=text_color)
    title_label.pack(side=tk.LEFT)
    
    count_label = tk.Label(title_row, text=f"({len(answer_history)})", font=('Segoe UI', 10), bg=card_bg, fg=secondary_text)
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
            font=('Segoe UI', 8),
            bg=light_gray,
            fg=secondary_text
        )
        time_label.pack(anchor='w')
        
        # Preview
        preview_label = tk.Label(
            inner_frame,
            text=entry['preview'],
            font=('Segoe UI', 10),
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
        if tray_icon:
            tray_icon.update_menu()
        fade_out()
    
    clear_btn = tk.Button(
        footer,
        text="Clear History",
        command=clear_history,
        font=('Segoe UI', 9),
        bg=card_bg,
        fg=secondary_text,
        relief=tk.SOLID,
        padx=12,
        pady=4,
        cursor='hand2',
        borderwidth=1
    )
    clear_btn.pack(side=tk.LEFT)
    
    hint_label = tk.Label(footer, text="Click to view", font=('Segoe UI', 9), bg=card_bg, fg='#9ca3af')
    hint_label.pack(side=tk.RIGHT)
    
    # Animations
    def fade_in(alpha=0.0):
        if alpha < 0.98:
            alpha += 0.1
            popup_window.attributes('-alpha', alpha)
            popup_window.after(15, lambda: fade_in(alpha))
        else:
            popup_window.attributes('-alpha', 0.98)
    
    def fade_out(alpha=0.98):
        if alpha > 0:
            alpha -= 0.12
            popup_window.attributes('-alpha', alpha)
            popup_window.after(12, lambda: fade_out(alpha))
        else:
            list_canvas.unbind_all("<MouseWheel>")
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


def show_settings_popup():
    """Show the settings popup with model selection and other options."""
    global settings_window, app_config, available_models
    
    # Close existing settings window if any
    if settings_window and settings_window.winfo_exists():
        settings_window.destroy()
    
    # Get theme
    current_theme = app_config.get("theme", "light")
    theme = THEMES[current_theme]
    
    # Create settings window
    settings_window = tk.Toplevel()
    settings_window.title("")
    settings_window.geometry("450x550+250+100")
    settings_window.overrideredirect(True)
    
    # Make it always on top
    settings_window.attributes('-topmost', True)
    settings_window.attributes('-alpha', 0.0)
    
    # Make window tool-style (no taskbar), but allow focus for input
    settings_window.update_idletasks()
    hwnd = ctypes.windll.user32.GetParent(settings_window.winfo_id())
    GWL_EXSTYLE = -20
    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    WS_EX_TOOLWINDOW = 0x00000080
    ex_style = ex_style | WS_EX_TOOLWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
    
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
    
    # Make window transparent for rounded corners
    settings_window.configure(bg='#000000')
    settings_window.wm_attributes('-transparentcolor', '#000000')
    
    # Main canvas for rounded corners
    canvas = tk.Canvas(settings_window, width=450, height=550, bg='#000000', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Draw rounded rectangle background
    radius = 16
    x1, y1, x2, y2 = 0, 0, 450, 550
    
    canvas.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
    canvas.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
    
    # Main card frame
    main_card = tk.Frame(canvas, bg=card_bg)
    canvas.create_window(225, 275, window=main_card, width=446, height=546)
    
    # Top bar
    top_bar = tk.Frame(main_card, bg=card_bg, height=50)
    top_bar.pack(fill=tk.X)
    top_bar.pack_propagate(False)
    
    # Close button
    close_btn = tk.Label(
        top_bar,
        text="×",
        font=('Segoe UI', 22),
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
    
    icon_label = tk.Label(title_row, text="⚙️", font=('Segoe UI', 16), bg=card_bg, fg=text_color)
    icon_label.pack(side=tk.LEFT, padx=(0, 10))
    
    title_label = tk.Label(title_row, text="Settings", font=('Segoe UI', 16, 'bold'), bg=card_bg, fg=text_color)
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
    
    api_icon = tk.Label(api_header, text="🔑", font=('Segoe UI', 12), bg=card_bg, fg=text_color)
    api_icon.pack(side=tk.LEFT)
    
    api_title = tk.Label(api_header, text="API Key", font=('Segoe UI', 11, 'bold'), bg=card_bg, fg=text_color)
    api_title.pack(side=tk.LEFT, padx=(6, 0))
    
    api_desc = tk.Label(
        api_section,
        text="Enter your Google Gemini API key",
        font=('Segoe UI', 9),
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
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 9, 'underline'),
        bg=card_bg,
        fg=accent_color,
        cursor='hand2'
    )
    api_link.pack(anchor='w', pady=(4, 0))
    api_link.bind('<Button-1>', lambda e: os.startfile("https://makersuite.google.com/app/apikey"))
    
    # Status indicator
    api_status_frame = tk.Frame(api_section, bg=card_bg)
    api_status_frame.pack(fill=tk.X, pady=(8, 0))
    
    if current_api_key:
        api_status = tk.Label(
            api_status_frame,
            text="✓ API key configured",
            font=('Segoe UI', 9),
            bg=card_bg,
            fg=green_accent
        )
    else:
        api_status = tk.Label(
            api_status_frame,
            text="⚠ No API key set",
            font=('Segoe UI', 9),
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
        font=('Segoe UI', 10),
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
    
    # === MODEL SELECTION SECTION ===
    model_section = tk.Frame(content_frame, bg=card_bg)
    model_section.pack(fill=tk.X, pady=(0, 20))
    
    model_header = tk.Frame(model_section, bg=card_bg)
    model_header.pack(fill=tk.X)
    
    model_icon = tk.Label(model_header, text="🤖", font=('Segoe UI', 12), bg=card_bg, fg=text_color)
    model_icon.pack(side=tk.LEFT)
    
    model_title = tk.Label(model_header, text="AI Model", font=('Segoe UI', 11, 'bold'), bg=card_bg, fg=text_color)
    model_title.pack(side=tk.LEFT, padx=(6, 0))
    
    model_desc = tk.Label(
        model_section,
        text="Select the Gemini model to use for analysis",
        font=('Segoe UI', 9),
        bg=card_bg,
        fg=secondary_text
    )
    model_desc.pack(anchor='w', pady=(4, 8))
    
    # Model dropdown
    model_var = tk.StringVar(value=app_config.get("model", "models/gemini-2.5-flash"))
    
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
    current_model_var = tk.StringVar(value=get_model_display_name(app_config.get("model", "models/gemini-2.5-flash")))
    
    model_display = tk.Label(
        model_listbox_frame,
        textvariable=current_model_var,
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 8),
        bg=light_gray,
        fg=secondary_text
    )
    arrow_label.place(relx=0.95, rely=0.5, anchor='center')
    
    # Dropdown list (hidden by default)
    dropdown_list_frame = tk.Frame(model_section, bg=border_color)
    dropdown_listbox = tk.Listbox(
        dropdown_list_frame,
        font=('Segoe UI', 9),
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
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro-preview-05-06",
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
        font=('Segoe UI', 10),
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
        font=('Segoe UI', 9),
        bg=card_bg,
        fg=secondary_text,
        anchor='w'
    )
    model_status.pack(fill=tk.X, pady=(6, 4))

    apply_model_btn = tk.Button(
        model_section,
        text="Set Model",
        command=apply_model,
        font=('Segoe UI', 10),
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
    
    theme_icon_lbl = tk.Label(theme_header, text="🎨", font=('Segoe UI', 12), bg=card_bg, fg=text_color)
    theme_icon_lbl.pack(side=tk.LEFT)
    
    theme_title = tk.Label(theme_header, text="Appearance", font=('Segoe UI', 11, 'bold'), bg=card_bg, fg=text_color)
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
                x1, y1, x2, y2 = 0, 0, 450, 550
                widget.create_arc(x1, y1, x1+radius*2, y1+radius*2, start=90, extent=90, fill=card_bg, outline=card_bg)
                widget.create_arc(x2-radius*2, y1, x2, y1+radius*2, start=0, extent=90, fill=card_bg, outline=card_bg)
                widget.create_arc(x1, y2-radius*2, x1+radius*2, y2, start=180, extent=90, fill=card_bg, outline=card_bg)
                widget.create_arc(x2-radius*2, y2-radius*2, x2, y2, start=270, extent=90, fill=card_bg, outline=card_bg)
                widget.create_rectangle(x1+radius, y1, x2-radius, y2, fill=card_bg, outline=card_bg)
                widget.create_rectangle(x1, y1+radius, x2, y2-radius, fill=card_bg, outline=card_bg)
                # Recreate the main card window
                widget.create_window(225, 275, window=main_card, width=446, height=546)
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
        
        btn_icon = tk.Label(btn_content, text=icon, font=('Segoe UI', 14), bg=light_gray, fg=text_color)
        btn_icon.pack()
        
        btn_text = tk.Label(btn_content, text=text, font=('Segoe UI', 9), bg=light_gray, fg=text_color)
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
    
    options_icon = tk.Label(options_header, text="⚡", font=('Segoe UI', 12), bg=card_bg, fg=text_color)
    options_icon.pack(side=tk.LEFT)
    
    options_title = tk.Label(options_header, text="Options", font=('Segoe UI', 11, 'bold'), bg=card_bg, fg=text_color)
    options_title.pack(side=tk.LEFT, padx=(6, 0))
    
    # Checkboxes
    auto_copy_var = tk.BooleanVar(value=app_config.get("auto_copy", False))
    show_explanation_var = tk.BooleanVar(value=app_config.get("show_explanation", True))
    compact_mode_var = tk.BooleanVar(value=app_config.get("compact_mode", False))
    
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
        
        cb_check = tk.Label(cb_inner, text="", font=('Segoe UI', 10), bg=light_gray, fg=accent_color)
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
        
        cb_label = tk.Label(cb_row, text=text, font=('Segoe UI', 10), bg=card_bg, fg=text_color, cursor='hand2')
        cb_label.pack(side=tk.LEFT, padx=(10, 0))
        cb_label.bind('<Button-1>', toggle_cb)
        
        desc_label = None
        if description:
            desc_label = tk.Label(cb_frame, text=description, font=('Segoe UI', 8), bg=card_bg, fg=secondary_text)
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
    
    # === HISTORY LIMIT SECTION ===
    history_section = tk.Frame(content_frame, bg=card_bg)
    history_section.pack(fill=tk.X, pady=(0, 10))
    
    history_header = tk.Frame(history_section, bg=card_bg)
    history_header.pack(fill=tk.X)
    
    history_icon = tk.Label(history_header, text="📚", font=('Segoe UI', 12), bg=card_bg, fg=text_color)
    history_icon.pack(side=tk.LEFT)
    
    history_title = tk.Label(history_header, text="History Limit", font=('Segoe UI', 11, 'bold'), bg=card_bg, fg=text_color)
    history_title.pack(side=tk.LEFT, padx=(6, 0))
    
    history_row = tk.Frame(history_section, bg=card_bg)
    history_row.pack(fill=tk.X, pady=(10, 0))
    
    max_history_var = tk.IntVar(value=app_config.get("max_history", 10))
    
    history_label = tk.Label(history_row, text="Maximum items:", font=('Segoe UI', 10), bg=card_bg, fg=text_color)
    history_label.pack(side=tk.LEFT)
    
    history_spinbox = tk.Spinbox(
        history_row,
        from_=5,
        to=50,
        textvariable=max_history_var,
        width=5,
        font=('Segoe UI', 10),
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
        
        # Update config
        app_config["model"] = model_var.get()
        app_config["theme"] = theme_var.get()
        app_config["auto_copy"] = auto_copy_var.get()
        app_config["show_explanation"] = show_explanation_var.get()
        app_config["compact_mode"] = compact_mode_var.get()
        app_config["max_history"] = max_history_var.get()
        
        # Update MAX_HISTORY_ITEMS
        MAX_HISTORY_ITEMS = max_history_var.get()
        
        # Save to file
        save_config(app_config)
        
        # Reconfigure API if key changed
        if api_key_changed and new_api_key:
            configure_genai()
        else:
            # Reload model if changed
            reload_model()
        
        # Update tray menu
        if tray_icon:
            tray_icon.update_menu()
        
        # Show confirmation
        save_btn.config(text="✓ Saved!")
        settings_window.after(1500, lambda: fade_out())
    
    save_btn = tk.Button(
        footer,
        text="Save Settings",
        command=save_settings,
        font=('Segoe UI', 11),
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
        font=('Segoe UI', 10),
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
    hint_label = tk.Label(footer, text="ESC to close", font=('Segoe UI', 9), bg=card_bg, fg='#9ca3af')
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
            scroll_canvas.unbind_all("<MouseWheel>")
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
    
    def on_quit(icon, item):
        """Quit from tray menu."""
        root.after(0, quit_application)
    
    def is_dark_theme():
        """Check if dark theme is active."""
        return app_config.get("theme", "light") == "dark"
    
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
            f"Hide/Show UI ({HIDE_HOTKEY})",
            on_hide_ui
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


# Hide console window on Windows
def hide_console():
    """Hide the console window on Windows."""
    if sys.platform == 'win32':
        try:
            # Get the console window handle
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0
        except Exception:
            pass


# Main Execution
if __name__ == "__main__":
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
    keyboard.add_hotkey(QUIT_HOTKEY, quit_application)
    
    # Start system tray icon in separate thread
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()
    
    # Hide console window (runs minimized in system tray)
    hide_console()
    
    # If no API key is set, show settings on first run
    if not API_KEY:
        logger.warning("No API key found. Opening settings...")
        root.after(500, show_settings_popup)
    
    # Run tkinter main loop (keeps GUI responsive)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        quit_application()