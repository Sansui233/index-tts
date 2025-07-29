# WebUI2 - Refactored IndexTTS Web Interface

## Overview

This is a refactored version of the IndexTTS web interface, organized into a clean, modular structure for better maintainability and extensibility.

## Project Structure

```
webui2/
├── __init__.py                 # Package initialization
├── main.py                     # Main entry point
├── config/                     # Configuration and setup
│   ├── __init__.py
│   └── settings.py            # Arguments, paths, validation
├── audio/                     # Audio processing modules
│   ├── __init__.py
│   ├── tts_engine.py         # TTS engine wrapper and management
│   ├── audio_mixer.py        # Background music mixing
│   └── subtitle_generator.py # Subtitle generation utilities
├── ui/                       # User interface components
│   ├── __init__.py
│   ├── components.py         # Reusable UI components
│   ├── handlers.py           # Event handlers for UI interactions
│   └── tabs/                 # Individual tab definitions
│       ├── __init__.py
│       ├── single_audio.py   # Single audio generation tab
│       ├── multi_dialog.py   # Multi-dialog generation tab
│       └── subtitle_only.py  # Subtitle-only generation tab
└── utils/                    # Utility functions
    ├── __init__.py
    └── helpers.py            # General helper functions
```

## Key Improvements

### 1. **Separation of Concerns**
- **Configuration**: Centralized in `config/` module
- **Audio Processing**: Isolated in `audio/` module  
- **UI Components**: Organized in `ui/` module with sub-modules
- **Utilities**: General helpers in `utils/` module

### 2. **Modular Design**
- Each tab is now a separate module
- Reusable UI components are extracted
- Event handlers are centralized
- Audio processing utilities are modularized

### 3. **Better Code Organization**
- Clear import structure
- Reduced code duplication
- Easier testing and maintenance
- Better scalability for future features

### 4. **Improved Maintainability**
- Each module has a single responsibility
- Dependencies are clearly defined
- Code is more readable and debuggable

## Usage

### Running the Application
```bash
python webui2/main.py
```

Or use the provided batch file:
```bash
run.bat
```

### Key Components

#### TTS Manager (`audio/tts_engine.py`)
- Manages TTS engine initialization
- Handles caching and configuration
- Loads example cases

#### Subtitle Manager (`audio/subtitle_generator.py`)
- Handles subtitle generation with different models
- Manages Whisper model lifecycle
- Provides error handling and cleanup

#### UI Components (`ui/components.py`)
- Reusable UI element factories
- Consistent styling and behavior
- Parameterized component creation

#### Event Handlers (`ui/handlers.py`)
- Centralized event handling logic
- Clean separation from UI definition
- Easier testing and debugging

## Migration Notes

### From webui2.py to webui2/
The original monolithic `webui2.py` file has been split into:

1. **Configuration** → `config/settings.py`
2. **TTS Management** → `audio/tts_engine.py` 
3. **Audio Mixing** → `audio/audio_mixer.py`
4. **Subtitle Generation** → `audio/subtitle_generator.py`
5. **UI Components** → `ui/components.py`
6. **Event Handlers** → `ui/handlers.py`
7. **Tab Definitions** → `ui/tabs/*.py`
8. **Main Application** → `main.py`

### Key Benefits
- **Easier debugging**: Issues can be isolated to specific modules
- **Better testing**: Each module can be tested independently
- **Team development**: Multiple developers can work on different modules
- **Feature extension**: New tabs and features can be added easily
- **Code reuse**: Components can be reused across different parts of the app

## Development

### Adding New Features
1. **New Audio Processing**: Add to `audio/` module
2. **New UI Components**: Add to `ui/components.py`
3. **New Tabs**: Create new file in `ui/tabs/`
4. **New Configuration**: Add to `config/settings.py`

### Testing
Use the provided test script to validate the structure:
```bash
python test_webui2_structure.py
```

## Dependencies

The modular structure maintains the same dependencies as the original:
- gradio
- torch/transformers
- pydub
- scipy
- numpy
- And other IndexTTS dependencies

## Future Enhancements

The modular structure enables:
- Plugin system for new audio processors
- Theme system for UI customization  
- Configuration file support
- API endpoints for external integration
- Comprehensive testing suite
- Documentation generation
