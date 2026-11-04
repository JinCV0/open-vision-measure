# Open Vision Measure 交接文档

更新时间：2026-11-05

## 1. 项目概况

- 产品名：Open Vision Measure
- 仓库：<https://github.com/JinCV0/open-vision-measure>
- 当前版本：`0.2.0`
- 当前分支：`main`
- `v0.2.0` 代码基线：`7c10c03`
- 许可证：Apache-2.0
- 技术栈：Python 3.12、PySide6、OpenCV、NumPy、PyInstaller
- 目标平台：Windows x64

项目最初实现为通用相机预览与图像测量工具，是独立实现，不包含
JCameraPro 的代码、资源或模型。下一阶段产品定位已调整为：

> 面向显微镜电子目镜的植物组织切片观察、测量、截图和科研记录工具。

交接时先区分两套状态：

| 范围 | 状态 | 依据 |
| --- | --- | --- |
| `v0.2.0` | 已发布、可运行 | Release 二进制、`7c10c03` 和现有测试 |
| 显微镜工作流 | 需求已确认，尚未实现 | 本文件第 2、7 节 |
| AI 主体提取 | 方案和模型已选定，尚未实现 | 本文件第 2 节 |

本次定位调整和 AI 功能仍处于设计阶段，尚未进入 `0.2.0` 发布代码。接手开发者
不得把本文件中的目标行为误报为现有功能。

## 2. 新阶段产品定义（设计阶段）

### 决策状态

已确认：

- 目标场景是显微镜电子目镜下的植物组织切片。
- 物镜倍率由用户手动切换，不做自动倍率识别。
- 每个倍率独立保存像素/物理单位标定，切换倍率时切换对应标定。
- 标尺使用用户指定的固定物理长度，并可在画布上拖动。
- AI 主体提取使用 `rembg` 和 `birefnet-general`。

待批准或待验证：

- 新标定交互的最终控件布局和文案。
- 未标定倍率下是否禁止物理测量、只允许像素测量，或允许临时测量后再补标定。
- 首版最终开放哪些 AI 截图输出模式。
- AI 使用独立进程、线程还是一个可选的本地服务。
- 模型权重如何随安装包分发，以及 CPU 与 DirectML 的默认选择。

### 目标用户与场景

- 使用显微镜电子目镜观察植物组织切片的研究人员、教师和学生。
- 日常操作包括切换物镜倍率、查看染色切片、判断组织层结构、测量细胞或导管、
  截图并制作论文或教学材料。
- 首版聚焦明场透射照明的植物组织切片，不预设荧光、偏光、共聚焦或自动扫描台
  能力。

### 必须覆盖的显微镜工作流

1. 连接电子目镜并自动选择最佳相机模式。
2. 用户手动选择当前物镜倍率，例如 `4x`、`10x`、`40x`、`100x`。
3. 每个倍率拥有独立标定配置；切换倍率后自动切换对应的像素/物理单位映射。
4. 在画布上完成参考物两点标定，并显示当前倍率、单位和比例尺。
5. 观察、截图、测量和导出，原图始终保留。
6. 可选启用 AI 主体提取与截图美化。

### 倍率与标定模型

推荐将倍率作为显式配置，而不是自动猜测：

- 倍率名称由用户维护，不强制只能是 4x/10x/40x/100x。
- 每个倍率保存：
  - 名称
  - pixels-per-unit
  - 物理单位
  - 最近一次标定时间
  - 标定参考长度
- 切换倍率只改变当前标定上下文，不修改历史测量记录。
- 相机分辨率或像素格式发生变化后，应提示重新标定当前倍率。
- 自动倍率识别不在首版范围；电子目镜通常不提供可靠物镜元数据。

### 植物组织切片优先测量

以下是建议的首版覆盖范围，除已有的两点距离外均未实现：

- 组织层厚度
- 任意两点距离
- 区域面积和周长
- 导管、细胞或空腔直径
- 数量统计
- 平均值、标准差、最小值和最大值
- 带比例尺和倍率信息的截图

细胞自动计数、自动识别组织层和切片分类暂不作为首版必选能力。

### AI 截图辅助设计

已选定主体分割引擎：

- `rembg`
- `birefnet-general`

许可证状态（2026-11-05 查询）：

- `danielgatis/rembg` 代码仓库：MIT
- `ZhengPeng7/BiRefNet` 代码仓库：MIT
- 实际打包进发行版的 ONNX 权重仍需记录下载地址、版本、SHA-256 和权重自身许可；
  不能只以代码仓库许可证代替权重许可。

AI 截图不是简单的“去掉背景”，建议拆成以下流水线：

1. 冻结原始帧，并保留不可变原图。
2. 使用 `rembg + birefnet-general` 生成主体 alpha 掩膜。
3. 对掩膜做形态学清理：
   - 删除远离主体的微小连通域
   - 修补主体内部的小孔
   - 对体积较大的组织碎片保留并提示用户人工确认
