FROM anoa/matrix-nio

RUN mkdir -p /app

COPY requirements.txt /app

WORKDIR /app

RUN pip install -r requirements.txt

COPY . .

CMD python main.py /config/config.yaml
