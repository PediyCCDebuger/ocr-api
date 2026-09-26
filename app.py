#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ddddocr 在线 OCR API —— 1:1 平替 https://api.nn.ci/ocr/b64/text
纯 Python + FastAPI，可一键部署到 Render / Hugging Face Spaces / 任意 Docker 平台。

接口：
  POST /ocr/b64/text   与 nn.ci 同路径、同用法
       请求体（任选其一）：
         - 纯 base64 字符串（原始文本）
         - JSON: {"base64": "...."}  或  {"image": "...."}
         - data URL: data:image/png;base64,....
       可选参数 ?digits=1  -> 仅保留 0-9（数字验证码更准）
       返回：纯文本（识别出的字符），与 nn.ci 一致（text/plain）
  POST /ocr/file        multipart 上传文件，便于 curl / 网页手动测试
  GET  /               简易网页表单（手动上传图片看结果）
  GET  /health         健康检查 {"status":"ok"}
  HEAD /              平台健康探针（Render 用它探活）
"""
import base64
import json
import re

import ddddocr
from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

# 兼容不同 ddddocr 版本的构造参数
try:
    _ocr = ddddocr.DdddOcr(show_ad=False)
except TypeError:
    _ocr = ddddocr.DdddOcr()

app = FastAPI(title="ddddocr API — nn.ci 平替")

# 允许跨域，方便其他网页（如你的 Neocities 站点）直接 fetch 调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>ddddocr 在线识别</title>
<style>body{font-family:system-ui,Arial;max-width:560px;margin:40px auto;padding:0 16px;color:#222}
.m{color:#888;font-size:13px}textarea,input{width:100%;box-sizing:border-box;margin:6px 0;padding:8px}
button{background:#2d7d5a;color:#fff;border:0;padding:10px 16px;border-radius:6px;cursor:pointer}
pre{background:#f4f4f4;padding:12px;border-radius:6px;min-height:22px;white-space:pre-wrap;word-break:break-all}</style></head>
<body><h2>ddddocr 在线识别（nn.ci 平替）</h2>
<p class="m">POST /ocr/b64/text （base64→文本，?digits=1 仅数字）　POST /ocr/file（上传文件）</p>
<input id="f" type="file" accept="image/*">
<p><label><input type="checkbox" id="d"> 仅识别数字 (0-9)</label></p>
<button onclick="run()">识别</button>
<h3>结果</h3><pre id="o">—</pre>
<script>
async function run(){
 const f=document.getElementById('f').files[0]; if(!f){alert('请先选图片');return;}
 const fd=new FormData(); fd.append('file',f);
 const d=document.getElementById('d').checked?'?digits=1':'';
 const r=await fetch('/ocr/file'+d,{method:'POST',body:fd});
 document.getElementById('o').textContent=await r.text();
}
</script></body></html>"""


def extract_b64(text: str):
    """从多种输入格式里取出 base64 字符串。"""
    text = (text or "").strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            obj = json.loads(text)
            b64 = obj.get("base64") or obj.get("image") or obj.get("img")
            if isinstance(b64, str):
                text = b64
        except Exception:
            pass
    if "," in text and text.lower().startswith("data:"):
        text = text.split(",", 1)[1]
    return text.strip()


def recognize(image_bytes: bytes, digits_only: bool) -> str:
    res = _ocr.classification(image_bytes)
    if digits_only:
        res = re.sub(r"[^0-9]", "", res)
    return res


@app.post("/ocr/b64/text")
async def ocr_b64_text(request: Request, digits: bool = Query(False)):
    raw = await request.body()
    b64 = extract_b64(raw.decode("utf-8", "ignore"))
    if not b64:
        return PlainTextResponse("no image", status_code=400)
    try:
        img = base64.b64decode(b64)
    except Exception:
        return PlainTextResponse("invalid base64", status_code=400)
    try:
        text = recognize(img, digits)
    except Exception as e:  # noqa
        return PlainTextResponse(f"error: {e}", status_code=500)
    return PlainTextResponse(text)


@app.post("/ocr/file")
async def ocr_file(file: UploadFile = File(...), digits: bool = Query(False)):
    img = await file.read()
    try:
        text = recognize(img, digits)
    except Exception as e:  # noqa
        return PlainTextResponse(f"error: {e}", status_code=500)
    return PlainTextResponse(text)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index():
    return HTMLResponse(PAGE)


@app.head("/")
async def head_root():
    return Response(status_code=200)
