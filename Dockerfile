FROM python:3.6-alpine

ENV FLASK_APP flasky.py
ENV FLASK_CONFIG docker

# create a new user with default value
RUN adduser -D flasky
USER flasky

WORKDIR /home/flasky

COPY requirements requirements
RUN python -m venv venv \
  && venv/bin/pip install --no-cache-dir -r requirements/docker.txt
# pip install --no-cache-dir is equivalent to
# RUN python -m venv venv \
#   && venv/bin/pip install -r requirements/docker.txt \
#   && rm -rf /home/flasky/.cache/pip

# copy instead mount file in production
COPY app app
COPY migrations migrations
COPY flasky.py config.py boot.sh ./

# runtime conf
EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
