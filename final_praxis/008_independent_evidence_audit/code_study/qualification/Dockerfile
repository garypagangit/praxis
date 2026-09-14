FROM python:3.11.9-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
RUN python -m pip install --no-cache-dir numpy==1.26.4 psutil==5.9.8 \
    && groupadd --gid 10001 praxis \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin praxis
WORKDIR /app
COPY qualification/ /app/
USER 10001:10001
ENTRYPOINT ["python", "/app/run_qualification.py"]
