# ddddocr OCR API · 阿里云函数计算（FC）部署包 & 完整留档

一份把 `https://api.nn.ci/ocr/b64/text` 平替成**你自己可控、免运维、按量付费、国内直连**的在线验证码识别接口的部署包。
代码基于 FastAPI + ddddocr，对外暴露与 nn.ci 完全一致的接口。

> 适用场景：自动识别视频网站搜索时弹出的**数字验证码**。调用方式与你原来完全一致——
> 把 `https://api.nn.ci/ocr/b64/text` 换成 `https://<你的地址>/ocr/b64/text`，数字验证码加 `?digits=1` 更准。

---

## 一、目录内容

| 文件 | 作用 |
|------|------|
| `app.py` | FastAPI 服务，核心接口 `POST /ocr/b64/text`（与 nn.ci 同路径、同返回） |
| `requirements.txt` | 依赖：`fastapi` / `uvicorn` / `ddddocr` / `python-multipart` |
| `bootstrap` | FC 自定义运行时启动脚本（冷启动时自动装依赖 + 启动 app） |
| `Dockerfile` | 自定义容器镜像方案（依赖太大 / 非杭州地域时的备选，见下方说明） |
| `README.md` | 本文件 |

---

## 二、接口说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/ocr/b64/text` | POST | 传 base64 返回纯文本。请求体支持：纯 base64 字符串 / JSON `{"base64": "..."}` 或 `{"image":"..."}` / data URL `data:image/png;base64,...`。可选参数 `?digits=1` 仅保留 0–9 |
| `/ocr/file` | POST | `multipart/form-data` 上传文件，便于 curl / 网页手动测试 |
| `/` | GET | 简易网页表单，手动上传图片看结果 |
| `/health` | GET | 健康检查，返回 `{"status":"ok"}` |

`app.py` 监听 `0.0.0.0:${PORT:-9000}`（FC 自定义运行时默认端口 9000）。

---

## 三、本地运行

```bash
pip install -r requirements.txt
python app.py
# 访问 http://127.0.0.1:9000
```

本地仅用于调试；正式服务走下面的 FC 云端部署。

---

## 四、阿里云 FC 部署（已实测可行的路径）

> ⚠️ 入口很重要：别进左侧「函数智能」下面的 **AgentRun / FunModel / FunArt**（那是给 AI Agent、大模型、文生图用的，跑不了你的 FastAPI）。
> 正确入口是：**函数计算控制台 → 左侧「函数管理 → 函数列表」（部分账号显示为「云函数」）→ 创建函数 → 选 Web 函数**。

### 0. 前提
- 开通函数计算，顺手领「新用户试用额度」。
- **地域务必选「华东1·杭州（cn-hangzhou）」**：代码包上限 500MB（ddddocr + onnxruntime 解压后约 200–400MB）；其他地域仅 100MB 会超限。

### 1. 创建函数（Web 函数 + 自定义运行时）
- 创建方式：**使用自定义运行时创建**
- 函数类型：**Web 函数**
- 函数名：`ocr-api`
- 运行时：**Custom Runtime**（Debian 10）
- **代码上传方式**：通过 ZIP 包上传 → 上传本目录打好的 `ocr-api-fc.zip`
- **启动命令**：`bash bootstrap`
- **监听端口**：`9000`
- **内存规格**：建议 `1 GB`（ddddocr 加载模型需要内存；0.5GB 也能跑，OOM 就调大）
- **磁盘**：`10 GB`（关键，见踩坑 3；默认偏小装不下依赖）
- **最小实例数**：先填 `0`（按需计费，最省）

### 2. 添加 Python 公共层（最关键，否则装不上依赖）
- 函数详情 → **配置** → **层** → 添加官方公共层 → 选 **`Python 3.10 Runtime`**（兼容 Custom.Debian10）。
- 不选 `Python 3.10 OSS`（那是 OSS SDK）和 `Python 3.10 Package Collection`。
- `bootstrap` 会自动优先使用 `/opt/python3.10`，不再用系统自带的 3.7。

### 3. 触发器改为「无需认证」
- 函数详情 → **配置** → **触发器** → 编辑 HTTP 触发器 → **认证方式：无需认证（anonymous）**。
- 否则你的脚本调用会被拦（报 `MissingRequiredHeader`）。

### 4. 部署 & 拿地址
- 保存/部署后，在触发器里拿 **公网访问地址**，形如：
  `https://ocr-api-xxxx.cn-hangzhou.fcapp.run`
