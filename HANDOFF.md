# Open Vision Measure 交接文档

更新时间：2026-11-04

## 1. 项目概况

- 产品名：Open Vision Measure
- 仓库：<https://github.com/JinCV0/open-vision-measure>
- 当前版本：`0.2.0`
- 当前分支：`main`
- 当前提交：`7c10c03`
- 许可证：Apache-2.0
- 技术栈：Python 3.12、PySide6、OpenCV、NumPy、PyInstaller
- 目标平台：Windows x64

项目是一个本地运行的相机预览与图像测量工具，是独立实现，不包含
JCameraPro 的代码、资源或模型。

## 2. 当前发布物

发布页：

<https://github.com/JinCV0/open-vision-measure/releases/tag/v0.2.0>

本机构建目录：

```text
H:\Project\open-vision-measure\release\0.2.0\windows-x64
```

文件：

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `OpenVisionMeasure.exe` | 99,161,128 bytes | `b574fca87e157931dfb90910ab0a34cd6b2e05b0616ec902d41da3c9a087ca5f` |
| `OpenVisionMeasure-0.2.0-win64.zip` | 98,583,529 bytes | `0d96e394566db1329da797bd3944d159af58fff373d5ad44942eb987bd81f229` |

当前 EXE 没有 Authenticode 数字签名，Windows SmartScreen 可能提示未知发布者。

## 3. 已实现功能

### 相机

- 支持 OpenCV 的 MSMF、DirectShow、V4L2 后端。
- Auto 模式在 Windows 上按 MSMF、DirectShow 顺序尝试。
- 默认分辨率和帧率显示为 `Best`。
- Best 模式会探测 `YUY2`、`UYVY`、`NV12`、`MJPG`、`H264` 和驱动默认格式，
  以实际读到的最高分辨率为第一优先级，同分辨率下优先无压缩格式。
- 相机采集在后台线程运行；UI 使用单槽缓冲，只保留最新帧。

### 图像处理

- 亮度
- 对比度
- 色温
- 色调
- 灰度
- 边缘预览

右侧 Image 面板使用滑块控制。色温修正红/蓝通道，色调修正绿/品红偏色。

### 测量与标定

- 在画布上通过两次点击创建一条测量线。
- 当前标定流程仍为：先画参考线，输入已知长度和单位，再点击
  `Calibrate last line`。
- 支持 `mm`、`cm`、`in`、`px`。
- 标定数据和测量线会写入项目 JSON。
- 原界面底部测量表格已经删除；测量数据仍用于项目保存和 CSV 导出。

### 截图

- 首次截图选择目标文件。
- 保存目录和扩展名写入用户偏好。
- 后续截图自动扫描目录中的 `capture_数字` 文件，从最大编号继续递增。
- 支持中文及非 ASCII Windows 路径。
- 当前提供 `Folder` 按钮用于更换保存目录。

### 标尺水印

- 完成标定后可启用 `Scale bar`。
- 标尺在实时画布和截图中使用相同归一化位置。
- 默认位置为左下角。
- 可在画布上直接拖动标尺。
- 位置、启用状态和截图目录会持久化。

注意：当前代码仍使用自动 `1/2/5 × 10ⁿ` 标尺长度，而不是用户要求的固定物理长度。
标尺改版尚未实现。

### 数据文件

- 项目文件：`.ovm.json`
- 测量导出：CSV
- 用户偏好：

```text
%LOCALAPPDATA%\OpenVisionMeasure\preferences.json
```

偏好文件包含：

```text
schema_version
screenshot_directory
screenshot_extension
scale_bar_enabled
scale_bar_position
```

## 4. 代码结构

```text
src/vision_measure/
  camera/
    models.py            相机、模式、配置和帧模型
    backend.py           CameraBackend/CameraSession 接口和类型化错误
    opencv_backend.py    OpenCV 后端、模式协商、最佳模式选择
    pump.py              后台取帧线程
    buffer.py            最新帧单槽缓冲
    synthetic.py         测试用合成相机
  inspection/
    models.py            点、线、单位、标定和测量结果
    calibration.py       像素长度与物理长度换算
    processing.py        亮度、对比度、色温、色调、灰度、边缘
    annotations.py       标尺几何和 OpenCV 标尺渲染
  workspace/
    controller.py        应用状态机、测量、截图和 CSV
    project.py           项目 JSON 原子读写
    models.py            ProjectDocument
    preferences.py       用户偏好原子读写
    screenshot.py        截图编号、Unicode 路径和安全写盘
  ui/
    app.py               应用入口
    main_window.py       窗口装配和事件连接
    panels.py            右侧控制面板
    viewport.py          图像、测量线、标尺和拖动交互
    camera_tasks.py      相机发现/打开后台线程
```

