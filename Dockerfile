FROM python:3.13-slim

WORKDIR /SIH

COPY pyproject.toml uv.lock ./

RUN pip install uv
RUN uv sync --frozen --no-install-project

COPY . .

ENV PATH="/SIH/.venv/bin:$PATH"
CMD ["uv","run","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]