- 直接 `POST /ocr/b64/text` 即可，无需再绑域名（见第八节可选绑域名）。

---

## 五、踩坑记录（都是实打实解决过的，下次照着避）

| # | 现象 | 根因 | 解决 |
|---|------|------|------|
| 1 | `pip` 报 `from versions: none`，一个版本都装不上 | FC 自定义运行时自带 **Python 3.7.4** 太老，fastapi/uvicorn/ddddocr 要求 3.8+ | 给函数加 **Python310 公共层**，`bootstrap` 自动用新 Python |
| 2 | 装依赖时卡住 / 超时 | 阿里云国内环境连 `files.pythonhosted.org` 下载超时 | `bootstrap` 里已写死阿里云镜像 `-i https://mirrors.aliyun.com/pypi/simple/ --timeout 120` |
| 3 | `OSError: [Errno 28] No space left on device` | `/code` 可写层空间不足，装不下 onnxruntime 那套 | `bootstrap` 把依赖装到 **`/tmp/pydeps`**（函数磁盘），并把函数**磁盘调到 10GB** |
| 4 | `RuntimeError: Form data requires "python-multipart"` | `app.py` 的 `/ocr/file` 用了 `UploadFile`，FastAPI 需要该包 | 已在 `requirements.txt` 加入 `python-multipart` |
| 5 | `MissingRequiredHeader` / 调用被拒 | HTTP 触发器默认开了签名认证 | 触发器认证方式改 **无需认证** |

> 提示：以上全部已固化进 `bootstrap` 和 `requirements.txt`，**用最新 `ocr-api-fc.zip` 上传即可**，不用手改控制台（层、磁盘、触发器仍需在控制台设一次）。

---

## 六、bootstrap 原理（冷启动自动装依赖）

FC 自定义运行时**不会**自动读 `requirements.txt` 安装依赖，所以靠 `bootstrap` 在实例冷启动时补装一次：
1. 自动定位层里的 Python 3.10（系统 3.7 仅兜底）；
2. 检查 `ddddocr/fastapi/uvicorn` 是否已装，没装才 `pip install -t /tmp/pydeps`（阿里云镜像）；
3. 通过 `PYTHONPATH` 让 `app.py` 能找到 `/tmp/pydeps` 里的包；
4. `exec python3 app.py` 启动服务。

实例保活期间不会重复安装；实例缩容到 0 后下次冷启动会再装一次（约 1–3 分钟，见第九节）。

---

## 七、部署后验证

```bash
# 健康检查
curl -s --max-time 120 https://<你的地址>/health
# => {"status":"ok"}

# 识别（数字验证码加 ?digits=1）
curl -X POST "https://<你的地址>/ocr/b64/text?digits=1" \
  -H "Content-Type: text/plain" \
  --data "这里换成验证码图片的base64"
```

Python 调用（与你原来调 nn.ci 一致）：

```python
import requests, base64
url = "https://<你的地址>/ocr/b64/text?digits=1"
b64 = base64.b64encode(open("code.png", "rb").read()).decode()
print(requests.post(url, json={"base64": b64}, timeout=30).text)
```

浏览器打开 `https://<你的地址>/` 也可用网页表单手动传图测试。

---

## 八、绑定自定义域名（可选，但推荐）

前提：域名已在阿里云接入备案（根域与子域均需在阿里云完成备案）。自定义域名**本身免费**。

1. 函数计算控制台 → **函数管理 → 域名管理**（地区选杭州）→ **添加自定义域名**，填你的子域（例如 `cf.your-domain.xyz`），记下页面给的**公网 CNAME**。
2. **云解析 DNS** 控制台 → 给你的根域加记录：主机填子域前缀（如 `cf`）、类型 `CNAME`、值填上面的 FC CNAME。
3. 回 FC 配**路由**：路径 `/*` → 函数 `ocr-api` → 版本 `LATEST`。
4. **HTTPS（可选）**：可先不开启，仅用 HTTP 也能正常做程序化 API 调用（接口形如 `http://你的子域/...`）。
   若以后想加密或浏览器访问，再去「数字证书管理服务」申请免费 DV 证书（绑定你的子域）回来选上即可。
5. 等 DNS 生效（几分钟到几十分钟）。生效后接口变：
   `http://你的子域/ocr/b64/text?digits=1`
   原 `.fcapp.run` 地址仍可并用。

> 注意：自定义域名只是多一条访问入口，最终仍落到原 HTTP 触发器，**触发器保持「无需认证」**。

