FROM python:3.12

WORKDIR /nuggit

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY nuggit/ /nuggit

ENV PYTHONUNBUFFERED=1
CMD ["python", "nuggit.py"]
