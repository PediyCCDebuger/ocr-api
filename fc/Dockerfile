# 阿里云函数计算 FC 自定义容器镜像
# 适用场景：依赖包体积超过代码包上限（杭州 500MB / 其他 100MB）时，
# 用自定义容器最稳（镜像上限 10GB，onnxruntime 完全无压力）。
FROM python:3.10-slim

WORKDIR /code

# 先装依赖（利用 Docker 层缓存）
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /code/app.py

# FC 自定义容器默认通过环境变量 PORT 注入监听端口（默认 9000），需监听 0.0.0.0
EXPOSE 9000
ENV PORT=9000

CMD ["python3", "app.py"]