依赖方向：

```text
ui -> workspace/camera/inspection
workspace -> camera interfaces + inspection
inspection -> NumPy/OpenCV only
```

## 5. 当前测试与验证

最近一次完整验证：

```text
38 passed
Ruff: passed
mypy: passed
wheel/sdist build: passed
PyInstaller packaged --smoke-test: passed
```

真实相机历史验证：

- `Astra Pro HD Camera`
- DirectShow 后端
- 已成功读取 `1280×720` 帧
- 已成功验证中文路径截图

当前未完成：

- 自动 Best 模式的真实相机最高分辨率/像素格式验收。
- 60 秒连续预览和内存稳定性测试。

最近一次准备真实验收时，相机被 Codex 随行占用：

```text
capture_agent.py
parent: codex-mobile.exe
```

在测试本软件前需关闭 Codex 随行的摄像头/实时画面，或经用户明确授权后再处理
占用进程。

## 6. 尚未实现的需求

用户正在重新设计标尺和手动标定交互，但尚未批准最终交互方案，也尚未修改代码。

已确认的产品要求：

- 标尺显示固定物理长度，而不是自动选择 `1/2/5 × 10ⁿ`。
- 标尺位置可在画布上拖动，默认左下角。
- 用户认为当前“最后一条线 + Calibrate last line”的操作不易理解。

待确认的推荐交互：

1. 用户在右侧输入已知实际长度和单位。
2. 点击 `Set calibration`。
3. 在画布上依次点击参考物的两个端点。
4. 第二次点击后立即完成标定并退出标定模式。

该交互尚未实现，后续开发者不应把现有 `Calibrate last line` 当作最终交互。

## 7. 已知风险和技术债

1. 自动 Best 模式通过多次打开相机来探测格式，部分驱动上可能较慢；需要在实际
   相机上测量启动耗时。
2. 窗口图标仍使用 PyInstaller 默认图标。
3. EXE 未签名。
4. PySide6 完整包体积较大，EXE 约 94.6 MiB；如果后续继续优化发布体积，应先
   验证 Qt 依赖裁剪不会破坏 DLL 加载。
5. 标尺的几何计算和 PySide6 绘制是两套渲染实现，但共用
   `inspection/annotations.py` 的几何结果。修改标尺样式时必须同时检查实时画布
   和保存截图。
6. 当前版本没有录像、AI、Excel、授权、支付、多语言、更新、WebUI 或联网功能。

## 8. 开发命令

安装和运行：

```powershell
cd H:\Project\open-vision-measure
uv sync --extra dev
uv run vision-measure
```

测试：

```powershell
uv run ruff check .
uv run mypy src
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest
```

构建 Python 包：

```powershell
uv build
```

构建 Windows 单文件 EXE：

```powershell
pwsh -NoProfile -File scripts\build_windows.ps1 -Version 0.2.0
```

构建脚本会：

1. 同步锁定依赖。
2. 运行 PyInstaller。
3. 运行 `OpenVisionMeasure.exe --smoke-test`。
4. 生成 `SHA256SUMS.txt`。
5. 生成包含 EXE、许可证和第三方声明的 ZIP。

## 9. 发布流程

1. 更新 `pyproject.toml`、`src/vision_measure/__init__.py`、
   `packaging/windows-version-info.txt` 和 `THIRD_PARTY_NOTICES.md` 中的版本。
2. 运行全部测试、Ruff、mypy 和 `uv build`。
3. 运行 `scripts/build_windows.ps1`。
4. 在真实相机上验包。
5. 提交并推送 `main`。
6. 创建 GitHub Release，上传 EXE、ZIP 和校验文件。

## 10. 下一步建议

1. 先完成标定交互重设计，并建立“标定模式”状态机测试。
2. 将标尺长度改为可编辑的固定物理长度，并验证拖动后截图一致。
3. 在 Codex 随行释放相机后，记录真实相机的 Best 模式分辨率、像素格式和启动耗时。
4. 执行 60 秒预览稳定性测试并记录内存曲线。
5. 发布 `0.3.0`。

交接时若上下文丢失，以本文件、`docs/superpowers/specs/` 和 `docs/superpowers/plans/`
中的文档为准；已发布行为以 `v0.2.0` Release 二进制和对应 Git 提交为准。
