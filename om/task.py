# coding=utf-8
from __future__ import print_function
import time
from om.util import *
from random import randint
from om.models import Task, JobGroup, Job


def exec_task_callback(chan, method, properties, body):
    print(chan, body, method, properties, 'body:[%s]' % body)
    if Task.objects.filter(pk=body).exists():
        exec_task(Task.objects.get(pk=body))
    else:
        print('invalid task id [%s]' % body)


def loop():
    conn = pika.BlockingConnection(pika.URLParameters(MQ_URL))
    ch = conn.channel()
    ch.exchange_declare(exchange=OM_EXCHANGE, type='direct')
    ch.queue_declare(queue=TASK_EXEC_QUEUE)
    ch.queue_bind(exchange=OM_EXCHANGE, queue=TASK_EXEC_QUEUE, routing_key=TASK_EXEC_KEY)
    ch.basic_consume(consumer_callback=exec_task_callback, queue=TASK_EXEC_QUEUE, no_ack=True)
    ch.start_consuming()
    ch.close()
    conn.close()


def exec_task(t):
    flow = t.exec_flow
    group_list = str2arr(flow.job_group_list)
    t.run()
    log = Task.TaskLog(t)
    for group_id in group_list:
        group = JobGroup.objects.get(pk=group_id)
        for job_id in group.job_list.split(','):
            job = Job.objects.get(pk=job_id)
            log.begin_job(group, job)
            send(JOB_CHANGED, ALL)
            time.sleep(randint(1, 3))
            log.finish_job(group, job)
            log.set_out(group, job, '执行成功！')
            if job.pause_when_finish:
                log.wait(group, job)
                send(JOB_CHANGED, ALL)
                wait(JOB_CONFIRM, '%s-%s-%s-%s' % (str(t.id), str(flow.id), group_id, job_id))
                log.wait(group, job, False)
            else:
                send(JOB_CHANGED, ALL)
    t.finish()
    t.save()
    send(JOB_CHANGED, ALL)
    time.sleep(randint(1, 5))