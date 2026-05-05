FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy your code
COPY yt_chatbot_backend.py .
COPY yt_chatbot_frontend.py .

# Expose port (Streamlit uses 8501)
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "yt_chatbot_frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]