4. 背景中的悬浮杂质和气泡通过背景替换从最终图中消失。
5. 覆盖在组织主体内部的气泡或杂质不能依靠 alpha 掩膜删除，需要图像修复或人工
   修正；首版不得自动宣称已准确移除这类目标。
6. 在保存前显示原图、AI 掩膜和合成结果，允许关闭 AI 并导出原图。
7. AI 失败、模型缺失或显存不足时，必须回退到普通截图流程。

推荐提供四种截图输出模式：

- 原图
- 透明背景 PNG
- 白底净图
- 暗化背景、突出主体

当前尚未确定首版最终提供哪些模式，也尚未确认 `rembg` 是在应用进程内本地运行，
还是通过独立本地服务运行。推荐使用本地 ONNX Runtime/独立 worker，保持离线并
避免阻塞 UI；在锁定具体运行时前必须验证 `birefnet-general` 的模型大小、CPU 延迟
和 DirectML 兼容性。

首版建议使用预训练模型，不训练自定义模型。正式实现前应收集至少 20 张植物组织
切片代表性图片，覆盖不同染色、倍率、气泡和杂质情况，用于验证掩膜质量。

## 3. 当前发布物

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

## 4. 已实现功能

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

## 5. 代码结构

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

当前 `ui/main_window.py` 约 388 行，已接近 400 行拆分阈值。显微镜倍率、标定交互、
AI 截图等新功能不得继续堆入该文件；应新增模块，并让 `main_window.py` 继续只承担
装配和事件连接。

### 下一阶段建议模块落点（待用户批准）

1. `inspection`：新增倍率配置、当前倍率对应标定、固定物理长度标尺和 AI 掩膜后处理
   所需的无 Qt 数据结构与纯计算。对外只暴露不可变配置、换算和渲染几何结果。
2. `workspace`：负责切换当前倍率、检测相机配置变化、触发重新标定、组织截图流水线，
   以及把多倍率标定写入项目文件和用户偏好。模型加载、推理和图像算法不放在这里。
3. `ui`：新增独立的倍率/标定控件和截图预览控件，只负责输入、展示和事件转发。
4. 新增独立的 `subject_extraction` 边界：定义 `SubjectExtractor` 接口，用
   `rembg + birefnet-general` 实现。建议首版运行在受控独立 worker 中，使模型缺失、
   推理失败或进程异常不会拖死 UI。

建议的领域接口如下，名称和字段仍需在实现前定稿：

```python
@dataclass(frozen=True)
class MagnificationProfile:
    name: str
    calibration: Calibration | None
    scale_bar_length: float | None

class SubjectExtractor(Protocol):
    def extract(self, image: np.ndarray) -> np.ndarray: ...
```

项目 JSON 需要保留现有 `schema_version=1` 的读取能力。升级到多倍率模型时，应使用
显式 schema 迁移；旧项目中的单个 `calibration` 不能静默套用到所有倍率。

## 6. 当前测试与验证

本次交接文档更新时实际执行：

```text
Ruff: passed
mypy: passed
38 passed
```

`v0.2.0` 发布时另已通过：

