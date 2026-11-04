FROM python:3.12-slim

WORKDIR /app
COPY calc_core.py mcp_server.py ./
COPY packs ./packs
RUN pip install --no-cache-dir "sympy>=1.12"

ENTRYPOINT ["python", "-u", "/app/mcp_server.py"]
