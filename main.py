"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              ⚡ ElAnswer                                       ║
║           AI-Powered Screen Capture & Question Solver                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Description:  Captures screen content and uses Google Gemini AI to          ║
║                analyze and solve questions, problems, or code snippets.      ║
║                                                                               ║
║  Version:      1.0.0                                                          ║
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
import time
import keyboard  # For detecting key presses
import google.generativeai as genai
from PIL import ImageGrab  # For taking screenshots
import tkinter as tk
from tkinter import scrolledtext
import threading
import ctypes

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

# ----------------------------------------------- #

# Global variable for the popup window
popup_window = None

def configure_genai():
    """Configures the Gemini API."""
    if API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("ERROR: Please edit the script and add your Gemini API Key.")
        return None
    
    genai.configure(api_key=API_KEY)
    # Using 1.5 Flash because it is fast and cheap for vision tasks
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    return model

def show_answer_popup(answer_text):
    """Creates a clean, professional popup window matching the reference design."""
    global popup_window
    
    # Close existing popup if any
    if popup_window and popup_window.winfo_exists():
        popup_window.destroy()
    
    # Create new popup window
    popup_window = tk.Toplevel()
    popup_window.title("")
    popup_window.geometry("480x520+200+80")
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
    
    # Clean, minimal color scheme (matching reference image)
    card_bg = '#ffffff'
    text_color = '#1a1a1a'
    secondary_text = '#6b7280'
    border_color = '#e5e7eb'
    accent_color = '#18181b'
    green_accent = '#22c55e'
    light_gray = '#f9fafb'
    
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
    close_btn.bind('<Enter>', lambda e: close_btn.config(fg='#374151'))
    close_btn.bind('<Leave>', lambda e: close_btn.config(fg='#9ca3af'))
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
    copy_btn.bind('<Enter>', lambda e: copy_btn.config(bg='#374151'))
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
    
    def fade_out_window(alpha=0.98):
        if alpha > 0:
            alpha -= 0.12
            popup_window.attributes('-alpha', alpha)
            popup_window.after(12, lambda: fade_out_window(alpha))
        else:
            popup_window.destroy()
    
    # Status dot pulse
    pulse_state = [True]
    def pulse_status():
        if not popup_window.winfo_exists():
            return
        if pulse_state[0]:
            status_dot.itemconfig(1, fill='#4ade80')
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
    
    for widget in [top_bar, header_section, title_row, title_label]:
        widget.bind('<Button-1>', start_move)
        widget.bind('<B1-Motion>', do_move)
    
    # Start animations
    popup_window.after(10, fade_in)
    popup_window.after(500, pulse_status)
    
def analyze_screen():
    """Captures screen, sends to Gemini, and displays answer in popup."""
    print("\n[+] Hotkey detected! Capturing screen...")
    
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
            
            # 5. Display result in popup
            answer = response.text
            print("[✓] Answer received. Displaying popup...")
            
            # Show popup on main thread
            root.after(0, lambda: show_answer_popup(answer))
            
            print(f"Ready for next query. Press {HOTKEY}...")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"\n[!] {error_msg}")
            root.after(0, lambda: show_answer_popup(error_msg))
    
    # Run analysis in separate thread to avoid blocking
    threading.Thread(target=process_and_display, daemon=True).start()

def quit_application():
    """Gracefully quit the application."""
    print("\n\n👋 ElAnswer closed. Goodbye!")
    root.quit()
    root.destroy()
    os._exit(0)

# Main Execution
if __name__ == "__main__":
    model = configure_genai()
    
    if model:
        print("="*50)
        print("       ✨ ElAnswer - AI Screen Solver ✨")
        print("="*50)
        print(f"\n📋 Instructions:")
        print(f"  1. Open your document/quiz/code on screen")
        print(f"  2. Press [{HOTKEY}] to get AI answer")
        print(f"  3. Press [{QUIT_HOTKEY}] to quit")
        print(f"  4. Or close this window to quit\n")
        print("⚡ Status: Ready and waiting...\n")
        
        # Create hidden root window for tkinter
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Add the hotkey listeners
        keyboard.add_hotkey(HOTKEY, analyze_screen)
        keyboard.add_hotkey(QUIT_HOTKEY, quit_application)
        
        # Suppress Ctrl+C in terminal by blocking keyboard module from capturing it
        try:
            # Run tkinter main loop (keeps GUI responsive)
            root.mainloop()
        except KeyboardInterrupt:
            print("\n\n👋 ElAnswer closed. Goodbye!")
            pass