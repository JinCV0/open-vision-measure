# Open Vision Measure 交接文档

更新时间：2026-11-05

## 1. 当前状态

- 产品名：Open Vision Measure
- 仓库：<https://github.com/JinCV0/open-vision-measure>
- 许可证：Apache-2.0
- 本机版本：`0.3.0`
- 开发分支：`feat/microscope-workflow`
- 当前行为基线：`09c8db6`
- 已发布版本：`v0.2.0`
- 技术栈：Python 3.12、PySide6、OpenCV、NumPy、PyInstaller
- 可选 AI 运行时：rembg 2.0.86、ONNX Runtime 1.31.1、BiRefNet

产品定位已从通用相机测量工具调整为：

> 面向显微镜电子目镜的植物组织切片观察、测量、截图和科研记录工具。

项目是独立实现，不包含 JCameraPro 的代码、资源或模型。

## 2. 已完成能力

### 相机与预览

- MSMF、DirectShow、V4L2 后端和自动发现。
- 后台取帧、冻结/恢复、停止、单槽最新帧。
- 亮度和对比度、色温、色调、灰度、边缘预览。

### 显微镜工作流

- 项目 schema v2。
- 倍率名称可由用户输入，内置 `4x`、`10x`、`40x`、`100x` 入口。
- 每个倍率独立保存标定、单位、参考长度和固定标尺长度。
- 切换倍率不会改写历史测量的来源倍率。
- 相机宽度、高度或像素格式变化时使当前倍率标定失效。
- v1 项目迁移到 `default` 倍率，不会把旧标定套到其他倍率。
- 新标定流程：输入已知长度 -> `Set calibration` -> 画布两次点击。
- 测量前必须点击一次 `Measure`；画布只在测量模式下接受两个点，完成一条线后自动退出。
- 普通浏览点击、拖标尺和标定点击不会误生成测量线。
- 未标定倍率显示 `未标定`。
- 标尺使用用户指定的固定物理长度，实时画布和截图共用同一几何函数。

### 截图与数据

- 保存普通截图，保持目录、扩展名和 `capture_0001` 顺延编号。
- 支持中文及非 ASCII Windows 路径。
- 项目保存/加载和 CSV 导出。
- 测量记录含来源倍率、单位、像素长度和物理长度。

### 界面

- Material You 风格：暖中性页面表面、白色/深色卡片、绿色主操作色。
- 60-30-10：约 60% 页面表面、30% 卡片表面、10% 主色操作与选中态。
- 主工作站使用左侧预览卡片和右侧可滚动工具卡片。
- 字号固定为 12/14/18px；间距使用 4/8/12/16/24 步进。
- 跟随系统浅色/深色模式，按钮、输入框、滑块、勾选框均有统一状态。
- 相机区域在窄窗口下分为两行，右侧工具区独立滚动。
- 主界面、状态栏、文件对话框和 AI 预览使用中文文案；驱动名和格式名保留技术原文。
- 单位支持毫米、厘米、微米、英寸和像素；微米在界面显示为“微米”，文件和 CSV 使用稳定的 `um`。
- 截图上的微米比例尺使用 OpenCV 可渲染的 `um`，避免 `μm` 在无 Unicode 字体时变成方框。
- 修改单位会使旧标定失效，并显示“未标定 · 请重新标定”，避免比例尺沿用旧单位。
- 比例尺长度输入框显示当前单位；勾选比例尺时采用界面中的固定长度，不再回退到自动长度。

### AI 截图

- `SubjectExtractor` 是可替换边界；`RemBgExtractor` 负责 BiRefNet 推理。
- 点击 AI 截图时立即冻结当前显示帧。
- 模型加载和推理在后台 `QThread` 中执行，不阻塞 Qt UI。
- 掩膜清理会删除小连通域并填补主体内部孔洞。
- 预览显示原图、掩膜和白底净图。
- 可保存原图或净图；原图永远不会被 AI 结果覆盖。
- 模型缺失、运行时缺失或推理异常时自动回退到原图，并禁用净图保存。
- AI 权重不随安装包分发，也不会在运行时自动下载。

## 3. 本地 0.3.0 构建物

目录：

```text
release/0.3.0/windows-x64
```

| 文件 | 大小 | SHA-256 |
| --- | ---: | --- |
| `OpenVisionMeasure.exe` | 205,290,147 bytes | `bd7574afd3f1ab7a22a9064ae55124cf7581f109eee06533c8aaf1ab0a13578b` |
| `OpenVisionMeasure-0.3.0-win64.zip` | 204,047,612 bytes | `29173bd15220b8780dc3f2caca09591040f807b3a56ff28a15f920c0753c4f9b` |

Python 包：

```text
dist\open_vision_measure-0.3.0-py3-none-any.whl
dist\open_vision_measure-0.3.0.tar.gz
```

EXE 没有 Authenticode 数字签名，Windows SmartScreen 可能显示未知发布者。

AI 版 EXE 已通过三种 smoke：

1. Qt/主窗口 smoke。
2. rembg + ONNX Runtime 导入 smoke。
3. 打包后真实加载本机 BiRefNet 权重并推理 64×64 图像。

尚未推送到远程，尚未创建 GitHub `v0.3.0` Release。推送和发布必须得到用户明确批准。

## 4. AI 模型边界

本机权重：

```text
%USERPROFILE%\.rembg\models\birefnet-general\birefnet-general.onnx
```

