import json
import os
import shutil
from pathlib import Path
from typing import Callable

import gradio as gr

from webui2.config import TEMP_DIR
from webui2.ui.handlers.generate import merge_from_temp_files, regenerate_single


def create_temp_list(
    pick_args: gr.State,  # state of list[gr.Component]
    output_audio: gr.Audio,
    interval: gr.Slider,
    session: gr.State,
    md_session: gr.Markdown,
):
    st_temp_list = gr.State([])  # list of (text, audio_path)
    st_curr_page = gr.State(1)
    unit = 5  # count per page

    @gr.render(inputs=(st_temp_list, st_curr_page))
    def render_temp_dialog_list(temp_list: list[tuple[str, str]], curr_page: int):
        all_pages: int = (len(temp_list) + unit - 1) // unit

        print(
            f"[webui2] [Debug] render_temp_dialog_list: {len(temp_list)} items, {all_pages} pages"
        )

        gr.Markdown(
            "## 🗂️ 对话列表\n\n生成的对话列表。",
            key="temp_list_header",
            elem_id="anchor-temp-list",
        )

        if len(temp_list) != 0:
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

            # Main List
            if (curr_page - 1) * unit > len(temp_list):
                back_btn = gr.Button(value="返回第一页")
                back_btn.click(fn=lambda: 1, outputs=st_curr_page)
            else:
                for i in range(
                    (curr_page - 1) * unit, min((curr_page) * unit, len(temp_list))
                ):
                    with gr.Row(scale=1):
                        (text, audio_path) = temp_list[i]
                        single_audio = gr.Audio(
                            value=audio_path,
                            label="Audio",
                            key=f"audio_{audio_path}",
                            interactive=False,
                            type="filepath",
                        )
                        with gr.Column():
                            text_box = gr.Textbox(
                                value=text,
                                label=f"句子_{i + 1}",
                                interactive=True,
                                key=f"text_{text}",
                            )
                            # text_box value is auto-updated
                            # but not re-render according to st_temp_list
                            text_box.blur(
                                fn=update_textbox(i), inputs=[text_box, st_temp_list]
                            )

                            re_btn = gr.Button(value="重新生成")
                            # update single_audio with new audio
                            re_btn.click(
                                fn=regenerate_single,
                                inputs=[
                                    text_box,
                                    single_audio,
                                    st_temp_list,
                                    session,
                                    pick_args,
                                ],
                                outputs=single_audio,
                            )

            with gr.Row():
                prev_5_btn2 = gr.Button("<<", key="prev_5_btn2", min_width=48)
                prev_btn2 = gr.Button("<", key="prev_btn2", min_width=48)
                gr.HTML(
                    f'<div style="text-align: center">{curr_page if all_pages > 0 else 0}  / {all_pages}</div>'
                )
                next_btn2 = gr.Button(">", key="next_btn2", min_width=48)
                next_5_btn2 = gr.Button(">>", key="next_5_btn2", min_width=48)

                prev_5_btn2.click(fn=lambda :max(1, curr_page - 5), outputs=st_curr_page)  # fmt: skip
                prev_btn2.click(fn=lambda :max(1, curr_page - 1), outputs=st_curr_page)  # fmt: skip
                next_btn2.click(fn=lambda :min(all_pages, curr_page + 1), outputs=st_curr_page)  # fmt: skip
                next_5_btn2.click(fn=lambda :min(all_pages, curr_page + 5), outputs=st_curr_page)  # fmt: skip

            gr.Button(
                value="合并音频", key="merge_audio", elem_classes=["bg-accent"]
            ).click(
                fn=merge_from_temp_files,
                inputs=[st_temp_list, interval],
                outputs=output_audio,
            )

        with gr.Row():
            dp = gr.Dropdown(
                label="选择对话",
                choices=get_temp_lists(),
                key="get_temp_lists",
                interactive=True,
            )
            gr.Button(value="加载对话", key="load_temp_list").click(
                fn=load_temp_list,
                inputs=dp,
                outputs=[st_temp_list, session, md_session],
            )
            gr.Button(value="保存对话", key="save_temp_list").click(
                fn=save_temp_list, inputs=[st_temp_list, session], outputs=dp
            )
        gr.Button(
            value="清空所有临时目录", key="clear all", size="sm", min_width=80, scale=0
        ).click(fn=lambda: clean_temp_files(str(TEMP_DIR)))
        with gr.Row():
            new_session_name = gr.Textbox(
                label="新的对话名",
                placeholder="我的对话",
            )
            gr.Button(value="重命名对话", key="rename_session").click(
                fn=rename_session,
                inputs=[new_session_name, session, st_temp_list],
                outputs=[session, md_session, dp],
            )
            gr.Button(value="查看当前对话名", key="check_session").click(
                fn=lambda s: gr.Info(f"当前session: {s}", 3),
                inputs=session,
            )

    return st_temp_list


