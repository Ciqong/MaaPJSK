# Development Notes

本项目按 MaaFramework README 的开发工具链整理，推荐用下面这些工具维护。

## Recommended Tools

- MFAAvalonia: 运行通用 UI，加载 `install/interface.json`。
- maa-support-extension: VSCode 插件，用于跳转节点、补全、取截图 ROI、按 MaaPiCli 模式执行。
- MaaDebugger: Pipeline 调试器，适合单节点验证识别与动作。
- MFAToolsPlus / ImageCropper: 连接设备截图、裁剪模板、获取 ROI。
- MaaPipelineEditor / MaaInspector: 可视化查看和编辑 `resource/pipeline/story.json`。
- MaaLogAnalyzer / MaaLogs: 分析 `debug/maafw.log` 和任务执行路径。
- Auto Green Background: 给模板图做绿色遮罩，减少 TemplateMatch 背景干扰。
- prettier-plugin-maafw-sort: 按 Maa Pipeline 生命周期顺序整理字段。

## Project Layout

```text
interface.json
resource/
  image/
  pipeline/
agent/
config/
  maa_option.json
```

开发目录里对应源文件在：

```text
assets/interface.json
assets/resource/
agent/
config/
```

## Debug Options

默认 `config/maa_option.json` 会保存日志和失败截图：

```json
{
    "logging": true,
    "save_draw": false,
    "save_on_error": true,
    "stdout_level": 4,
    "draw_quality": 85
}
```

如果要排查模板命中问题，把 `config/maa_option.draw.json` 复制覆盖为 `config/maa_option.json`，或者手动把 `save_draw` 改成 `true`。启用后图像识别可视化结果会输出到 `debug/vision/`。

## Template Workflow

1. 使用 MFAAvalonia、MFAToolsPlus、VSCode 插件或 ImageCropper 获取 720p 逻辑截图。
2. 裁剪模板到 `resource/image/` 或 `assets/resource/image/`。
3. 在 `resource/pipeline/story.json` 里调整 `template`、`roi` 和 `threshold`。
4. 用 MaaDebugger 或 MFAAvalonia 单跑任务。
5. 若识别失败，开启 `save_draw`，再用 MaaLogAnalyzer/MaaLogs 看 `debug/maafw.log` 与 `debug/vision/`。

## Quick Checks

```powershell
python tools/check_project.py
python -m py_compile agent/main.py agent/story_actions.py
```