- 模型：`birefnet-general`
- 大小：972,666,916 bytes
- SHA-256：`58f621f00f5d756097615970a88a791584600dcf7c45b18a0a6267535a1ebd3c`
- rembg 来源 MD5：`7a35a0141cbbc80de11d9c9a28f52697`

代码仓库许可证不能自动代表 ONNX 权重许可证。权重来源、版本和自身许可尚未完成
法律核实，因此当前不打包、不公开分发权重。

安装 AI 开发依赖：

```powershell
uv sync --extra dev --extra ai
```

## 5. AI 实测

机器：AMD Ryzen 9 9950X，16 核 / 32 线程，93.5 GiB RAM。

样本：合成的 1024×1024 椭圆，仅用于工程成本验证，不证明植物组织切片质量。

| 指标 | 结果 |
| --- | ---: |
| 权重缓存后 session 加载 | 4.94 s |
| 5 次推理 p50 | 6.07 s |
| 5 次推理 p95 | 6.31 s |
| 进程峰值私有内存 | 约 19.7 GB |
| DirectML | 当前运行时不可用 |

详细记录见 `docs/ai-spike-2026-11-05.md`。

结论：

- CPU 推理不能在 UI 线程运行。
- AI 版本内存开销很高，必须在独立 worker 中运行。
- 当前权重和模型推理速度适合继续验证，但还不能据此宣称实时或低内存。

## 6. 真实相机验证

本次实际执行：

```text
后端：DirectShow
设备：Camera 0 (dshow)
模式：1280×720，YUY2
发现耗时：1.03 s
打开耗时：13.95 s
首帧耗时：0.10 s
```

这意味着相机链路可用，但该次打开耗时明显偏长。需要继续判断是否为驱动、设备枚举
或首次打开冷启动导致。

尚未完成：

- 用打包后的 EXE 连接真实相机。
- 60 秒连续预览和内存稳定性。
- 在真实电子目镜上切换倍率、标定、测量并带固定标尺截图。

## 7. 当前测试门禁

本次实际执行：

```text
ruff: passed
mypy strict: passed, 32 source files
pytest: 84 passed
wheel/sdist: passed
PyInstaller EXE: passed
packaged basic smoke: passed
packaged AI import smoke: passed
packaged AI model inference smoke: passed
```

测试门禁命令：

```powershell
uv run ruff check .
uv run mypy src
$env:QT_QPA_PLATFORM = "offscreen"
uv run pytest
uv build
```

## 8. 代码结构

```text
src/vision_measure/
  camera/                相机发现、打开、后台取帧
  inspection/            纯计算：标定、测量、标尺、图像处理
  workspace/             状态机、项目持久化、截图、CSV、AI 截图管线
  subject_extraction/    可替换分割边界、rembg 实现、掩膜清理、合成
  ui/                    Qt 装配、面板、视口、后台 AI worker
```

关键文件：

- `workspace/controller.py`：倍率、标定、AI 截图和保存管线。
- `subject_extraction/rembg_extractor.py`：BiRefNet 适配器。
- `subject_extraction/mask.py`：连通域清理和孔洞填充。
- `subject_extraction/composite.py`：白底合成。
- `ui/microscope.py`：倍率/标定/标尺 UI 协调。
- `ui/ai_capture.py`：AI 后台线程、预览对话框和截图控制器。
- `ui/main_window.py`：只做装配，当前 377 行。

## 9. 尚未完成

### 产品功能

- 区域面积和周长。
- 数量统计。
- 平均值、标准差、最小值和最大值汇总。
- 记录模块、Excel 报告、录像。
- 自动倍率识别和组织结构自动识别不在首版范围。

### 真实质量验收

- 至少 20 张真实植物组织切片，覆盖不同染色、倍率、气泡和杂质。
- 原图、掩膜和净图的人工质量评估。
- 组织主体内部气泡或杂质目前不能保证被 AI 删除，只能通过背景替换处理主体外
  杂质。

### 发布

- 权重自身许可和再分发条款核实。
- 真实电子目镜 + 真实切片完整流程验收。
- 60 秒预览内存曲线。
- EXE 数字签名。
- 推送分支、合并 `main`、创建 GitHub Release。

## 10. 构建命令

AI 运行时版本：

```powershell
pwsh -NoProfile -File scripts\build_windows.ps1 -Version 0.3.0 -WithAI
```

不含 AI 运行时的较小版本：

```powershell
pwsh -NoProfile -File scripts\build_windows.ps1 -Version 0.3.0
```

AI 版本会在构建后自动执行：

```text
--smoke-test
--ai-smoke-test
--ai-model-smoke-test
```

`--ai-model-smoke-test` 读取用户目录中的外部 BiRefNet 权重；如果权重不存在，构建
会失败。模型权重不进入 EXE。

## 11. 接手顺序

1. `git status` 和 `git log` 确认当前分支。
2. 阅读本文件、显微镜 spec 和 AI spike 文档。
3. 跑 Ruff、mypy 和离屏 pytest。
4. 用真实相机跑 60 秒预览并记录内存。
5. 用真实植物组织切片执行 20 张 AI 验收。
6. 核实权重许可后，决定是否在法律允许的范围分发模型。
7. 完成真实设备验收后，再请求用户批准推送和 Release。

已发布行为仍以 `v0.2.0` Release 二进制为准；`0.3.0` 目前是本机已验证构建，不是
公开版本。
