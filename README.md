# MaaPJSK

基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 重构的世界计划主线剧情自动阅读助手。

## 重构目标

- 使用 MaaFramework 的 ADB 控制器替代裸 `uiautomator2`。
- 使用 Pipeline JSON 描述主流程，便于可视化调试和后续维护。
- 使用 `display_short_side: 720` 作为逻辑分辨率，适配不同真实分辨率。
- 将动态阅读逻辑放到 Python Agent，避免在 JSON 中硬写大量循环。

## 分辨率策略

本项目不再绑定 `1920x1080`。MaaFramework 会把设备截图缩放到短边 720，再按这个逻辑分辨率进行识别和点击。

在横屏 16:9 设备上，逻辑坐标约等于 `1280x720`。如果模拟器使用更宽的横屏比例，逻辑宽度也会随之增加，例如参考截图为 `1520x720`。Maa 会自动把逻辑坐标映射回真实设备坐标。

对于更宽或更窄的横屏比例，Pipeline 尽量使用：

- 模板命中框点击：`target: true`
- 边缘锚定 ROI/target：负坐标
- 较宽的 ROI 搜索区域

如果游戏 UI 在特殊比例下发生明显重排，需要重新裁剪模板或添加一套资源包。

## 项目结构

```text
assets/
  interface.json
  resource/
    image/
      *.png
    pipeline/
      story.json
agent/
  main.py
  story_actions.py
config/
  maa_option.json
  maa_option.draw.json
tools/
  check_project.py
```

## 使用方法

推荐加载打包后的运行目录：

```text
install/interface.json
```

通用 UI 会从 `interface.json` 读取：

- `controller`：使用 `安卓端` ADB 控制器。
- `resource`：加载同目录下的 `resource/`。
- `agent`：启动 `agent/main.py` 执行自定义动作。
- `task`：显示任务 `自动阅读主线剧情`。

运行步骤：

1. 安装 Python Agent 依赖：

   ```powershell
   python -m pip install MaaFw numpy
   ```

2. 使用 MaaFramework 通用 UI 加载 `install/interface.json`。
3. 选择 `安卓端`，连接模拟器 ADB。
4. 手动进入游戏的故事主页或主界面附近。
5. 运行任务 `自动阅读主线剧情`。

开发调试时也可以直接加载：

```text
assets/interface.json
```

但此时 `resource` 与 `agent` 路径相对 `assets/`，不同通用 UI 的工作目录处理可能有差异。实际运行优先使用 `install/interface.json`。

## 开发工具

这个项目按 MaaFramework README 的开发工具链整理：

- MFAAvalonia：推荐运行 GUI，加载 `install/interface.json`。
- maa-support-extension：VSCode 插件，支持节点跳转、补全、截图、ROI 裁剪和 MaaPiCli 模式执行。
- MaaDebugger：单节点调试 Pipeline 识别与动作。
- MFAToolsPlus / ImageCropper：连接模拟器截图、裁剪 720p 模板、获取 ROI。
- MaaPipelineEditor / MaaInspector：可视化查看和编辑 `resource/pipeline/story.json`。
- MaaLogAnalyzer / MaaLogs：分析 `debug/maafw.log` 和任务执行路径。
- Auto Green Background：为 TemplateMatch 模板制作绿色遮罩。
- prettier-plugin-maafw-sort：按 Maa Pipeline 生命周期顺序格式化字段。

更多维护说明见 `DEVELOPMENT.md`。

## 调试

运行包根目录带有：

```text
config/maa_option.json
```

默认会保存日志和失败截图。日志路径通常是：

```text
debug/maafw.log
```

如果要排查识图问题，把 `config/maa_option.draw.json` 复制覆盖为 `config/maa_option.json`，或把其中的 `save_draw` 改成 `true`。识别可视化图会输出到：

```text
debug/vision/
```

本地快速检查：

```powershell
python tools/check_project.py
```

建议模拟器设置：

- 横屏
- 游戏语言/服务器 UI 与模板素材一致
- 网络稳定
- 关闭会影响截图的后台/省电限制

## 当前限制

- 关键素材已根据 `1520x720` 参考截图重新裁剪；未出现在截图中的入口/网络错误/开始按钮素材仍来自原项目模板迁移，建议后续用 Maa 截图工具继续补齐。
- Agent 的“阅读结束”判断使用截图差异检测回到剧情列表，真实设备上需要根据日志微调 `return_diff_threshold`。
- 目前主要覆盖主线剧情路径，活动剧情或 UI 大改版需要新增 Pipeline 节点和模板。
