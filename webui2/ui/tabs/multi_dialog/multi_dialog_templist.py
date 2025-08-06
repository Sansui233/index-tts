import json

import gradio as gr

from webui2.ui.handlers.generate import (
    TEMP_DIR,
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
        gr.Markdown(
            "### 🗂️ 对话列表\n\n生成的对话列表。\n编辑文字后，需要点击文本框外保存。",
            elem_id="anchor-temp-list",
        )
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
                                value=text,
                                label=f"句子_{i + 1}",
                                interactive=True,
                                key=f"text_{text}",
                            )
                            text_box.blur(
                                fn=update_textbox(i),
                                inputs=[text_box, st_temp_list],
                                outputs=st_temp_list,
                            )

                            re_btn = gr.Button(value="重新生成")
                            re_btn.click(
                                fn=bind_regen_click_param(text, audio_path),
                                inputs=[st_temp_list, *pick_args],
                                outputs=st_temp_list,
                            )

                        gr.Audio(
                            value=audio_path, label="Audio", key=f"audio_{audio_path}"
                        )

        gr.Button(value="合并音频", key="merge_audio").click(
            fn=merge_from_temp_files, inputs=[st_temp_list], outputs=output_audio
        )
        with gr.Row():
            gr.Button(value="加载列表", key="load_temp_list").click(
                fn=load_temp_list, outputs=st_temp_list
            )
            gr.Button(value="保存列表", key="save_temp_list").click(
                fn=save_temp_list, inputs=st_temp_list
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
        progress=gr.Progress(),
    ):
        return regenerate_single(
            text,audio_output_path,temp_list,speakers_data,
            "普通推理",
            do_sample, top_p, top_k, temperature,
            length_penalty, num_beams, repetition_penalty, max_mel_tokens,
            progress=progress
        )  # fmt: skip

    return inner


TEMP_LIST_FILE = TEMP_DIR / "temp_list.json"


# temp_list format: list of tuples (text, audio_path)
# save format should be a JSON file with each entry as a dict
def save_temp_list(temp_list: list[tuple[str, str]]):
    if not temp_list:
        gr.Warning("临时对话列表为空，无法保存")
        return

    data = [{"text": text, "audio_path": audio_path} for text, audio_path in temp_list]
    try:
        with open(TEMP_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            gr.Success(f"临时对话列表已保存到 {TEMP_LIST_FILE}")
    except Exception as e:
        gr.Error(f"保存临时对话列表失败: {e}")
        print(f"Error: saving temp list: {e}")
        return


def load_temp_list() -> list[tuple[str, str]] | None:
    if not TEMP_LIST_FILE.exists():
        gr.Error(f"临时对话列表文件不存在: {TEMP_LIST_FILE}")
        return

    try:
        with open(TEMP_LIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            temp_list = [(item["text"], item["audio_path"]) for item in data]
            gr.Success(f"临时对话列表已加载: {len(temp_list)} 条记录")
            return temp_list
    except Exception as e:
        gr.Error(f"加载临时对话列表失败: {e}")
        print(f"Error: loading temp list: {e}")
        return
