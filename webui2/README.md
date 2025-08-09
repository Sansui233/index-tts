# IndexTTS WebUI2

功能新增：
- 多人对话生成
  - 预设管理
  - 对话批量生成
  - 单句重新生成
  - 合并对话，并加入间隔
- 字幕生成（依赖于 whisper 模型）

## 目录结构增加

```
index-tts 根目录
├── ...
├── checkpoints   # indextts 模型目录
│   └── whisper/  # whisper 模型目录（新）
├── indextts/
├── outputs/      # 输出目录
├── prompts/
├── samples/      # 音频样本目录（新）
├── ...
├── webui2/       # WebUI2 目录（新）
└── run_webui2.py # 启动脚本（新）
```

## 环境准备

在原版 IndexTTS 基础上，需要再安装一个 `opencc`。

```sh
pip install opencc
```

如果你用的整合包，需要自行找到整合包内 pip 路径。
- Windows 下通常为 `.venv/Scripts/pip`。

## 运行

在 Index-tts 根目录下
```sh
python run_webui2.py
```

## 使用

见 UI 内说明。

## License

GPL-3.0
