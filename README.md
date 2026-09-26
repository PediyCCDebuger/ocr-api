---
title: ddddocr-api
sdk: docker
app_port: 8000
---

# ddddocr 在线 OCR API（nn.ci 平替）

纯 Python + FastAPI 封装 [ddddocr](https://github.com/sml2h3/ddddocr)，提供与
`https://api.nn.ci/ocr/b64/text` **完全一致**的接口，可免费部署到 Render / Hugging Face Spaces / 任意 Docker 平台。

## 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/ocr/b64/text` | **与 nn.ci 同路径**。请求体为 base64（纯文本 / `{"base64":..}` / `data:image/..;base64,..`），返回纯文本 |
| POST | `/ocr/file` | 上传文件（multipart），便于 curl / 网页测试 |
| GET  | `/` | 简易网页表单，可手动上传图片识别 |
| GET  | `/health` | 健康检查 |

- 可选参数 `?digits=1`：仅保留 `0-9`，数字验证码更准。
- 已开启 CORS（`*`），任何前端（含你的 Neocities 页面）都能直接 `fetch` 调用。

## 用法示例

```bash
# 1) base64 文本（和原来调 nn.ci 一样）
curl -X POST https://你的地址/ocr/b64/text \
  -H "Content-Type: text/plain" \
  -d "iVBORw0KGgoAAAANSUhEUgAA..."

# 2) JSON
curl -X POST https://你的地址/ocr/b64/text \
  -H "Content-Type: application/json" \
  -d '{"base64":"iVBORw0KGgoAAAANSUhEUgAA..."}'

# 3) 仅数字
curl -X POST "https://你的地址/ocr/b64/text?digits=1" -d "...."

# 4) 上传文件
curl -X POST https://你的地址/ocr/file -F "file=@captcha.png"
```

Python 调用（把你原来代码里的域名换掉即可）：

```python
import requests, base64
b64 = base64.b64encode(open("captcha.png", "rb").read()).decode()
r = requests.post("https://你的地址/ocr/b64/text?digits=1",
                  json={"base64": b64}, timeout=10)
print(r.text)
```

## 部署

### A. Render（最省事，免信用卡）

1. 把这个目录推到 GitHub 仓库。
2. 登录 https://render.com → New → Web Service → 关联仓库。
3. 环境选 **Python**（Render 会自动读 `requirements.txt`）。
4. Build Command：`pip install -r requirements.txt`
5. Start Command：`uvicorn app:app --host 0.0.0.0 --port $PORT`
   （也可直接放 `Procfile`，Render 会自动识别。）
6. 选 Free 套餐，Create。部署完拿到 `https://xxx.onrender.com`。

> 免费档 15 分钟无访问会休眠，首次唤醒约 30–60 秒。可用 cron-job.org / UptimeRobot 每 10 分钟 ping 一次 `https://xxx.onrender.com/` 保活。

### B. Hugging Face Spaces（资源更足，免信用卡）

1. 新建 Space，SDK 选 **Docker**。
2. 把本目录文件（含此 README 顶部的 YAML 元数据）推到 Space 仓库。
3. 平台按 `Dockerfile` 构建，监听 `app_port: 8000`。
4. 部署完地址：`https://你的用户名-空间名.hf.space`。

### C. 任意 Docker 平台

```bash
docker build -t ddddocr-api .
docker run -p 8000:8000 ddddocr-api
```
