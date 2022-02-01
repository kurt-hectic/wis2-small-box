import os
import io
import pika
import logging
import time
import hashlib
import base64
import json

from datetime import datetime, timezone
from minio import Minio

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pika").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


url = os.environ.get('BROKER_URL', 'amqp://guest:guest@localhost:5672/%2f') # the location and username password of the broker
minio_user = os.environ.get("MINIO_USER")
minio_pass = os.environ.get("MINIO_PASS")
public_topic = os.environ.get('TOPIC')
MAX_SIZE = int(os.environ.get('MAX_SIZE',4000))
PUBLIC_URL = os.environ.get('PUBLIC_URL','http://localhost:9000/public')

exchange_name = os.environ.get('PUB_EXCHANGE_NAME',"publication")

def make_mqp_message(rel_path,body):
    """creates a MQP notification based on the WIS 2.0 message structure.
    Embedds the file, if below message max size
    """
    
    logging.debug("entry make_mqp_message")

    size = len(body)
    
    pub_time = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")
    
    base64_digest = base64.b64encode( hashlib.sha512(body).digest() ).decode("utf8")
       
    # message structure
    message = {
        "pubTime" : pub_time,
        "baseUrl" : PUBLIC_URL,
        "integrity" : { "method" : "sha512" , "value" : base64_digest },
        "relPath" : "/{}".format(rel_path),
        "size" : size
    }

    # embed the file if below max size
    if size <= MAX_SIZE:
        logging.info("embedding file into message")
        base64_string = base64.b64encode(body).decode("ascii")
        message["content"] = {"encoding" : "base64", "value" : base64_string }

    logging.debug("exit: make_mqp_message: returning ",message)

    return message



def publish_message(filename,body):
    """function that publishes the message on the public broker and makes the file available publicly"""

    logging.info("creating minIO client")
    client = Minio("minio:9000",access_key=minio_user,secret_key=minio_pass,secure=False)

    client.put_object("public",filename,io.BytesIO(body),len(body))
    
    logging.info("file published on minio")
    
    logging.info("establishing connection to brokwer")
    
    params = pika.URLParameters(url)
    outgoing_connection = pika.BlockingConnection(params) # FIXME: this is not efficient. opens a new connection for each message
    channel = outgoing_connection.channel()
    
    
    key = public_topic

    logging.debug(f"publishing to exchange with {key}")
    
    msg = json.dumps(make_mqp_message(filename,body))
    
    channel.basic_publish(exchange="amq.topic",routing_key=key,body=msg)      
    
    outgoing_connection.close()
    
    logging.debug("closing connection")
    


def callback(ch, method, properties, body):
    """callback function, called when a new notificaton arrives"""
    
    logging.info(f"callback {method.routing_key}")
    
    
    now = int( time.time() )
    
    (wigos_id,obs_date) = method.routing_key.split("_")
    mydate = datetime.strptime(obs_date,"%Y-%m-%d %H:%M:%S").strftime("%Y%m%d%H%M%S")
    
    filename=f"{wigos_id}_{mydate}_{now}.bufr4"
    
    publish_message(filename,body)
  
  
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

    logging.info("setting up minIO client")
    
 
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