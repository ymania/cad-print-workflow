# 图片 → 网页助手 → FreeCAD

## 本机网页启动

安装 Python 3.10+ 和依赖，然后启动：

```bash
python -m pip install -e '.[web]'
cad-assistant
```

浏览器打开 http://127.0.0.1:8765 。界面沿用数据质量 Agent 的“配置 / 对话与执行 / 结果工作台”组织方式，后端为 FastAPI。没有账号系统，仅绑定本机回环地址；不要通过反向代理直接公开到公网。

1. 点击“模型配置”，填写支持图片的 Chat Completions 兼容服务地址（一般以 `/v1` 结尾）、模型名与密钥。密钥仅存在进程内，接口不回显，重启后重新配置。
2. 上传图片，输入要求。图片将发送给所配置的服务；任务在后台执行，页面轮询真实状态。
3. 查看构件、尺寸来源和待确认项。继续对话可以结合原始图片和上一版结构重新识别。它是有固定工具流程的图纸助手，不是任意执行代码的通用 Agent。
4. 核对完整几何数据。尺寸证据列表是说明，不会驱动几何自动求解；修订须同步更新 entities，或要求模型重新计算并复核。清除已解决的 unresolved 后勾选确认。
5. 生成并下载 DXF、A3 PDF、检查报告、FreeCAD 宏；配置 FreeCAD 命令行后同时生成 FCStd。安装 Poppler 时可显示 PNG 预览。

无密钥也能点“试用内置示例”，走完核对、生成、下载流程。它明确是合成示例，不代表识图成功。

任务文件默认保存到 `~/.local/share/cad-print-workflow`，可通过 `CAD_DATA_DIR` 修改。服务重启后页面任务索引和对话不恢复，但文件仍保留在任务目录；需长期记录时自行备份。每次修订和构建使用独立目录，不覆盖源文件。

## FreeCAD 连接

安装 FreeCAD 并设置命令行程序路径后启动网页：

```bash
export CAD_FREECAD_CMD=/path/to/FreeCADCmd
cad-assistant
```

Linux AppImage 可以使用一个本机启动脚本作为 `CAD_FREECAD_CMD`，调用解包目录的 `AppRun freecadcmd "$@"`。路径依安装位置而异，不应把个人绝对路径写入公共项目。

未配置时下载 `build.FCMacro`，在 FreeCAD 的“宏”菜单执行。它在宏旁边生成 `model.FCStd`；已有同名文件时拒绝覆盖。每个构件建立一个原生 Sketcher 草图，中心线作为构造几何，尺寸来源放在 DimensionEvidence 属性中。

当前是二维、原尺寸、未约束的可编辑草图：没有自动推导厚度、拉伸成实体、驱动尺寸约束或 TechDraw 标注。没有通用相切约束求解器；模型推导的坐标必须核对。PDF 为 A3 1:1，不自动排版/缩放，超界报错。后续在 FreeCAD 中修改草图不会自动刷新此前导出的 DXF/PDF。

## 命令行调用

模型接口通过环境变量配置，也可由网页内存配置：

```bash
export CAD_VISION_BASE_URL=https://your-provider.example/v1
export CAD_VISION_MODEL=your-vision-model
# 使用本机密钥管理器或私密终端设置 CAD_VISION_API_KEY，勿提交到 Git
cad-model extract photo.jpg -o draft.json --instruction '提取构件和实际毫米尺寸；不确定项单独列出'
# 人工核对/修订 draft.json，解决 unresolved 并设置 reviewed=true
cad-model build draft.json -o result/my-drawing --preview --freecad /path/to/FreeCADCmd
```

接口发送图片和文字到 `/chat/completions`，要求 JSON；只解析受支持图元，不执行模型返回的代码。extract 强制写入 reviewed=false，不允许模型自行通过复核。格式参见 `examples/reviewed_geometry.json`。支持 line/circle/arc；坐标毫米，圆弧逆时针，角度范围 [0,360)，允许跨0°。

## 验证与边界

测试包括审核阻断、非法尺寸、DXF实体尺寸、输入不变、模拟模型响应、网页下载与密钥不回显。FreeCAD 1.1.4 本机实测：生成并重开 FCStd，核对四个几何对象、R40、150°跨0°圆弧与构造中心线。真实视觉模型准确率未验证：需用户配置自己的服务；模拟测试不等于真实模型识图验收。

依据：[FreeCAD 官方脚本文档](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Python_scripting_tutorial.md)、[ezdxf 图元文档](https://ezdxf.readthedocs.io/en/stable/dxfentities/index.html)。
