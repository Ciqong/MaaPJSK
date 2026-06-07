# MaaPJSK

MaaPJSK 是基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 和 [MFAAvalonia](https://github.com/MaaXYZ/MFAAvalonia) 的《世界计划》剧情自动阅读助手。

当前主要用于自动阅读主线剧情：进入剧情列表、滚动到列表底部、选择带有 `SKIP` 或红色叹号标记的章节、开始阅读，并在可用时勾选“自动阅读下一张剧情”。

## 功能

- 支持从游戏主页面或剧情页面附近开始运行。
- 自动进入主线剧情页面并设置未读过滤。
- 剧情列表会先滑到最下面，再从底部往上寻找可读章节。
- 只会点击带 `SKIP` 或红色叹号标记的章节。
- 进入阅读前会尝试勾选“自动阅读下一张剧情”。
- 支持无语音确认、资源下载按钮、网络重试弹窗。
- 使用 `display_short_side: 720` 作为逻辑分辨率，适配 1080p 以外的横屏分辨率。

## 一键运行

双击仓库根目录的：

```text
Run.bat
```

首次运行会自动生成 `install-mfaavalonia/`，下载 MFAAvalonia、准备内置 Python，并安装 Agent 依赖。之后再次双击会直接启动 GUI。

需要重新生成运行目录时：

```powershell
.\Run.bat --rebuild
```

生成完成后也可以直接启动：

```text
install-mfaavalonia/Start-MaaPJSK.bat
```

## 使用步骤

1. 启动模拟器或连接安卓设备，确认 ADB 可用。
2. 将游戏切到横屏，进入游戏主页面或剧情页面附近。
3. 双击 `Run.bat` 打开 MFAAvalonia。
4. 在 GUI 中选择安卓 ADB 控制器并连接设备。
5. 运行任务“自动阅读主线剧情”。

## 分辨率

项目不绑定 `1920x1080`。MaaFramework 会把设备截图映射到短边 720 的逻辑坐标，再执行识别和点击。

常见横屏设备会接近这些逻辑尺寸：

- 16:9：`1280x720`
- 更宽的横屏：例如 `1520x720`

Pipeline 中尽量使用负坐标 ROI、宽范围搜索和模板中心点击，以减少不同宽高比带来的偏移。若游戏 UI 在特殊比例下明显重排，需要重新截图裁剪模板，并调整 `assets/resource/pipeline/story.json` 中的 `roi` 和 `threshold`。

## 项目结构

```text
assets/
  interface.json
  resource/
    icon.png
    image/
    pipeline/
agent/
  main.py
  story_actions.py
config/
tools/
Run.bat
```

仓库只提交源码、资源和构建脚本，不提交 `install-mfaavalonia/`、日志、缓存或 zip 包。

## 调试

本地自检：

```powershell
python tools/check_project.py
python -m py_compile agent/main.py agent/story_actions.py tools/check_project.py tools/install_mfaavalonia_app.py
```

运行包内也有：

```text
install-mfaavalonia/Check-Project.bat
```

日志默认输出到：

```text
install-mfaavalonia/debug/maafw.log
install-mfaavalonia/logs/
```

如需查看识别可视化结果，可以把 `config/maa_option.draw.json` 覆盖到 `config/maa_option.json`，或手动把 `save_draw` 改为 `true`。识别截图会输出到 `debug/vision/`。

## 开发工具

推荐配合 MaaFramework README 中的开发工具使用：

- MFAAvalonia：通用 GUI，用于加载 `interface.json` 并运行任务。
- maa-support-extension：VSCode 插件，用于截图、ROI 裁剪、节点跳转和补全。
- MaaDebugger：单节点调试 Pipeline 识别和动作。
- MFAToolsPlus / ImageCropper：连接设备截图、裁剪 720p 模板、获取 ROI。
- MaaPipelineEditor / MaaInspector：查看和编辑 `resource/pipeline/story.json`。
- MaaLogAnalyzer / MaaLogs：分析 `maafw.log` 和任务执行路径。

## 维护提示

- 如果漏点 `SKIP`，优先重新裁剪 `assets/resource/image/skip_badge.png`，并检查每行 ROI。
- 如果读完后停在列表不继续，查看日志里是否出现 `Story list marker matched`。
- 如果点击了错误章节，检查 `story_row_points`、`skip_color_roi` 和模板阈值。
