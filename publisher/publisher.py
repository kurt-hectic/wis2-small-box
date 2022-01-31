import os
import pika
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pika").setLevel(logging.WARNING)


url = os.environ.get('BROKER_URL', 'amqp://guest:guest@localhost:5672/%2f') # the location and username password of the broker
exchange_name = os.environ.get('PUB_EXCHANGE_NAME',"publication")

def callback(ch, method, properties, body):
    """callback function, called when a new notificaton arrives"""
    
    logging.info(f"callback {method.routing_key}")
  
  
def setup_incoming(connection):
    """setup the connection to the incoming exchange"""
    
    channel = connection.channel()

    channel.exchange_declare(exchange=exchange_name,exchange_type='fanout')
    
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=exchange_name,queue=queue_name)
    # configure callback function
    channel.basic_consume(queue_name,
                          callback,
                          auto_ack=True) #FIXME: check for data safety

    # start waiting for messages
    logging.info('waiting for messages:')

    return channel

def main():

    logging.info("setting up MQP consumer")

    # connect to the broker
    params = pika.URLParameters(url)
    
    while(True):
        try:
        
            logging.debug("Connecting to {}".format(params))
            incoming_connection = pika.BlockingConnection(params)
         
            incoming_channel = setup_incoming(incoming_connection)
            
            try:
                incoming_channel.start_consuming()
            except KeyboardInterrupt:
                incoming_channel.stop_consuming()
                incoming_connection.close()
                break
        except pika.exceptions.ConnectionClosedByBroker:
            # Uncomment this to make the example not attempt recovery
            # from server-initiated connection closure, including
            # when the node is stopped cleanly
            #
            # break
            continue
        # Do not recover on channel errors
        except pika.exceptions.AMQPChannelError as err:
            logging.info("Caught a channel error: {}, stopping...".format(err))
            break
        # Recover on all other connection errors
        except pika.exceptions.AMQPConnectionError:
            logging.info("Connection was closed, retrying...")
            time.sleep(0.5)
            continue
        
    
    # gracefully stop and close ressources
    incoming_connection.close()

if __name__ == "__main__":
    main()