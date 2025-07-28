import gradio as gr

from webui2.ui.handlers import refresh_preset_list


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
        fn=refresh_preset_list,
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
