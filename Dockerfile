# Gunakan official image Playwright Python dari Microsoft
# Base image ini sudah menyertakan Chromium, Firefox, Webkit, beserta seluruh OS dependencies Linux
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set working directory di container
WORKDIR /app

# Copy file requirements.txt ke container
COPY requirements.txt .

# Install dependencies Python & pastikan browser chromium terinstall
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy seluruh file project ke dalam container
COPY . .

# Environment variable opsional
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Command default saat dikirim/dideploy ke Railway
# Menjalankan bot Telegram yang memproses web scraping
CMD ["python", "capskip_bot.py"]
