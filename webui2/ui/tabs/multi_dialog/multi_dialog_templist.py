import gradio as gr

from webui2.ui.handlers.generate import (
    merge_from_temp_files,
    regenerate_single,
)


def create_temp_list(pick_args: list[gr.Component], output_audio: gr.Audio):
    """
    clickhandler:
        (text, audio_output_path, temp_files) -> temp_files
    """

    st_temp_list = gr.State([])  # list of (text, audio_path)
    st_curr_page = gr.State(1)
    unit = 5  # count per page

    @gr.render(inputs=(st_temp_list, st_curr_page))
    def render_temp_dialog_list(temp_list: list[tuple[str, str]], curr_page: int):
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

            prev_5_btn.click(fn=lambda :max(1, curr_page - 5), outputs=st_curr_page)  # fmt: skip
            prev_btn.click(fn=lambda :max(1, curr_page - 1), outputs=st_curr_page)  # fmt: skip
            next_btn.click(fn=lambda :min(all_pages, curr_page + 1), outputs=st_curr_page)  # fmt: skip
            next_5_btn.click(fn=lambda :min(all_pages, curr_page + 5), outputs=st_curr_page)  # fmt: skip

        if len(temp_list) != 0:
            if (curr_page - 1) * unit > len(temp_list):
                back_btn = gr.Button(value="返回第一页")
                back_btn.click(fn=lambda: 1, outputs=st_curr_page)
            else:
                for i in range(
                    (curr_page - 1) * unit, min((curr_page) * unit, len(temp_list))
                ):
                    with gr.Row(scale=1):
                        (text, audio_path) = temp_list[i]
                        with gr.Column():
                            text_box = gr.Textbox(
                                value=text, label=f"句子 {i + 1}", interactive=True
                            )
                            re_btn = gr.Button(value="重新生成")

                            text_box.blur(
                                fn=update_textbox(i),
                                inputs=[text_box, st_temp_list],
                                outputs=st_temp_list,
                            )
                            re_btn.click(
                                fn=bind_regen_click_param(text, audio_path),
                                inputs=[st_temp_list, *pick_args],
                                outputs=st_temp_list,
                            )

                        gr.Audio(value=audio_path, label="Audio")

        gr.Button(value="合并音频").click(
            fn=merge_from_temp_files, inputs=[st_temp_list], outputs=output_audio
        )

    return st_temp_list


def update_textbox(i: int):
    def inner(text: str, temp_list: list[tuple[str, str]]) -> list[tuple[str, str]]:
        new_list = temp_list.copy()
        if 0 <= i < len(new_list):
            audio_path = new_list[i][1]
            new_list[i] = (text, audio_path)
        return new_list

    return inner


def bind_regen_click_param(text, audio_output_path):
    def inner(
        # from templist
        temp_list,
        # from pick args
        speakers_data,
        do_sample,
        top_p,
        top_k,
        temperature,
        length_penalty,
        num_beams,
        repetition_penalty,
        max_mel_tokens,
    ):
        return regenerate_single(
            text,audio_output_path,temp_list,speakers_data,
            "普通推理",
            do_sample, top_p, top_k, temperature,
            length_penalty, num_beams, repetition_penalty, max_mel_tokens,
        )  # fmt: skip

    return inner
