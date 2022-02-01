import pika
import logging
import io

logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.WARNING)


file = r"../converter/test/Namitambo_SYNOP.csv" #

def main():

    params = pika.URLParameters("amqp://internal:rt9w3d2DFwfVJQJ@box.wis.wmo.int:5672/internal")
    
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    
    #channel.exchange_declare(exchange='incoming', exchange_type='fanout')

    
    with open(file,encoding="utf-8") as f:
        channel.basic_publish(exchange="incoming",routing_key="0-454-2-AWSNAMITAMBO",body=f.read())

    channel.close()
    connection.close()

if __name__ == "__main__":
    main()