```text
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

## 7. 尚未实现的需求

### 标定与标尺

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

固定物理长度标尺的统一口径：

- 用户输入或选择实际长度，例如 `10 mm`。
- 当前倍率已有标定时，按 `calibration.unit_to_pixels()` 计算绘制长度。
- 画布预览和截图必须使用同一几何函数；不得各自实现另一套换算。
- 标尺默认左下角，拖动位置继续以归一化图像坐标保存。
- 若固定长度超出当前画布或图像可用范围，应明确拒绝或要求用户修改长度，不能静默
  换成另一个“好看”的长度。

### 多倍率工作流

尚未实现：

- 倍率选择控件及用户可维护的倍率清单。
- 每个倍率独立的 `pixels-per-unit`、单位、参考长度和标定时间。
- 切换倍率后的标定切换，以及未标定倍率的明确状态。
- 相机分辨率或像素格式变化后的重新标定提示。
- 测量记录保存其来源倍率，避免之后切换倍率导致历史数值含义不清。

### 植物组织切片测量

现有版本只有两点线段测量。组织层厚度可使用现有线段工具；区域面积/周长、导管或
细胞直径、数量统计和统计值汇总仍需要新的几何工具与数据模型。

### AI 截图

尚未实现任何 `rembg`、ONNX Runtime、模型下载、主体掩膜、背景替换或 AI 截图 UI。
现有截图始终直接保存当前处理后的画面，不经过主体分割。

## 8. 已知风险和技术债

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
7. `rembg` 和 `birefnet-general` 会显著增加安装包体积、冷启动时间和内存占用。
   必须分别测量模型文件大小、首次加载时间、CPU/DirectML 延迟和峰值私有内存。
8. `rembg` 或 BiRefNet 仓库采用 MIT，不代表任意 ONNX 权重都自动满足相同条件。
   发布前必须锁定权重来源、版本、SHA-256 和权重自身许可，更新
   `THIRD_PARTY_NOTICES.md`，不得运行时静默下载未经验证的模型。
9. AI 分割只能可靠去除 alpha 掩膜之外的背景。组织主体内部的气泡、杂质和染色
   断层仍会保留，首版不能宣传为“自动移除所有气泡和杂质”。
10. PyInstaller 下的多进程 worker、ONNX Runtime 和 Qt 插件可能发生 DLL 或启动
    问题。AI 版本必须继续执行打包后的 smoke test，并验证实际模型推理，不只验证源码
    环境。
11. 多倍率项目格式涉及历史数据。升级 schema 前必须增加旧项目加载测试，避免把旧的
    单一标定错误应用到其他倍率。

## 9. `0.3.0` 验收标准

### 显微镜核心流程

- 能打开电子目镜，并在实际设备上记录后端、分辨率、像素格式和启动耗时。
- 用户可手动切换至少 `4x`、`10x`、`40x`、`100x` 四个倍率，名称可配置。
- 每个倍率独立标定；切换倍率后，测量值和标尺立即使用对应倍率的数据。
- 切换倍率不会改写历史测量记录所属的倍率和单位。
- 相机分辨率或像素格式变化后，旧标定不会被静默沿用。
- 新标定流程只依赖当前两次画布点击，不要求用户理解“最后一条线”。
- 固定物理长度标尺在实时画布和截图中的长度、位置、字体和线宽一致。
- 项目保存、重开和旧版 schema 1 项目加载均有自动化测试。
- 截图继续保留上次目录、扩展名和顺延编号，并覆盖中文路径。

### AI 截图

- 原图始终可保存，任何 AI 结果都不得覆盖唯一原图。
- 用户能在保存前查看原图、掩膜和合成结果。
- 背景中的悬浮杂质和气泡应通过背景替换消失。
- 组织主体内部的气泡或杂质不被虚假宣称已自动去除。
- 模型缺失、推理超时、显存不足或 worker 异常时，普通截图仍能完成。
- 发布包离线可运行，不依赖首次启动时联网下载未锁定模型。
- 至少用 20 张真实植物组织切片验收，覆盖不同染色、倍率、气泡和杂质条件。
- 在目标机器记录 CPU 与可用 DirectML 路径的冷/热启动时间、p50/p95 推理时间和
  峰值私有内存；没有测量过的数据不得写成性能结论。

### 真实验收边界

合成相机、模拟分割器和单元测试不能证明电子目镜、驱动、真实切片或 ONNX 模型可用。
发布说明必须分别写明已执行的自动化测试、实际硬件验证和仍未执行的验证。

## 10. 开发命令

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

## 11. 发布流程

1. 更新 `pyproject.toml`、`src/vision_measure/__init__.py`、
   `packaging/windows-version-info.txt` 和 `THIRD_PARTY_NOTICES.md` 中的版本。
2. 运行全部测试、Ruff、mypy 和 `uv build`。
3. 运行 `scripts/build_windows.ps1`。
4. 在真实相机上验包。
5. AI 版本额外记录模型包路径、文件大小、SHA-256、权重来源和许可。
6. 提交并推送 `main`。
7. 创建 GitHub Release，上传 EXE、ZIP、模型相关发布物和校验文件。

## 12. 建议实施顺序

1. 为新阶段编写独立 spec 和 implementation plan，确认第 2、5、7 节中的待定决策。
2. 建立倍率配置和 schema 迁移，先保证旧项目可读，不接 UI。
3. 实现“输入物理长度 -> 两次画布点击 -> 完成标定”的状态机和自动化测试。
4. 实现固定物理长度标尺，确保实时预览与截图共用几何结果。
5. 完成相机配置变化失效、历史测量保留倍率信息和真实显微镜验收。
6. 记录 Best 模式真实分辨率/像素格式、启动耗时和 60 秒预览内存曲线。
7. 用独立脚本完成 `rembg + birefnet-general` spike，测量模型和推理成本，再决定 worker
   方案。
8. 接入 AI 掩膜、微连通域清理、小孔修补、预览确认和普通截图回退。
9. 完成至少 20 张真实切片验收并发布 `0.3.0`。

在第 1 步得到批准前，不应直接开始第 2 步及后续代码实现。

## 13. 接手检查清单

1. 执行 `git status`，确认是否有未提交的设计或本地发布物。
2. 阅读本文件、`docs/superpowers/specs/` 和 `docs/superpowers/plans/` 中的现有文档。
3. 运行 Ruff、mypy 和离屏 pytest，确认当前源码基线。
4. 检查电子目镜是否被其他进程占用，尤其是 Codex 随行的 `capture_agent.py`。
5. 先确认标定交互、模块落点和 AI 首版范围，再按新 spec 写代码。
6. 任何功能完成都要区分“自动化测试通过”和“真实显微镜/真实切片通过”。

交接时若上下文丢失，以本文件、`docs/superpowers/specs/` 和 `docs/superpowers/plans/`
中的文档为准；已发布行为以 `v0.2.0` Release 二进制和对应 Git 提交为准。
