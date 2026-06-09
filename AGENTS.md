# AGENTS.md

This repository is the MaaPJSK source package. The real Git project root is
`outputs/MaaPJSK` inside the Codex workspace.

## Project Shape

- `assets/interface.json`: MFAAvalonia interface/task metadata.
- `assets/resource/pipeline/story.json`: MaaFramework pipeline nodes.
- `assets/resource/image/`: template images used by pipeline recognition.
- `agent/story_actions.py`: Python custom actions for story navigation and reading.
- `tools/install_mfaavalonia_app.py`: builds/syncs the local MFAAvalonia runtime.
- `install-mfaavalonia/`: generated local runtime, ignored by Git.

Do not commit generated runtime files, logs, caches, screenshots, or zip packages.
The user intends to push source changes to Git, not distribute a zip.

## Runtime Sync

After changing source assets, pipeline, agent code, or config, sync the generated
MFAAvalonia runtime before asking the user to test:

```powershell
python -c "from pathlib import Path; from tools.install_mfaavalonia_app import copy_project_files; copy_project_files(Path('install-mfaavalonia'), 'debug')"
```

If the GUI is already open, ask the user to stop the task and restart MFAAvalonia
when resource loading may be stale.

## Checks

Run these checks before committing:

```powershell
python tools\check_project.py
python -m compileall -q agent tools
install-mfaavalonia\python\python.exe install-mfaavalonia\tools\check_project.py
install-mfaavalonia\python\python.exe -c "import ast, pathlib; ast.parse(pathlib.Path('install-mfaavalonia/agent/story_actions.py').read_text(encoding='utf-8')); print('INSTALL AST OK')"
```

## Story Automation Rules

- The project targets PJSK story reading through MaaFramework + MFAAvalonia.
- The controller uses `display_short_side: 720`; many coordinates are logical
  720p Maa coordinates, not raw 1920x1080 device coordinates.
- The user asked not to broadly refactor the current absolute/logical coordinate
  approach unless requested again.
- Red `!` badges must not be used as the primary unread/readable criterion. They
  can disappear after opening a story even if content is still unread.
- Chapter section readability is based on `SKIP` template plus the tight cyan/text
  color check. Keep `use_unread_badge_as_readable` false unless the user asks.
- If the current chapter list has no readable `SKIP` rows, the action should go
  back to the outer story list/filter flow, not mark the whole task complete.
- After finishing one section, return to the chapter page and rescan instead of
  blindly rereading the same row.
- If only one readable section remains, do not enable next-story auto read.

## Debugging

Useful logs:

```text
install-mfaavalonia/logs/log-YYYYMMDD.log
install-mfaavalonia/debug/maafw.log
```

Useful ADB path seen in this workspace:

```text
C:\Users\ciqiong\AppData\Local\Android\platform-tools\adb.exe
```

When diagnosing recognition failures, check the maafw log for template scores.
For example, a recent stuck page was caused by `story_home_confirm.png` scoring
about `0.752869` while the threshold was `0.78`.

To capture the current device screen when a device is connected:

```powershell
$adb='C:\Users\ciqiong\AppData\Local\Android\platform-tools\adb.exe'
& $adb shell screencap -p /sdcard/maapjsk.png
& $adb pull /sdcard/maapjsk.png work\maapjsk.png
```

## Git

Remote is expected to be:

```text
https://github.com/Ciqong/MaaPJSK.git
```

Use focused commits. Do not revert unrelated user changes in a dirty worktree.
