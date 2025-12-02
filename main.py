"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              ⚡ ElAnswer                                       ║
║           AI-Powered Screen Capture & Question Solver                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Description:  Captures screen content and uses Google Gemini AI to          ║
║                analyze and solve questions, problems, or code snippets.      ║
║                                                                               ║
║  Version:      1.1.0                                                          ║
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
from datetime import datetime
import keyboard  # For detecting key presses
import google.generativeai as genai
from PIL import ImageGrab, Image, ImageTk  # For taking screenshots and image handling
import tkinter as tk
from tkinter import scrolledtext
import threading
import ctypes
import pystray  # For system tray icon

# Enable High DPI awareness for crisp rendering
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Fallback for older Windows
    except:
        pass

# ---------------- CONFIGURATION ---------------- #

# PASTE YOUR API KEY HERE
# Or set it as an environment variable: os.environ["GEMINI_API_KEY"]
API_KEY = "YOUR_GEMINI_API_KEY_HERE"

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

# Maximum number of history items to keep
MAX_HISTORY_ITEMS = 10

# ----------------------------------------------- #

# Global variable for the popup window
popup_window = None
popup_hidden = False  # Track if popup is hidden
loading_indicator = None  # Loading indicator window
logo_image = None  # Store logo image reference
tray_icon = None  # System tray icon

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(SCRIPT_DIR, "assets", "logo.png")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
HISTORY_PATH = os.path.join(SCRIPT_DIR, "history.json")

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
    default_config = {"popup_x": 200, "popup_y": 80, "theme": "light"}
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**default_config, **config}
    except Exception as e:
        print(f"[!] Could not load config: {e}")
    return default_config

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[!] Could not save config: {e}")

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
        print(f"[!] Could not load history: {e}")
        answer_history = []

def save_history():
    """Save answer history to file."""
    try:
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(answer_history[:MAX_HISTORY_ITEMS], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Could not save history: {e}")

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

# Load answer history
load_history()

def configure_genai():
    """Configures the Gemini API."""
    if API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("ERROR: Please edit the script and add your Gemini API Key.")
        return None
    
    genai.configure(api_key=API_KEY)
    # Using 1.5 Flash because it is fast and cheap for vision tasks
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    return model

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
        print(f"[!] Could not load logo: {e}")
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
    print("\n[+] Hotkey detected! Capturing screen...")
    
    # Show loading indicator on main thread
    root.after(0, show_loading_indicator)
    
    def process_and_display():
        try:
            # 1. Capture the entire screen
            screenshot = ImageGrab.grab()
            
            # 2. visual feedback
            print("[-] Screen captured. Sending to Gemini...")
            
            # 3. Prepare the prompt
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

            # 4. Send to Gemini
            response = model.generate_content([prompt, screenshot])
            
            # 5. Hide loading indicator and display result in popup
            answer = response.text
            print("[✓] Answer received. Displaying popup...")
            
            # Add to history
            add_to_history(answer)
            
            # Hide loading indicator and show popup on main thread
            root.after(0, hide_loading_indicator)
            root.after(50, lambda: show_answer_popup(answer))
            
            print(f"Ready for next query. Press {HOTKEY}...")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"\n[!] {error_msg}")
            # Hide loading indicator and show error
            root.after(0, hide_loading_indicator)
            root.after(50, lambda: show_answer_popup(error_msg))
    
    # Run analysis in separate thread to avoid blocking
    threading.Thread(target=process_and_display, daemon=True).start()

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
            print("[+] UI shown")
        else:
            # Hide the windows
            if has_popup:
                popup_window.withdraw()
            if has_loading:
                loading_indicator.withdraw()
            popup_hidden = True
            print("[-] UI hidden")
    else:
        print("[!] No UI elements to hide/show")

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
    print(f"[+] Theme switched to {new_theme} mode {theme_icon}")
    
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
    
    if model:
        # Create hidden root window for tkinter
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Add the hotkey listeners
        keyboard.add_hotkey(HOTKEY, analyze_screen)
        keyboard.add_hotkey(HIDE_HOTKEY, toggle_popup_visibility)
        keyboard.add_hotkey(THEME_HOTKEY, toggle_theme)
        keyboard.add_hotkey(HISTORY_HOTKEY, show_history_popup)
        keyboard.add_hotkey(QUIT_HOTKEY, quit_application)
        
        # Start system tray icon in separate thread
        tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
        tray_thread.start()
        
        # Hide console window (runs minimized in system tray)
        hide_console()
        
        # Run tkinter main loop (keeps GUI responsive)
        try:
            root.mainloop()
        except KeyboardInterrupt:
            quit_application()