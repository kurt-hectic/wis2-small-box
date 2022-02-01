import csv
import os
import json
import redis
import pika
import logging
import time


logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pika").setLevel(logging.WARNING)
logging.getLogger("csv2bufr").setLevel(logging.WARNING)

from csv2bufr import transform

url = os.environ.get('BROKER_URL', 'amqp://guest:guest@localhost:5672/%2f') # the location and username password of the broker
exchange_name = os.environ.get('EXCHANGE_NAME',"incoming")
exchange_pub_name = os.environ.get('PUB_EXCHANGE_NAME',"publication")
r = redis.Redis(host="redis")

logging.debug("loading mapping")
mappings = json.load( open(r"malawi_synop_bufr_tp.json") ) 


def callback(ch, method, properties, body):
    """callback function, called when a new notificaton arrives"""
    
    wigos_id = method.routing_key
    csv_string = body.decode("utf-8")
    
    logging.info("Received message with topic: " + wigos_id )
    logging.info(f"callback {properties}, {wigos_id}")
    
    bufr = process_csv(wigos_id,csv_string)
    
    if bufr:
        publish_for_publication(wigos_id,bufr)
    

def process_csv(wigos_id,data): 
    """transform the csv into bufr""" 

    logging.info(f"processing {wigos_id}")

    station_metadata = r.json().get(wigos_id, "." )
    
    if not station_metadata:
        raise Exception(f"no metadata for {wigos_id}")
    
    logging.debug("got metadata {} for {}".format( json.dumps(station_metadata,indent=4),wigos_id))
    logging.debug(f"incoming CSV data {data}")
    
    result = transform(data, station_metadata, mappings)
    logging.debug(f"obtained bufr records")
    
    ret = next(result)
    
    if ret:
        logging.debug(f"returning {ret['_meta']}")
        return ret
    else:
        return False
    

def publish_for_publication(wigos_id,bufr):
    """send the bufr back to the internal queue for publication""" 
    
    logging.info(f"publishing {wigos_id}")
    
    params = pika.URLParameters(url)
    outgoing_connection = pika.BlockingConnection(params) # FIXME: this is not efficient. opens a new connection for each message
    channel = outgoing_connection.channel()
    
    channel.exchange_declare(exchange=exchange_pub_name, exchange_type='fanout')

    key = f"{wigos_id}_{bufr['_meta']['data_date']}"

    logging.debug(f"publishing to exchange with {key}")
    channel.basic_publish(exchange=exchange_pub_name,routing_key=key,body=bufr["bufr4"])      
    
    channel.close()
    outgoing_connection.close()
    
    logging.debug("closing connection")
      
       
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
    
def setup_outgoing(connection):
    """setup the connection to the outgoing exchange"""
    
    
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange_pub_name, exchange_type='fanout')
    
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
    time.sleep(15) # wait for message queue to come up
    main()