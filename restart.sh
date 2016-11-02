#!/bin/bash
ps -ef|grep celery|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
ps -ef|grep runserver|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
nohup celery -A ActionSpace flower --basic_auth=wqz:belongwqz,demo:password123 --address=0.0.0.0 --port=5555 &
celery -A ActionSpace worker -l info --detach
nohup python manage.py runserver 0.0.0.0:8000 &

