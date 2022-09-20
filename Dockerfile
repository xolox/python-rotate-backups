FROM python:3.9.14-bullseye
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
COPY . /app
RUN pip3 install .
ENTRYPOINT ["rotate-backups"]
