start py -2 manage.py runserver
start celery -A ActionSpace worker -l info
start celery -A ActionSpace flower --basic_auth=wqz:belongwqz,demo:password123
start celery beat
cd /d D:\soft\nginx
start run.bat