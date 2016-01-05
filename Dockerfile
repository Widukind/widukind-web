FROM debian:jessie

ENV LANG C.UTF-8
ENV PATH /opt/conda/bin:${PATH}
ENV PYTHON_RELEASE 3.4.3

ADD . /code/

ADD docker/sources.list /etc/apt/

RUN apt-get update -y

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential \
  python3-dev \
  ca-certificates \
  curl \
  git \
  bzip2

ADD docker/*.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/*.sh
RUN /usr/local/bin/install-miniconda.sh

ENV GUNICORN_RELEASE ${GUNICORN_RELEASE:-https://github.com/benoitc/gunicorn/tarball/master}

#BUG gevent on stable release    
RUN pip install ${GUNICORN_RELEASE}
    
WORKDIR /code/

RUN pip install -r requirements/default.txt
RUN pip install -e .

RUN mkdir -vp /etc/gunicorn

ADD docker/gunicorn_conf.py /etc/gunicorn/conf.py

EXPOSE 8080

CMD ["gunicorn", "-c", "/etc/gunicorn/conf.py", "widukind_web.wsgi:create_app()"]

