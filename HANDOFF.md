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

- 标定卡片提供 `比例尺` 开关和独立的 `比例尺设置…` 窗口。
- 设置窗口包括实时预览、五种预设、四种形态、水平/垂直方向、
  标签位置与显隐、描边、四组颜色、整体透明度、底板样式与透明度、
  线宽、刻度长度、字号、分段数量和 3×3 九宫格位置。
- 五种预设为 `简洁线`、`科研描边`、`分段标尺`、`Material 绿`、`紧凑括号`。
- 物理长度按倍率独立保存；视觉样式和位置作为全局偏好保存。
- 比例尺必须有明确的固定物理长度。缺少固定长度时不绘制，也不会自动拟合
  一个不同的长度。
- 修改标定单位会清除旧标定及旧比例尺长度；重新标定并启用比例尺时使用
  `10.0` 当前单位作为可见的固定默认值。
- 实时画布和保存截图使用同一套样式模型与几何计算。
- 比例尺可拖动，位置按归一化图像坐标保存。
- 截图使用 OpenCV 可渲染的 ASCII 单位标签，微米显示为 `um`。
- 全局偏好 schema v2 保存比例尺样式；v1 偏好可自动迁移。

### 项目数据

- 项目文件：`.ovm.json`
- 测量导出：CSV
- schema v2 保存倍率、标定、标尺长度、测量来源倍率和图像设置。

### 界面

- Material You 风格，暖中性页面、卡片表面和绿色主操作色。
- 60-30-10 配色、统一间距、圆角和 12/14/18px 字号。
- 跟随系统浅色/深色模式。
- 中文界面；驱动和格式技术名保留原文。
- 比例尺设置使用独立弹窗，浅色、深色及 100%/150% 缩放布局均通过检查。

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
| `OpenVisionMeasure.exe` | 99,217,119 bytes | `d62dd1200133ede4104eed4414bbfcd5cedc8508fb7f42618f09b9a21fdfa282` |
| `OpenVisionMeasure-0.3.0-win64.zip` | 98,638,415 bytes | `356656c5b3c2c9e7422ddd3ceb34a8cc7a094b8f0e1271cb498bc0bcd69b4ada` |

Python 包：

```text
dist/open_vision_measure-0.3.0-py3-none-any.whl
dist/open_vision_measure-0.3.0.tar.gz
```

EXE 没有 Authenticode 数字签名，Windows SmartScreen 可能显示未知发布者。

## 测试与验证

比例尺工作室完成后实际执行：

```text
ruff: passed
mypy strict: passed, 35 source files
pytest: 96 passed
light/dark and 100%/150% native renders: passed
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

1. 用真实电子目镜完成比例尺工作室和微米单位的端到端验收。
2. 完成 60 秒预览稳定性测试。
3. 根据真实切片反馈继续增强面积、周长和统计功能。
4. AI 背景去除保持在核心应用之外。
