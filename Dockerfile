FROM python:3.14-slim-trixie

WORKDIR /usr/src/telegramArchiver

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENTRYPOINT ["uv", "run", "python", "./main.py"]