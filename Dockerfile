FROM widukind/docker-base

ADD . /code/

WORKDIR /code/

RUN pip install -r requirements/default.txt \
    && pip install https://github.com/benoitc/gunicorn/tarball/master \
    && pip install --no-deps -e .

EXPOSE 8080

CMD ["gunicorn", "-c", "/code/docker/gunicorn_conf.py", "widukind_web.wsgi:create_app()"]


