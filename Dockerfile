FROM python:3.8-alpine as base
FROM base as builder
RUN mkdir /install
COPY . /src
RUN pip install --prefix=/install /src

FROM base
# Added system deps for runtime.
RUN apk add less
COPY --from=builder /install /usr/local
COPY rotate_backups/ /app
WORKDIR /app

ENTRYPOINT ["rotate-backups"]
CMD ["-h"]