---

## 九、最小实例数 & 计费

- **按量付费，不用不花钱**：最小实例数保持 `0`，无请求不计费。
- **免费额度**：每月 100 万次调用 + 40 万 CU-秒算力免费；个人刷验证码量级基本 **≈0 元/月**。
- **冷启动**：空闲后实例回收，下次请求触发冷启动（含装依赖 + 加载 ddddocr 模型）约 **1–3 分钟**；保活期间很快。脚本自动识别验证码完全可用。
- **想常驻免冷启动**：函数详情 → **弹性管理 / 弹性策略** 标签页 → 创建/编辑规则 → 基础配置里把**最小实例数设为 1**。注意：>0 会让实例 **7×24 常驻**，即使空闲也产生少量费用（闲置单价很低）。

---

## 十、备选方案：自定义容器镜像（非杭州地域 / 想彻底打包依赖）

代码包方案依赖云端装、受冷启动影响。若想一劳永逸，可用容器镜像（上限 10GB，依赖烤进镜像、无冷启动装包）：

1. 装 Docker，在阿里云「容器镜像服务 ACR」建个人版实例 + 仓库。
2. 本目录 `docker build -t registry.cn-hangzhou.aliyuncs.com/<命名空间>/ocr-api:latest .` 并 `docker push`。
3. 函数计算 → 创建函数 → **Web 函数 / 自定义镜像** → 选该镜像，端口 `9000`，触发器无需认证。

---

## 十一、常见问题

- **调用 502 / FunctionNotStarted**：确认 `app.py` 监听 `0.0.0.0:9000`（本包已写 `${PORT:-9000}`，正常不会）。
- **部署后第一次请求很慢/超时**：正常的冷启动装依赖，多等一会儿或重试。
- **识别不准**：数字验证码务必加 `?digits=1`；干扰极强的图可先用 PIL 做灰度/二值化再识别。
- **代码包超限（100MB）**：换杭州地域，或改用容器镜像方案。

---

## 十二、附录：本机 → GitHub 推送（api.github.com REST 方式）

部分网络环境（如某些沙箱 / 内网）**直连 `github.com` 的 git 协议会被拦截**（返回 502），但 `api.github.com` 通常可达。本项目附带 `push_api.py`，改用 **GitHub REST API**（blobs → tree → commit → 更新 ref）代替 `git push`，无需本地装 git 也能把代码推上去。

### 前置条件
- 一个对目标仓库有**写入权限**的 GitHub Personal Access Token（Classic 勾 `repo`；或 Fine-grained 指定该仓库的 Contents 读写）。
- Python 3（脚本只用标准库 `urllib`，无第三方依赖）。

### 推送内容
脚本把本目录 `ocr-api-fc/` 的 5 个文件推到仓库的 **`fc/` 子目录** 与 **根目录** 各一份（根目录副本便于把仓库根直接当部署入口）：
`app.py` / `requirements.txt` / `bootstrap` / `Dockerfile` / `README.md`。

> 想只推 `fc/` 单一目录、或推到别的路径，改 `push_api.py` 里的 `FILES` 映射即可。

### 用法
```bash
# 1. 把脚本顶部的 OWNER / REPO 常量改成你的仓库（默认 PediyCCDebuger/ocr-api）
# 2. 通过环境变量传入 token —— 绝不写进任何文件
GH_TOKEN=github_pat_xxx python push_api.py
```
脚本自动完成：取 `main` 最新 commit → 为每个文件建 blob → 合成 tree（**保留仓库其他已有文件**）→ 建 commit → fast-forward `main`。结尾打印最终 commit SHA 和仓库地址。

### 安全注意事项
- token **只经命令行环境变量传入**；`push_api.py` 内部也不会把 token 回显（错误信息里会替换成 `<TOKEN>`）。
- 推送完建议到 GitHub 后台 **Revoke** 该 token，或确认它到期时间合理、且只限定本仓库。
- 若返回 `401 Bad credentials`：常见原因是 token **被截断 / 复制不全**（GitHub PAT 通常 70+ 字符），请整串重发再试；也可能是 token 已失效，需重新生成。

---

*部署记录归档：本项目从「本地 FastAPI」→「Neocities 静态页（ddddocr-node WASM）」→「Render / HuggingFace / Zeabur（均因信用卡或国内不可达放弃）」→ 最终落地「阿里云函数计算 FC Web 函数（自定义运行时 + Python310 层）」。代码可自行托管到你自己的 GitHub 仓库。*
