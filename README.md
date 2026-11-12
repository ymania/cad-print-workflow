# CAD Print Workflow

把这次 LibreCAD 工程制图与缺线排查经验整理为可重复使用的工作流。提供 **DXF 检查 → 黑白矢量 PDF → 页面校验 → PNG 预览**，以及指导 Agent 建图、标注和验收的中文文档。

现在提供图片识别接口和本机网页助手，识图结果必须经核对后再建图。这不是完整 CAD 内核。主要服务于二维、毫米单位的模型空间工程线稿。遇到不支持的对象会报错，避免无声漏画。

## 网页助手与 FreeCAD

```bash
python -m pip install -e '.[web]'
cad-assistant
```

打开 http://127.0.0.1:8765 ，配置视觉模型，上传图片并对话提取构件，核对尺寸后生成 DXF、PDF 和 FreeCAD 草图。无密钥可先试内置示例。

[完整配置、命令行流程与 FreeCAD 连接说明](docs/image-to-freecad.md)。草图可编辑但未添加驱动尺寸约束；真实识图需配置支持图片的模型。

## 安装和直接调用

需要 Python 3.10+；预览需要 Poppler 的 `pdftoppm`。LibreCAD 是可选的查看/编辑工具，转换本身不依赖它。

```bash
git clone https://github.com/ymania/cad-print-workflow.git
cd cad-print-workflow
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
# Ubuntu / Debian，按需安装：
# sudo apt install poppler-utils fonts-dejavu-core

cad-print inspect /path/to/drawing.dxf
cad-print export /path/to/drawing.dxf -o result/drawing.pdf --preview
```

Windows 激活环境：`.venv\Scripts\activate`。私有仓库需先配置 GitHub 登录。命令不会覆盖已有结果，确需替换时加 `--force`。

输出 PDF、同名 `.report.json` 检查报告；加 `--preview` 时输出同名 PNG。默认 A3 横向 420×297 mm，世界坐标原点 (0,0)，**1 DXF 毫米 = 1 PDF 毫米**。不自动缩放。图纸超出页面时会报错，可调整排版或指定 `--origin X Y --width W --height H`。

文字默认使用系统 DejaVu Sans/Arial；可通过 `--font /path/to/font.ttf` 指定含所需字符的独立 TrueType 字体。缺失字符会报错。中文通常需要额外字体；TTC 字体集合、SHX 暂不支持。文字转成矢量轮廓，字形与原 CAD 字体可能不同，须检查。

## 三条使用路径

- **已有 DXF，需要打印**：运行 inspect/export，查看报告和 PNG，再按 A3、实际大小/100% 打印。
- **让 Agent 帮你制图**：让它先读 [Agent 工作流](docs/agent-workflow.md)，按参数表建图，再用本项目转换。
- **排查缺线/尺寸问题**：读 [排查说明](docs/troubleshooting.md)，先区分原文件缺对象、导出缺对象与显示太淡。

## 支持边界

支持 LINE、ARC、CIRCLE、二维无宽度 POLYLINE/LWPOLYLINE（含圆弧凸度）、SOLID、TEXT、常规 MTEXT，以及已有显示块的 DIMENSION。简单虚线按 DXF 线型与比例输出，保留实际分段线。圆、圆弧直接写入矢量 PDF；多段线曲线及文字轮廓采用 0.003 mm 展平容差。

模型空间 INSERT、HATCH、SPLINE、图片、复杂线型、三维、宽多段线等不在本版支持范围；先在 CAD 中显式转换为受支持图元并复查。DIMENSION 内部块引用由库展开。隐藏、冻结、不打印图层及不可见对象被跳过。不要将纸空间布局当成模型空间打印。

所有可打印对象输出黑色；保留粗细层级，线宽下限为0.13 mm。源文件只读；不修改元数据、不伪造历史。尺寸值沿用保存的显示块，**不会自动纠正错标尺寸**。

## 示例与测试

```bash
python examples/create_demo.py
cad-print export demo.dxf -o result/demo.pdf --preview
pytest -q
```

示例是合成测试图，不含个人作业、学校信息或聊天附件。测试检查纸张尺寸、细线实际渲染、输入不变、缺字/不支持对象/越界报错及尺寸比例。

在 Python 中调用：

```python
from cad_print_workflow.cli import convert
convert('drawing.dxf', 'result/drawing.pdf', preview=True)
```

验证并不等于工程签审。打印前仍需看预览、检查图形内容及尺寸含义。工程图放大3:1时，图上长165 mm应标实际55 mm；此规则由建图/标注阶段负责。
