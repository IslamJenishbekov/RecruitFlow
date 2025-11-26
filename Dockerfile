FROM python:3.10-slim

# 1. Ставим системные пакеты (git нужен для gigaam!)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Копируем зависимости
COPY requirements.txt /app/

# 3. Устанавливаем их (ТУТ ставится Django)
RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем код проекта
COPY . /app/

# 5. Собираем статику с фейковыми ключами (чтобы сборка не упала)
RUN DJANGO_SECRET_KEY=build-mode-key \
    DATABASE_URL=postgres://user:pass@localhost:5432/db \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "RecruitFlow.wsgi:application"]