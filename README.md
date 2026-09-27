# ddddocr OCR API · 阿里云函数计算（FC）部署包

把 `https://api.nn.ci/ocr/b64/text` 平替成你自己的**免运维、按量付费、国内直连**的在线验证码识别接口。
代码基于 FastAPI，监听 `0.0.0.0:9000`（FC 自定义运行时默认端口）。

## 目录内容

| 文件 | 作用 |
|------|------|
| `app.py` | FastAPI 服务，核心接口 `POST /ocr/b64/text`（与 nn.ci 同路径、同返回） |
| `requirements.txt` | 依赖：fastapi / uvicorn / ddddocr |
| `bootstrap` | FC 自定义运行时启动脚本（不配置启动命令时的默认入口） |
| `Dockerfile` | 自定义容器镜像（依赖太大时的稳妥方案） |
| `README.md` | 本文件 |

> 调用方式与你原来完全一致：把 `https://api.nn.ci/ocr/b64/text`
> 换成 `https://<你的FC域名>/ocr/b64/text`，数字验证码加 `?digits=1` 更准。

---

## 方案一（推荐）：Function AI / Web 函数，云端自动装依赖，免 Docker、免本机 pip

适合你这种场景：**不用在自己电脑装 onnxruntime**，FC 在云端构建时自动 `pip install`。
只需上传 `app.py` 和 `requirements.txt` 两个文件。

1. **开通函数计算**：登录 [阿里云函数计算控制台](https://fc.console.aliyun.com/) → 按提示开通（顺手领取「新用户试用额度」）。
2. **进入函数智能**：左侧导航栏点 **「函数智能」**（即原来的 Function AI，阿里云改了中文名）→ 选「项目」→ 新建项目（空白项目）→ 项目内「新建服务」→ 选 **Web 服务**。
3. **配置服务**（关键项）：
   - 运行环境 / 构建环境：都选 **Python**（两者一致）。
   - **构建命令**：`pip install -t . -r requirements.txt`（FC 在云端把依赖装到代码目录，**不用你本机装 onnxruntime**）。
   - **启动命令**：`python3 app.py`。
   - **监听端口**：`9000`。
   - 代码包路径 / 执行路径：根目录 `.`（即 `app.py`、`requirements.txt` 放在工程根）。
4. **上传代码**：把本目录里的 `app.py` 和 `requirements.txt` 上传；或「绑定 GitHub」连仓库 `PediyCCDebuger/ocr-api`（入口文件已在**仓库根目录**，直接连即可，不用进 `fc/` 子目录）。
5. **预览 & 部署**：点「预览&部署」→ 确认资源 → 部署。等待构建（约 2–5 分钟，要装 ddddocr + onnxruntime）。
6. **拿到地址**：部署完成后在「服务情况」拿到 API 公网地址（形如 `https://<随机>.cn-hangzhou.fcapp.run`）。
   - 若只想用 API、不在浏览器打开，直接用该**服务公网地址**即可，无需绑定自定义域名。
   - 若要在浏览器直接打开页面，可用平台临时测试域名（仅 HTTP）。

> ⚠️ **代码包体积提醒**：ddddocr 依赖（onnxruntime + opencv 等）解压后约 200–400MB。
> 请务必在**杭州地域（cn-hangzhou）**创建（代码包上限 500MB）；其他地域上限仅 100MB，会超限。
> 如果确实要用非杭州地域，请改用下方的「自定义容器」方案。

> ⚠️ **HTTP 触发器鉴权**：在触发器配置里把「认证方式」设为 **无需认证（anonymous）**，
> 这样你用 Python `requests.post` 调用时才不用做签名。若设为需认证，调用需带 FC 签名头。

---

## 方案二：自定义容器镜像（依赖太大 / 非杭州地域时最稳）

镜像上限 10GB，彻底绕开代码包体积限制，且自带完整运行环境。

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。
2. 在阿里云「容器镜像服务 ACR」创建**个人版实例**和一个仓库（如 `ocr-api`）。
3. 在本目录构建并推送镜像（需先 `docker login` 到你的 ACR  registry）：
   ```bash
   docker build -t registry.cn-hangzhou.aliyuncs.com/<命名空间>/ocr-api:latest .
   docker push registry.cn-hangzhou.aliyuncs.com/<命名空间>/ocr-api:latest
   ```
4. 函数计算控制台 → 创建函数 → 选 **Web 函数 / 自定义镜像** → 选上面推送的镜像，
   监听端口填 `9000`，HTTP 触发器认证方式选「无需认证」。

---

## 部署后验证

拿到地址后，用你原来调 nn.ci 的方式测试：

```python
import requests, base64

url = "https://<你的FC域名>/ocr/b64/text?digits=1"   # 数字验证码加 ?digits=1
b64 = base64.b64encode(open("code.png", "rb").read()).decode()
r = requests.post(url, json={"base64": b64}, timeout=30)
print(r.text)   # 识别出的数字
```

或浏览器打开 `https://<你的FC域名>/` 用网页表单手动传图测试。

---

## 计费与保活（重要）

- **按量付费，不用不花钱**：函数「最小实例数」保持默认 **0**，没有请求就不计费。
- **免费额度**：每月 100 万次调用 + 40 万 CU-秒算力免费；个人刷验证码量级基本 **≈0 元/月**。
- **冷启动**：空闲后实例回收，下次请求约 1–3 秒唤醒（首次含 ddddocr 模型加载稍慢），
  对脚本自动识别验证码完全可用。若要常驻，可在「弹性管理」把最小实例数调为 1（会产生常驻费用）。

---

## 常见问题

- **部署后调用 502 / FunctionNotStarted**：多半是没监听 `0.0.0.0:9000`。本包已用 `0.0.0.0` 和 `${PORT:-9000}`，正常不会。
- **代码包超限（100MB）**：换成杭州地域，或改用方案二（自定义容器）。
- **识别不准**：数字验证码务必加 `?digits=1`；若仍是彩色干扰线极强的图，可先用 PIL 做灰度/二值化再识别。
