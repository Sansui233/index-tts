# Multi-Dialog Preset System

This directory contains preset files for the multi-dialog generation feature.

## How to Use

### Loading Presets
1. Click the "刷新列表" (Refresh List) button to load available presets
2. Select a preset from the dropdown list
3. Click "加载预设" (Load Preset) to apply the preset settings

### Saving Presets
1. Configure all the settings as desired (speaker names, intervals, subtitle settings, BGM settings, and advanced parameters)
2. Enter a name for your preset in the "预设名称" (Preset Name) field
3. Click "保存预设" (Save Preset) to save the current configuration

### Deleting Presets
1. Select the preset you want to delete from the dropdown list
2. Click "删除预设" (Delete Preset) to remove the preset file

## What Gets Saved

Presets include:
- **Speaker Names**: Names for all 6 speaker slots
- **Server Audio Paths**: If server audio files are selected, their paths will be saved and restored
- **Dialog Settings**: Interval between speakers
- **Subtitle Settings**: Whether to generate subtitles, model choice, language
- **Background Music Settings**: Volume and loop settings (BGM files are NOT saved)
- **Advanced Parameters**: All TTS generation parameters (do_sample, top_p, top_k, etc.)

## What Does NOT Get Saved

- Manually uploaded audio files (only server audio paths are saved)
- Dialog text content
- Generated output files
- Background music files (only volume/loop settings)

## Server Audio Selection

For each speaker, you can:
1. **Select Server Audio**: Choose from available audio files on the server using the dropdown
2. **Upload Your Own**: Use the audio upload component for custom files
3. **Use Microphone**: Record directly using the microphone option

When you select a server audio file from the dropdown, it will automatically load into the audio component. If you save a preset while server audio is selected, the audio path will be included in the preset and restored when you load it later.

## Preset File Format

Presets are stored as JSON files with the following structure:

```json
{
  "speakers": {
    "speaker1_name": "角色名1",
    "speaker2_name": "角色名2",
    ...
  },
  "settings": {
    "interval": 0.8,
    "gen_subtitle": true,
    "subtitle_model": "base",
    "subtitle_lang": "zh",
    "bgm_volume": 0.2,
    "bgm_loop": true
  },
  "advanced_params": {
    "do_sample": true,
    "top_p": 0.9,
    "top_k": 35,
    "temperature": 1.1,
    "length_penalty": 0.1,
    "num_beams": 3,
    "repetition_penalty": 8.0,
    "max_mel_tokens": 500
  }
}
```

## Notes

- Preset files must have a `.json` extension
- Preset names should not contain special characters that are invalid for filenames
- The system automatically manages the preset directory and file operations
- If a preset file becomes corrupted, simply delete it and create a new one
