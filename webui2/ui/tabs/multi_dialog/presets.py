import gradio as gr

from webui2.utils import preset_mgr


def create_multi_dialog_presets():
    with gr.Row(elem_id="multi-dialog-presets"):
        # Preset components
        preset_dropdown = gr.Dropdown(
            label="预设列表",
            choices=preset_mgr.get_preset_list(),
            value=None,
            interactive=True,
            allow_custom_value=False,
            scale=2,
        )
        preset_name_input = gr.Textbox(
            label="新预设名称",
            placeholder="输入新预设名称",
            interactive=True,
            lines=1,
        )
        with gr.Column(scale=2):
            with gr.Row():
                load_preset_btn = gr.Button("加载预设", size="sm", min_width=80)
                refresh_preset_btn = gr.Button("刷新列表", size="sm", min_width=80)
            with gr.Row():
                save_preset_btn = gr.Button("保存预设", size="sm", min_width=80)
                delete_preset_btn = gr.Button("删除预设", size="sm", min_width=80)

    # Bind events
    refresh_preset_btn.click(
        fn=on_refresh_preset_list,
        outputs=[preset_dropdown],
    )

    return (
        preset_dropdown,
        load_preset_btn,
        preset_name_input,
        save_preset_btn,
        delete_preset_btn,
    )


def on_refresh_preset_list():
    """Refresh the preset dropdown list"""
    preset_list = preset_mgr.get_preset_list()
    choices = preset_list if preset_list else []
    return gr.update(choices=choices, value=choices[0] if choices else None)


def on_save_preset_click(
    preset_name,
    # Settings
    interval,
    gen_subtitle,
    subtitle_model,
    subtitle_lang,
    bgm_volume,
    bgm_loop,
    # Advanced params
    do_sample,
    top_p,
    top_k,
    temperature,
    length_penalty,
    num_beams,
    repetition_penalty,
    max_mel_tokens,
    speaker_count,
    *speakers,
):
    """Handle saving a preset"""
    if not preset_name or preset_name.strip() == "":
        gr.Error("❌ 请输入要保存的预设名称")
        print("[webui2] [Error] No preset name provided")
        return gr.update()

    preset_name = preset_name.strip()

    # Extract parameters from args
    # Speaker names (6) + Server audio paths (6) + Audio files (6) + Settings (6) + Advanced (8) = 32
    speakers_data = {}
    audio_data = {}

    for i in range(speaker_count):
        speakers_data[f"speaker{i + 1}_name"] = speakers[i * 3]

    # Server audio paths - these are the actual selected server files
    for i in range(speaker_count):
        audio_data[f"speaker{str(i + 1)}_audio"] = speakers[i * 3 + 1]

    preset_data = preset_mgr.collect_preset_data(
        speaker_count,
        speakers_data,
        audio_data,
        interval,
        gen_subtitle,
        subtitle_model,
        subtitle_lang,
        bgm_volume,
        bgm_loop,
        advanced_params=[
            do_sample,
            top_p,
            top_k,
            temperature,
            length_penalty,
            num_beams,
            repetition_penalty,
            max_mel_tokens,
        ],
    )

    success = preset_mgr.save_preset(preset_name, preset_data)

    if success:
        gr.Info(f"✅ 预设 '{preset_name}' 保存成功")
    else:
        gr.Error(f"❌ 保存预设 '{preset_name}' 失败")

    return on_refresh_preset_list()


def on_delete_preset_click(preset_name):
    """Handle deleting a preset"""
    if not preset_name:
        gr.Error("❌ 请选择要删除的预设")
        return on_refresh_preset_list()

    success = preset_mgr.delete_preset(preset_name)

    if success:
        gr.Info(f"✅ 预设 '{preset_name}' 删除成功")
    else:
        gr.Error(f"❌ 删除预设 '{preset_name}' 失败")

    return on_refresh_preset_list()


def on_load_preset_click(preset_name):
    """Handle loading a preset"""
    if not preset_name:
        gr.Error("请选择一个预设")
        print("[webui2] [Error] No preset selected")
        return
    else:
        print("[webui2] [Info] 加载预设:", preset_name)

    preset_data = preset_mgr.load_preset(preset_name)
    if not preset_data:
        gr.Error("加载预设失败")
        return

    config, speaker_count = preset_mgr.flatten_preset_config(preset_data)
    speakers_data: list[tuple] = []
    for i in range(speaker_count):
        speakers_data.append(
            (
                config.get(f"speaker{i + 1}_name", f"角色{i + 1}"),
                config.get(f"speaker{i + 1}_audio", None),
            )
        )

    # Return updates in the order of components
    result = []
    # Settings (6)
    result.append(config.get("interval", 0.5))
    result.append(config.get("gen_subtitle_multi", True))
    result.append(config.get("subtitle_model_multi", "base"))
    result.append(config.get("subtitle_lang_multi", "zh"))
    result.append(config.get("bgm_volume_multi", 0.3))
    result.append(config.get("bgm_loop_multi", True))

    # Advanced params (8)
    result.append(config.get("do_sample", True))
    result.append(config.get("top_p", 0.8))
    result.append(config.get("top_k", 30))
    result.append(config.get("temperature", 1.0))
    result.append(config.get("length_penalty", 0.0))
    result.append(config.get("num_beams", 3))
    result.append(config.get("repetition_penalty", 10.0))
    result.append(config.get("max_mel_tokens", 600))

    result.append(speaker_count)
    result.append(speakers_data)

    return result
