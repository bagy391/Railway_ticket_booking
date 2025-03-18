FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /opt/app

# Install dependencies
COPY requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt

# Copy project
COPY . /opt/app/

# Expose port
EXPOSE 8000