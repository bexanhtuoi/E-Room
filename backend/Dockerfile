FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install uv && uv sync

EXPOSE 8000
EXPOSE 9000

CMD ["uv", "run", "python", "-m", "app.server"]
