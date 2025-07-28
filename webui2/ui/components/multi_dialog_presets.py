import gradio as gr

from webui2.ui.handlers.preset import collect_preset_data
from webui2.utils import preset_manager


def create_multi_dialog_presets():
    with gr.Row(elem_id="multi_dialog_presets"):
        # Preset components
        with gr.Column(scale=2):
            preset_dropdown = gr.Dropdown(
                label="预设列表",
                choices=[],
                value=None,
                interactive=True,
                allow_custom_value=False,
            )
        with gr.Column(scale=1):
            load_preset_btn = gr.Button("加载预设", size="sm")
        with gr.Column(scale=1):
            refresh_preset_btn = gr.Button("刷新列表", size="sm")
        with gr.Column(scale=2):
            preset_name_input = gr.Textbox(label="预设名称", placeholder="输入新预设名称", interactive=True)
        with gr.Column(scale=1):
            save_preset_btn = gr.Button("保存预设", size="sm")
        with gr.Column(scale=1):
            delete_preset_btn = gr.Button("删除预设", size="sm")

    preset_status = gr.Markdown("", visible=True)

    # Bind events
    refresh_preset_btn.click(
        fn=on_refresh_preset_list,
        outputs=[preset_dropdown],
    )

    return (
        preset_dropdown,
        load_preset_btn,
        refresh_preset_btn,
        preset_name_input,
        save_preset_btn,
        delete_preset_btn,
        preset_status,
    )


def on_refresh_preset_list():
    """Refresh the preset dropdown list"""
    preset_list = preset_manager.get_preset_list()
    choices = preset_list if preset_list else []
    return gr.update(choices=choices, value=choices[0] if choices else None)


def on_save_preset_click(preset_name, *args):
    """Handle saving a preset"""
    if not preset_name or not preset_name.strip():
        return gr.update(value="❌ 请输入预设名称"), on_refresh_preset_list()

    preset_name = preset_name.strip()

    # Extract parameters from args
    # Speaker names (6) + Server audio paths (6) + Audio files (6) + Settings (6) + Advanced (8) = 32
    speakers_data = {}
    audio_data = {}

    for i in range(6):
        speakers_data[f"speaker{i + 1}_name"] = args[i]

    # Server audio paths - these are the actual selected server files
    for i in range(6):
        server_audio_path = args[i + 6]
        if server_audio_path:  # Only save if a server audio is selected
            audio_data[f"speaker{i + 1}_audio"] = server_audio_path

    # Skip the uploaded audio files (args[12:18]) as we don't save those paths

    # Settings start at index 18 (6 names + 6 server audio + 6 uploaded audio)
    interval = args[18]
    gen_subtitle = args[19]
    subtitle_model = args[20]
    subtitle_lang = args[21]
    bgm_volume = args[22]
    bgm_loop = args[23]

    # Advanced params start at index 24
    advanced_params = list(args[24:32])

    preset_data = collect_preset_data(
        speakers_data,
        interval,
        gen_subtitle,
        subtitle_model,
        subtitle_lang,
        bgm_volume,
        bgm_loop,
        advanced_params,
        audio_data,
    )

    success = preset_manager.save_preset(preset_name, preset_data)

    if success:
        message = f"✅ 预设 '{preset_name}' 保存成功"
    else:
        message = f"❌ 保存预设 '{preset_name}' 失败"

    return gr.update(value=message), on_refresh_preset_list()


def on_delete_preset_click(preset_name):
    """Handle deleting a preset"""
    if not preset_name:
        return gr.update(value="❌ 请选择要删除的预设"), on_refresh_preset_list()

    success = preset_manager.delete_preset(preset_name)

    if success:
        message = f"✅ 预设 '{preset_name}' 删除成功"
    else:
        message = f"❌ 删除预设 '{preset_name}' 失败"

    return gr.update(value=message), on_refresh_preset_list()
