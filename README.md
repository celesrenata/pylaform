# Pylaform - Modern Resume Generator

## Overview
Pylaform is a dynamic, web-based resume generator that combines SQLite3, Python, PyLaTeX, and modern web technologies to create professional-looking resumes. With an AI-powered resume improvement helper and a clean, responsive UI, Pylaform makes the resume creation process efficient and enjoyable.

## Features
- **Web-based UI**: Clean, Bootstrap-powered interface for easy resume editing
- **AI Resume Helper**: Integrated AI assistant to improve your resume content with:
  - Core principle/tenet highlighting
  - Text-to-list conversion
  - Sentence restructuring
  - Content summarization
- **PDF Generation**: High-quality PDF output using LaTeX templates
- **Multiple Sections**: Support for contact information, summary, education, certifications, skills, employment history, and achievements
- **Local AI Integration**: Optional Ollama integration for privacy-focused AI assistance

## Installation Instructions

### Standard Installation
1. Clone the repository:
```
git clone https://github.com/celesrenata/pylaform.git
   cd pylaform
```


2. Set up a virtual environment (recommended):
```
python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```


3. Install dependencies:
```
pip install -r requirements.txt
```


4. Install LaTeX class file:
   - Navigate to the `resources` directory
   - Follow one of these guides to install the `res.cls` class:
     * [Windows](https://tex.stackexchange.com/questions/2063/how-can-i-manually-install-a-package-on-miktex-windows)
     * [Mac and Linux](https://tex.stackexchange.com/questions/8357/how-to-have-local-package-override-default-package)

5. Run the application:
```
python -m flask run
```


6. Open your browser and go to `http://127.0.0.1:5000`

### Docker Installation

1. Clone the repository:
```
git clone https://github.com/celesrenata/pylaform.git
   cd pylaform
```


2. Build and run the Docker container:
```
docker build -t pylaform .
   docker run -p 5000:5000 pylaform
```


3. Open your browser and go to `http://127.0.0.1:5000`

## AI Resume Helper Configuration

The AI resume helper is an optional feature that can improve your resume content. To use it:

1. Click the AI Resume Helper at the bottom of the screen
2. Click the settings gear icon
3. Configure Ollama:
   - Enable AI Features toggle
   - Set Ollama Server URL (default: http://localhost:11434)
   - Choose a model (e.g., llama3.2:1b)
   - Click "Save Settings"

### Setting up Ollama (optional)

To use the AI resume helper locally:

1. Install Ollama from [ollama.ai](https://ollama.ai/)
2. Start the Ollama service
3. In Pylaform, configure the AI helper to use your local Ollama server

## Usage

1. Navigate through the sidebar to edit different sections of your resume
2. Use the AI Helper to improve text content by:
   - Selecting content type (Core Principle, List, Restructure, Summarize)
   - Entering your text
   - Clicking "Improve Text"
3. Click "Generate PDF" to create your polished resume

## Development

- Built with Python 3.10+, Flask, SQLite3, PyLaTeX, and Bootstrap 5
- Uses modern JavaScript for the interactive components
- Integrates with Ollama for local AI processing

## Future Plans
- Additional LaTeX templates
- More AI improvement options
- Export to different formats
- Enhanced UI customization

## License
[MIT License](LICENSE)

## Contributors
Developed by Celes Hillyerd
GitHub: [@celesrenata](https://github.com/celesrenata)

---

Ready to create an impressive resume? Get started with Pylaform today!
