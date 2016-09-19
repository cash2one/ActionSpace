# coding=utf-8
from __future__ import print_function
import pika

MQ_URL = 'amqp://action_space:action_space@localhost:5672/%2F'
JOB_CONFIRM = 'JOB_CONFIRM'
JOB_CHANGED = 'JOB_CHANGED'
OM_EXCHANGE = 'om'
TASK_EXEC_QUEUE = 'task_exec_queue'
TASK_EXEC_KEY = 'task_exec_key'
ALL = 'ALL'


def send_task_to_exec(task_id):
    conn = pika.BlockingConnection(pika.URLParameters(MQ_URL))
    ch = conn.channel()
    ch.exchange_declare(exchange=OM_EXCHANGE, type='direct')
    ch.queue_declare(queue=TASK_EXEC_QUEUE)
    ch.basic_publish(exchange=OM_EXCHANGE, routing_key=TASK_EXEC_KEY, body=str(task_id))
    ch.close()
    conn.close()


def notify(ch, method, properties, body):
    print(body, method, properties)
    ch.stop_consuming()


def wait(topic, queue_name):
    queue = '[%s]-[%s]' % (topic, queue_name)
    routing_key = 'K_' + queue
    print('wait %s' % queue)
    conn = pika.BlockingConnection(pika.URLParameters(MQ_URL))
    ch = conn.channel()
    ch.exchange_declare(exchange=OM_EXCHANGE, type='direct')
    ch.queue_declare(queue=queue)
    ch.queue_bind(exchange=OM_EXCHANGE, queue=queue, routing_key=routing_key)
    ch.basic_consume(consumer_callback=notify, queue=queue, no_ack=True)
    ch.start_consuming()
    ch.close()
    conn.close()


def send(topic, queue_name):
    queue = '[%s]-[%s]' % (topic, queue_name)
    routing_key = 'K_' + queue
    msg = 'Y'
    print('send %s' % queue)
    conn = pika.BlockingConnection(pika.URLParameters(MQ_URL))
    ch = conn.channel()
    ch.exchange_declare(exchange=OM_EXCHANGE, type='direct')
    ch.queue_declare(queue=queue)
    ch.basic_publish(exchange=OM_EXCHANGE, routing_key=routing_key, body=msg)
    ch.close()
    conn.close()


def str2arr(val, sep=',', digit_check=True):
    arr = []
    if val:
        arr = [x for x in val.split(sep) if not digit_check or x.isdigit()]
    return arr
