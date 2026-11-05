# Open Vision Measure 开发状态

更新时间：2026-11-05

## 项目概况

- 仓库：<https://github.com/JinCV0/open-vision-measure>
- 许可证：Apache-2.0
- 当前版本：`0.3.0`
- 默认分支：`main`
- 技术栈：Python 3.12、PySide6、OpenCV、NumPy、PyInstaller
- 目标平台：Windows x64

项目是独立实现，不包含 JCameraPro 的代码、资源或模型。

## 当前范围

### 相机

- MSMF、DirectShow、V4L2 后端。
- 自动选择最佳相机模式，也支持指定分辨率、帧率和格式。
- 后台取帧、冻结/恢复、停止和错误处理。

### 图像

- 亮度、对比度、色温、色调。
- 灰度、边缘预览。
- 普通截图、目录记忆和编号顺延。
- 中文和 Unicode Windows 路径。

### 测量与标定

- `Measure` 一次性两点测量模式，完成或取消后自动退出。
- 普通浏览点击不会绘制测量线。
- 每个倍率独立保存标定。
- 已知长度支持毫米、厘米、微米、英寸和像素。
- 单位修改会使旧标定失效，并显示“未标定 · 请重新标定”。
- v1 项目可迁移到 schema v2。

### 比例尺

- 用户输入固定物理长度，不使用不可见自动长度替代。
- 比例尺长度输入框显示当前单位，例如 `10.0000 微米`。
- 勾选比例尺时提交输入框中的固定长度。
- 实时画布和保存截图共用同一个几何函数。
- 比例尺可拖动，位置按归一化图像坐标保存。
- 截图使用 OpenCV 可渲染的 ASCII 单位标签，微米显示为 `um`。
- 切换倍率或修改标定单位后，比例尺使用新的当前标定，不沿用旧单位。

### 项目数据

- 项目文件：`.ovm.json`
- 测量导出：CSV
- schema v2 保存倍率、标定、标尺长度、测量来源倍率和图像设置。

### 界面

- Material You 风格，暖中性页面、卡片表面和绿色主操作色。
- 60-30-10 配色、统一间距、圆角和 12/14/18px 字号。
- 跟随系统浅色/深色模式。
- 中文界面；驱动和格式技术名保留原文。

## AI 功能状态

AI 截图已经完整下线：

- 不显示 AI 截图入口。
- 不包含 rembg、BiRefNet、ONNX Runtime 或模型权重。
- 不包含主体分割、掩膜清理、AI 后台线程或 AI 预览。
- 安装包不再提供 `--WithAI` 构建模式。

后续如需要 AI 背景去除，应由用户或独立扩展自行实现，并重新评估模型质量、
许可、内存和真实切片验收。

## 本地 0.3.0 构建物

目录：

```text
release/0.3.0/windows-x64
```

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `OpenVisionMeasure.exe` | 99,183,137 bytes | `bb0925884d91c6f562424be7718ea4afd7a60fa99443c931e241bb0c1f5dc16c` |
| `OpenVisionMeasure-0.3.0-win64.zip` | 98,604,872 bytes | `34bf32aac7f3762130335a2b2ddc2473329cf8afd7d12bf47720e0775310c44e` |

Python 包：

```text
dist/open_vision_measure-0.3.0-py3-none-any.whl
dist/open_vision_measure-0.3.0.tar.gz
```

EXE 没有 Authenticode 数字签名，Windows SmartScreen 可能显示未知发布者。

## 测试与验证

本次实际执行：

```text
ruff: passed
mypy strict: passed, 28 source files
pytest: 71 passed
wheel/sdist: passed
PyInstaller EXE: passed
packaged smoke: passed
```

真实相机历史结果：

```text
DirectShow, 1280x720, YUY2
发现：约 1.03 秒
打开：约 13.95 秒
首帧：约 0.10 秒
```

仍未完成：

- 真实电子目镜上的完整倍率切换、标定、测量和比例尺截图验收。
- 60 秒真实相机预览和内存稳定性。
- 区域面积、周长、统计汇总、Excel。
- 打包 EXE 的真实硬件验收。

## 构建命令

```powershell
pwsh -NoProfile -File scripts/build_windows.ps1 -Version 0.3.0
```

构建脚本只安装基础运行和开发依赖，不再安装 AI 依赖。

## 公开仓库状态

- 仓库可见性：PUBLIC
- 许可证：Apache-2.0
- 贡献指南、安全策略、行为准则、Issue/PR 模板已发布。
- Dependabot 安全更新、Secret Scanning 和推送保护已启用。
- GitHub Actions CI 文件仍需在 OAuth 获得 `workflow` scope 后启用。

## 下一步优先级

1. 用真实电子目镜完成比例尺和微米单位的端到端验收。
2. 完成 60 秒预览稳定性测试。
3. 根据真实切片反馈继续增强面积、周长和统计功能。
4. AI 背景去除保持在核心应用之外。
