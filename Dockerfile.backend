FROM python:3.12-slim

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

COPY . .

CMD ["poetry", "run", "python", "main.py"]
