import gradio as gr


def create_temp_list():
    temp_list = gr.State([])  # list of (text, audio_path)
    curr_page_state = gr.State(1)
    unit = 2  # count per page

    @gr.render(inputs=(temp_list, curr_page_state))
    def render_temp_dialog_list(temp_list, curr_page: int):
        all_pages: int = (len(temp_list) + unit - 1) // unit

        print(
            f"[webui2] [Debug] render_temp_dialog_list: {len(temp_list)} items, {all_pages} pages"
        )

        """Render the temporary dialog list"""
        gr.Markdown("### 🗂️ 临时对话列表", elem_id="anchor-temp-list")
        with gr.Row():
            prev_5_btn = gr.Button("<<", key="prev_5_btn", min_width=48)
            prev_btn = gr.Button("<", key="prev_btn", min_width=48)
            gr.HTML(
                f'<div style="text-align: center">{curr_page if all_pages > 0 else 0}  / {all_pages}</div>'
            )
            next_btn = gr.Button(">", key="next_btn", min_width=48)
            next_5_btn = gr.Button(">>", key="next_5_btn", min_width=48)

            prev_5_btn.click(fn=lambda :max(1, curr_page - 5), outputs=curr_page_state)  # fmt: off
            prev_btn.click(fn=lambda :max(1, curr_page - 1), outputs=curr_page_state)  # fmt: off
            next_btn.click(fn=lambda :min(all_pages, curr_page + 1), outputs=curr_page_state)  # fmt: off
            next_5_btn.click(fn=lambda :min(all_pages, curr_page + 5), outputs=curr_page_state)  # fmt: off

        if len(temp_list) != 0:
            if (curr_page - 1) * unit > len(temp_list):
                btn = gr.Button(value="返回第一页")
                btn.click(fn=lambda: 1, outputs=curr_page_state)
            else:
                for i in range(
                    (curr_page - 1) * unit, min((curr_page) * unit, len(temp_list))
                ):
                    with gr.Row(scale=1):
                        (text, audio_path) = temp_list[i]
                        with gr.Column():
                            gr.Textbox(
                                value=text,
                                label=f"句子 {i + 1}",
                                interactive=True,
                                key=f"s{i + 1}",
                            )
                            gr.Button(value="重新生成", key=f"b{i + 1}")
                        gr.Audio(value=audio_path, label="Audio", key=f"a{i + 1}")

        gr.Button(value="重新合并音频")

    return temp_list
