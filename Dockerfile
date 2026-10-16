FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Create a regular user to run the application
RUN useradd --create-home appuser

# Give appuser ownership of the application directory
RUN chown -R appuser:appuser /app

# Switch from root to appuser
USER appuser

CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:5000", "app:app"]
