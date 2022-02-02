import pika
import logging
import io
import os
import sys

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


AMQP_URL = os.environ.get("AMQP_URL","amqp://internal:rt9w3d2DFwfVJQJ@127.0.0.1:5672/internal")

def main():

    file = sys.argv[1]

    params = pika.URLParameters(AMQP_URL)
    
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    #channel.exchange_declare(exchange='incoming', exchange_type='fanout')

    head, filename = os.path.split(file)
    key = filename.replace(".csv","")
    
    with open(file,encoding="utf-8") as f:
        channel.basic_publish(exchange="incoming",routing_key=key,body=f.read())

    channel.close()
    connection.close()

if __name__ == "__main__":
    main()