<p align="center">
  <img src="assets/logo.png" alt="ElAnswer Logo" width="120" height="120">
</p>

<h1 align="center">⚡ ElAnswer</h1>

<p align="center">
  <strong>AI-powered screen capture tool that instantly solves questions, problems, and code snippets on your screen.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/AI-Google%20Gemini-orange.svg" alt="AI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## ✨ Features

- 🖥️ **Instant Screen Capture** - Press a hotkey to capture your entire screen
- 🤖 **AI-Powered Analysis** - Uses Google Gemini 2.5 Flash to analyze and solve problems
- 📋 **Smart Formatting** - Answers are organized with Question, Answer, and Explanation sections
- 🎨 **Modern UI** - Clean, professional popup with rounded corners and smooth animations
- 👻 **Stealth Mode** - Window is undetectable by other apps (no taskbar, no Alt+Tab)
- 📌 **Always on Top** - Answer popup stays visible above all windows
- 📝 **One-Click Copy** - Copy the entire answer to clipboard instantly
- ⌨️ **Keyboard Shortcuts** - Full hotkey support for quick access
- ⚡ **Loading Indicator** - Small blinking logo at bottom-left shows when AI is processing
- 👁️ **Quick Hide/Unhide** - Instantly toggle visibility of all UI elements with a hotkey

## 🖼️ Screenshot

```
┌─────────────────────────────────────┐
│                              ×      │
│  ⚡ ElAnswer                        │
│  AI-powered answer to your screen   │
│  ┌─────────────────────────────┐   │
│  │ 📋 QUESTION:                │   │
│  │ [Identified question]       │   │
│  │                             │   │
│  │ ✅ ANSWER:                  │   │
│  │ [Direct answer]             │   │
│  │                             │   │
│  │ 💡 EXPLANATION:             │   │
│  │ [Why this is correct]       │   │
│  └─────────────────────────────┘   │
│  ● Response generated              │
│  [Copy] [Close]      ESC to close  │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Windows 10/11
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/XploitGh0st/elanswer.git
   cd elanswer
   ```

2. **Install dependencies**
   ```bash
   pip install google-generativeai keyboard pillow
   ```

3. **Configure your API key**
   
   Open `main.py` and replace the API key:
   ```python
   API_KEY = "your-gemini-api-key-here"
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Alt + S` | Capture screen and get AI answer |
| `Ctrl + Alt + I` | Hide/Unhide UI (popup & loading indicator) |
| `Ctrl + Alt + Q` | Quit the application |
| `ESC` | Close the answer popup |

## 🎯 Use Cases

- 📚 **Online Quizzes** - Get instant answers to multiple choice questions
- 💻 **Coding Problems** - Solve programming challenges and debug code
- 📖 **Homework Help** - Understand and solve academic problems
- 🔧 **Technical Questions** - Get explanations for technical concepts
- 🧮 **Math Problems** - Solve equations and mathematical expressions

## 🛠️ Configuration

You can customize the hotkeys in `main.py`:

```python
# The Hotkey combination to trigger the capture
HOTKEY = "ctrl+alt+s"

# The Hotkey combination to quit the application
QUIT_HOTKEY = "ctrl+alt+q"

# The Hotkey combination to hide/unhide the popup
HIDE_HOTKEY = "ctrl+alt+i"
```

## 📁 Project Structure

```
elanswer/
├── main.py          # Main application file
├── README.md        # This file
├── requirements.txt # Python dependencies
├── LICENSE          # MIT License
└── assets/
    └── logo.png     # Application logo
```

## 🔒 Privacy & Security

- **Local Processing** - Screenshots are captured locally and sent directly to Google's Gemini API
- **No Storage** - Images are not stored or saved anywhere
- **Stealth Mode** - The application window is hidden from screen recording and monitoring software

## ⚠️ Disclaimer

This tool is intended for educational purposes and personal use. Please use responsibly and in accordance with your institution's academic integrity policies.

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI model for image analysis
- [Python Keyboard](https://github.com/boppreh/keyboard) - Global hotkey detection
- [Pillow](https://python-pillow.org/) - Screen capture functionality

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/XploitGh0st">Nanda Kumaran G</a> & <a href="https://github.com/Saffronzen005">Saffron Zen</a>
</p>
