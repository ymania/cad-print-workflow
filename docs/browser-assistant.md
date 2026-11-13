# 纯前端 CAD 助手

`frontend/` 是独立静态网站，只有 HTML、CSS、JavaScript，不依赖 Python 服务、数据库、npm 包或远程 CDN 脚本。旧的 Python CLI / 本机 FastAPI 助手仍保留，不能把它们与本版的密钥存储行为混淆。

## 使用

1. 打开网站，先“试用内置示例”。不填密钥也能预览和下载文件。
2. 识图时，在模型配置里填支持图片的 Chat Completions 基础地址、模型名和自己的 API Key。服务必须允许浏览器 CORS 请求（包括 Authorization、Content-Type 的预检）。本站不使用中转；不能保证所有“兼容API”都可直连。
3. 选择PNG、JPEG或WebP图片，填写要求，核对页面显示的接收接口，再勾选发送许可。模型只返回结构化JSON；代码不会执行模型返回的脚本。
4. 检查构件、尺寸来源、unresolved 和几何预览。可以继续对话修订，或打开完整参数编辑器手动修改并校验。参数证据不自动求解几何，不应只改显示尺寸。
5. 确认后在浏览器本地生成 DXF、PDF、SVG、FreeCAD宏、JSON参数和检查报告。刷新前下载参数；以后用“导入参数”继续，重新审核。

## 导出区别

| 文件 | 含义 |
|---|---|
| drawing.dxf | DXF R2000 / AC1015，毫米单位，基础LINE/CIRCLE/ARC，按用途分层，适合LibreCAD编辑 |
| drawing.pdf | 一页A3横向矢量PDF，420×297mm，打印使用实际大小100% |
| drawing.svg | 同尺寸矢量预览 |
| build.FCMacro | 在本机FreeCAD中执行，旁边生成model.FCStd；已有同名文件时拒绝覆盖 |
| reviewed.json | 已确认的输入参数，不含模型密钥 |
| report.json | 页面、比例与限制报告 |

`entities` 中坐标与半径表示实际毫米。每个构件可设置 `scale` 和 `offset:[x,y]` 调整纸面排版，DXF/PDF/SVG应用该变换，FreeCAD宏保留实际几何。水坝实际55mm、scale=3时纸上长165mm，原始参数仍是55。当前不自动输出尺寸文字或原生DIMENSION，需在LibreCAD中添加；不能把165当成实际标注55而不设置相应尺寸比例。

支持用途层 outline（0.50mm）、thin/center/dashed/hatch/dimension（0.18mm）。hatch只接受明确的斜线段，非填充HATCH。FreeCAD中心线用构造几何，其余为普通草图几何；草图尚未完全约束，不生成三维实体。LibreCAD可能按内置线型名称调整节距，最终打印可优先使用本页生成的PDF。

本版没有通用几何约束求解器：结构和边界检查不能证明相切、尺寸解释或模型推导正确。不支持的图元报错，不静默丢弃。PDF曲线采用每段不大于90°的三次贝塞尔圆弧近似（标准圆近似最大径向误差约半径的0.0273%）；DXF和FreeCAD保留真实圆/圆弧。重要加工尺寸以CAD几何为准。

## 数据与密钥

- API Key只在页面内存里使用，不写入localStorage/sessionStorage、Cookie、日志、URL、导出文件或后端。关闭配置框时清空密码输入框；刷新页面、忘记密钥、清空会话后不能继续使用原密钥。
- 配置本身不会触发模型请求。识图需要显式点击并勾选接收地址确认。图像与要求会离开电脑，直接交给选定的模型服务商，遵循其数据政策。
- HTTPS直连，禁止带账号/查询参数的接口地址，不携带浏览器Cookie、不发送Referer、不跟随HTTP重定向。请求取消/超时不保证服务商停止处理或免除费用。
- 无统计脚本或外部脚本依赖；页面设置CSP，模型文本通过textContent展示，图形只从验证过的数字生成。静态托管商仍可能记录网页访问IP等访问日志。
- 这不是绝对保密保证：运行中的页面代码能读取用户输入的密钥，恶意扩展、设备入侵、源码或托管被篡改仍构成风险。建议独立限额密钥、自托管审核过的源码。切勿把站长的密钥内置到源码。

## 自托管与域名

把整个 `frontend/` 文件夹上传到任意支持HTTPS的静态托管平台即可。所有资源为相对路径，可部署到子目录，无需构建。仓库提供 `.github/workflows/pages.yml`，使用 GitHub Pages Actions 发布，仅上传 frontend/，不上传本地文件、测试结果或Python后端。

本地查看可运行：

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory frontend
```

然后打开 http://127.0.0.1:8766 。这里只启动静态文件预览器，不处理用户图片或密钥，也不承担CAD计算。直接打开 index.html 可用本地示例和导出，但 file:// Origin 可能被模型接口拒绝；线上使用HTTPS。

使用你自己的域名时，以托管平台返回的记录为准。GitHub Pages 子域名示例：先在仓库Pages设置配置 `cad.jackmen.asia`，再把阿里云DNS的 `cad` CNAME 指向 `ymania.github.io`（不是带路径的网址），等待DNS与证书就绪后启用HTTPS。不要仅配置DNS而漏掉平台端自定义域名。当前是否已绑定以平台实际配置为准，本项目不自动修改你的域名。

参考：[GitHub Pages发布](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)、[自定义域名](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)、[LibreCAD线属性](https://docs.librecad.org/en/latest/appx/lines.html)。

## 验证

```bash
node --test tests/browser/*.test.cjs
python -m pip install -e '.[dev]'
pytest -q
```

浏览器侧测试：结构审核阻断、页界、绘图比例、DXF线型、字符串安全、接口请求结构及失败处理。Python测试独立读取浏览器导出的DXF与PDF。已用本机LibreCAD 2.2.1.5读取示例DXF并打印，FreeCAD 1.1.4执行宏并重开核对实际圆半径及构造线。真实视觉模型质量与具体服务的浏览器CORS尚需用户配置后验证，模拟接口测试不代表真实模型已验收。
