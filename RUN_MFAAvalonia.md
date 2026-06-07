# MFAAvalonia 整合包运行说明

本项目可以打成 MFAAvalonia GUI 整合包，目录里会包含：

- `MFAAvalonia.exe`
- `interface.json`
- `resource/`
- `agent/`
- `config/`
- `python/` 内置 Python 和 Agent 依赖

## 从 git 源码构建

仓库里只需要提交源码、资源和构建脚本，不需要提交 MFAAvalonia、内置 Python、runtime 或 zip。

最简单的方式是直接双击仓库根目录的：

```text
Run.bat
```

它会在首次运行时自动生成 `install-mfaavalonia/`，之后会直接启动 GUI。

如果要强制重新下载并重建运行目录：

```powershell
.\Run.bat --rebuild
```

手动构建也可以运行：

在仓库根目录运行：

```powershell
python tools\install_mfaavalonia_app.py --mfa-version v2.12.1 --output install-mfaavalonia
```

脚本会自动下载 MFAAvalonia、Python embeddable，并安装 `MaaFw` 与 `numpy`。生成目录 `install-mfaavalonia/` 已被 `.gitignore` 忽略。

## 直接运行

构建完成后，双击：

```text
install-mfaavalonia/Start-MaaPJSK.bat
```

或直接运行：

```text
install-mfaavalonia/MFAAvalonia.exe
```

然后在 GUI 中：

1. 选择安卓 ADB 控制器并连接模拟器。
2. 确认模拟器横屏，游戏已经进入主页或故事页附近。
3. 运行任务“自动阅读主线剧情”。

## 分辨率

项目使用 `display_short_side: 720` 作为逻辑分辨率，不再绑定 1920x1080。MaaFramework 会把不同真实分辨率的截图映射到短边 720 的逻辑坐标。

如果某些超宽屏、窄屏或 UI 改版后识别不稳，优先使用 MFAAvalonia / MaaDebugger / VSCode maa-support-extension 重新截图并裁剪模板，再调整 `resource/pipeline/story.json` 里的 `roi`、`threshold` 和模板文件。

## 自检

双击：

```text
Check-Project.bat
```

它会检查 pipeline、模板文件、Agent 语法，以及内置 Python 是否可以导入 `maa` 和 `numpy`。

## 调试

日志和截图默认输出到：

```text
debug/
```

如果识别失败，把 `config/maa_option.draw.json` 复制覆盖为 `config/maa_option.json`，或手动把 `save_draw` 改成 `true`，再重新运行任务。可视化识别结果会输出到 `debug/vision/`。
