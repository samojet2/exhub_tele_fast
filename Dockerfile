FROM python:3.12

# --------------------------------
# Environment
# --------------------------------

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --------------------------------
# Working directory
# --------------------------------

WORKDIR /app

# --------------------------------
# Install dependencies
# --------------------------------

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --------------------------------
# Copy project
# --------------------------------

COPY . .

# --------------------------------
# Port
# --------------------------------

EXPOSE 8000

# --------------------------------
# Run
# --------------------------------

CMD ["gunicorn", \
     "app.main:app", \
     "-k", \
     "uvicorn.workers.UvicornWorker", \
     "--bind", \
     "0.0.0.0:8000", \
     "--workers", \
     "1", \
     "--access-logfile", \
     "-", \
     "--error-logfile", \
     "-"]