def update_temp_list_with_audio(index: int) -> Callable:
    # 这边不要触发重新渲染了，因为 audio 重新渲染过了
    def inner(
        temp_list: list[tuple[str, str]], audio_path: str
    ) -> list[tuple[str, str]]:
        if 0 <= index < len(temp_list):
            text = temp_list[index][0]
            temp_list[index] = (text, audio_path)
            gr.Info(f"更新第 {index + 1} 项的音频路径为: {audio_path}", 3)
        return temp_list

    return inner


def update_textbox(i: int) -> Callable:
    # 这边不要触发重新渲染了，因为 text value 自动变的重新渲染过了
    def inner(text: str, temp_list: list[tuple[str, str]]) -> list | None:
        if 0 <= i < len(temp_list):
            audio_path = temp_list[i][1]
            temp_list[i] = (text, audio_path)
            gr.Info(f"更新第 {i + 1} 项的文本为: {text}", 3)
        return

    return inner


def get_temp_lists() -> list[tuple[str, str]]:
    """Get the list of temporary dialog files"""
    temp_dir = TEMP_DIR
    if not temp_dir.exists():
        temp_dir.mkdir(parents=True, exist_ok=True)
        return []

    temp_files = list(temp_dir.rglob("*.json"))

    def key(f: Path) -> str:
        """
        Example: "a/b/c/d.json" -> "c/d.json"
        """
        parts = f.parts
        return str(Path(*parts[-2:]))

    return [(key(file), str(file)) for file in temp_files]


# temp_list format: list of tuples (text, audio_path)
# save format should be a JSON file with each entry as a dict
def save_temp_list(temp_list: list[tuple[str, str]], session: str):
    output_file = str(TEMP_DIR / f"{session}" / "temp_list.json")
    if not temp_list:
        gr.Warning("临时对话列表为空，无法保存")
        return

    data = [{"text": text, "audio_path": audio_path} for text, audio_path in temp_list]
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            gr.Success(f"临时对话列表已保存到 {output_file}")
            return gr.update(choices=get_temp_lists())
    except Exception as e:
        gr.Error(f"保存临时对话列表失败: {e}")
        print(f"Error: saving temp list: {e}")
        return gr.update(choices=get_temp_lists())


def load_temp_list(
    input_path="",
) -> list[list[tuple[str, str]] | str | None] | None:
    file = Path(input_path)

    if not file.is_file():
        raise FileNotFoundError(input_path)

    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            temp_list = [(item["text"], item["audio_path"]) for item in data]
            session = file.parent.name
            gr.Success(
                f"临时对话列表已加载: {len(temp_list)} 条记录\n文件\nsession: {session}"
            )
            print(f"[webui2] [Debug] load_temp_list: session set to {session}")
            return [temp_list, session, f"当前对话 Session: **{session}**"]

    except Exception as e:
        raise RuntimeError(f"Error when load_temp_list: {e}") from e


def rename_session(name: str, last_session: str, temp_list: list[tuple[str, str]]):
    if "/" in name or "\\" in name:
        gr.Error("Session 名称不能包含斜杠或反斜杠")
        return [gr.update(), gr.update(), gr.update()]

    # check if last_session directory exists
    dirname = TEMP_DIR / last_session
    if not dirname.exists():
        gr.Error(f"原始 Session {dirname} 不存在，无法重命名")
        print(f"Error: original session {dirname} does not exist")
        return [gr.update(), gr.update(), gr.update()]

    # rename the directory
    new_dirname = TEMP_DIR / name
    try:
        dirname.rename(new_dirname)
        gr.Success(f"Session 已重命名为 {new_dirname}")
    except Exception as e:
        gr.Error(f"重命名对话失败: {e}")
        return [gr.update(), gr.update(), gr.update()]

    # replace temp_list
    for i, (text, audio_path) in enumerate(temp_list):
        if last_session in audio_path:
            new_audio_path = audio_path.replace(last_session, name)
            temp_list[i] = (text, new_audio_path)

    # replace temp_list file
    data = [{"text": text, "audio_path": audio_path} for text, audio_path in temp_list]
    output_file = str(new_dirname / "temp_list.json")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            gr.Success(f"临时对话列表已保存到 {output_file}")

            return [
                name,
                f"当前 Session: **{name}**",
                gr.update(choices=get_temp_lists()),
            ]

    except Exception as e:
        gr.Error(f"保存临时对话列表失败，需手动更改 templist.json 中的音频路径: {e}")
        print(f"Error: saving temp list. Modify audio paths templist.json {e}")
        return [gr.update(), gr.update(), gr.update(choices=get_temp_lists())]


def clean_temp_files(temp_dir: str):
    if not os.path.exists(temp_dir):
        return
    for file in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, file)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"无法删除 {file_path}: {e}")
    gr.Warning(f"已清理临时文件夹 {temp_dir} 中的所有文件")
    print(f"已经清理临时文件夹 {temp_dir} 中的所有文件")
