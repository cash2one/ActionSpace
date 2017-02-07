#!/bin/bash

function main()
{
    local worker_count=8
    cd /wls/wls81/om
    echo "$(date '+%Y-%m-%d %H:%M:%S'):restart [$@]" >> ./logs/restart.log
    ps -ef|grep celery|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
    ps -ef|grep flower|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
    nohup celery -A ActionSpace flower --address=0.0.0.0 --port=5555 --url_prefix=flower >./logs/flower.log 2>&1 &
    celery -A ActionSpace worker -l info -f ./logs/celery.log --detach
    celery -A ActionSpace beat -l info -f ./logs/celery-beat.log --detach
    ps -ef|grep runserver|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
    python manage.py runserver --noworker 0.0.0.0:8000  > ./logs/server.log 2>&1 &
    ps -ef|grep runworker|grep -v grep|awk '{print $2}'|xargs -i kill -9 {} 
    for ((i=1;i<=${worker_count};i++))
    do
        python manage.py runworker -v 2 > "./logs/worker${i}.log" 2>&1 &
    done    
    if [ "$1" = "all" ]
    then
        ps -ef|grep notebook|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
        nohup jupyter notebook >./logs/notebook.logs 2>&1 &
        ps -ef|grep redis-server|grep 6379|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
        nohup redis-server > ./logs/redis.log 2>&1 &
        ps -ef|grep redmon|grep -v grep|awk '{print $2}'|xargs -i kill -9 {}
        #nohup redmon -r redis://10.25.167.89:7001 -a 0.0.0.0 -p 8083 -b /redis/ > ./logs/redmon.log 2>&1 &
        nohup redmon -a 0.0.0.0 -p 8083 -b /redis/ > ./logs/redmon.log 2>&1 &
    fi
    cd -
}

main $@
