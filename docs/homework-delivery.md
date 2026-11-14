# 整套作业交付工具

本地工具 `cad-job` 管理1～20张已经绘制并核对的A3横向DXF：检查原生尺寸、生成逐页及合并PDF、渲染预览，再打包。输入只读，不会改源图、自动缩放或代改尺寸。

目前这是Python本地工具，可供本地Agent调用；**尚未接入GitHub Pages网页**。没有新增服务器，不上传图纸，不使用模型Key。此工具也不等于照片自动完成整套作业。

## 调用

安装仓库后使用 `cad-job`，或以 `python -m cad_print_workflow.delivery` 替代。

```bash
cad-job inventory sheet2.dxf
cad-job check job.json
cad-job build job.json -o delivery --font /path/to/font.ttf
# 逐页打开PNG和PDF检查文字、线条、图框、裁切之后：
cad-job package delivery --confirm-visual
```

构建需要Poppler的 `pdftoppm`，转换复用项目现有字体与DXF兼容性检查。输出目录必须尚不存在。打包前校验所有文件的SHA-256，构建后修改文件应重新构建、重新审核；这用于发现误改，不是防篡改签名。

## 作业清单

清单与DXF放在同一目录，source可指向该目录内的子目录，不能指向外部路径。编号用于输出文件名。

```json
{
  "version": 1,
  "sheets": [
    {
      "id": "sheet2",
      "title": "几何作图",
      "source": "sheet2.dxf",
      "geometry_reviewed": true,
      "dimensions": [
        {
          "handle": "D1",
          "expected": 55,
          "drawing_scale": 3,
          "tolerance": 0.01,
          "source": "教材：水坝实际总长55，作业要求绘图3:1"
        }
      ]
    }
  ]
}
```

句柄从inventory获得，示例D1不是任意图纸通用编号。每个可打印的原生尺寸必须列入清单；几何审阅字段应在核对题意和图形后设置。不要把文件中测出的当前值直接当作expected，否则会让错误自证正确。

同一张图中可以混用比例：水坝尺寸drawing_scale=3，吊钩和五角星=1。检查三件事：DIMLFAC应等于1/绘图比例，几何测量乘换算因子应等于预期实际尺寸，缓存显示文字也应等于预期。固定文字覆盖、未核查的原生尺寸、没有显示缓存、超出A3、不支持图元均阻断交付。

支持线性、对齐、半径和直径尺寸。角度/公差/多行复杂标注目前不自动放行；无原生DIMENSION时明确提示人工核对，不能识别已炸开的标注数字，也不能证明尺寸定义点关联到了正确轮廓。标题栏姓名和班级不自动替换，需先在图纸中核对。

## 输出与状态

- 每张图的DXF副本、PDF、PNG预览、转换报告。
- A3-all.pdf：合并打印稿，420×297毫米，100%打印。
- audit.json：每个尺寸的结果、源文件指纹和未覆盖范围。
- delivery.json：待视觉审核状态及文件指纹。
- delivery.zip：显式视觉确认后生成，包含review.json确认记录，不含API Key。

先检查所有图纸，再在临时目录构建；某张失败不会留下貌似完成的交付目录。打包不会清除源文件或覆盖旧交付包。

## 实测

2026-11-14用此前两张作业运行了完整链：第二张21个原生尺寸通过，第一张无原生尺寸按人工审核提示处理；逐页检查预览后完成打包。私人原图、清单与输出不提交仓库。新增合成回归覆盖3:1误标、固定文字掩盖、陈旧缓存、遗漏检查、目录越界、原件不变、多页输出与修改后阻断。
