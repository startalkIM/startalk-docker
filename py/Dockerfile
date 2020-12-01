FROM python:3.7.9-alpine3.12 AS base
RUN apk add --no-cache libpq 

FROM base AS dependencies

RUN mkdir /install
WORKDIR /install
COPY requirements.txt /

ENV PATH=/root/.local:$PATH

RUN apk update && apk add --no-cache postgresql-dev gcc python3-dev musl-dev libxslt-dev libpq bash && \
pip install --prefix=/install -r /requirements.txt

FROM base


# copy only the dependencies installation from the 1st stage image
# COPY --from=dependencies /root/.local/bin /root/.local
COPY --from=dependencies /install /usr/local

COPY ./code /app

WORKDIR /app

# update PATH environment variable
ENV PATH=/usr/local:$PATH

CMD [ "python", "./start_service.py" ]


