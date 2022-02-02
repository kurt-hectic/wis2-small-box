# wis2-small-box

This small box can receive incoming messages in CSV via an incoming message queue. It then converts them into BUFR, crafts a WIS 2.0 compatible notification and publishes it on its broker. The file is made available on the web via an integrated minio storage.

# installation and use
## code and startup
```git clone https://github.com/kurt-hectic/wis2-small-box ; cd wis2-small-box```

```docker-compose up --build```

## Send test data:
```pip install python3 pike```
```cd testing ``` 
```python .\publish_test.py .\test\0-454-2-AWSNAMITAMBO.csv ``` 

Can use environment variable *AMQP_URL* to set broker url (points to localhost, internal v-host) 

## architecture
The box consists of two main components, the converter and the publisher, orchestrated by a rabbitmq broker. Files are inserted into the box by sending them to the *incoming* exchange via AMQP. The converter converts a CSV file into BUFR whereas the publisher is responsible for publishing the message in WIS 2.0 compatible format. These components are supported by an internal redis cache, which holds station metadata needed for the conversion and which is populated initially by a launch component (launchpad). The components communicate via the internal exchanges *incoming* and *publishing* hosted on the internal rabbitmq virtual-host. The final message is published on a topic exchange on the public rabbitmq virtual-host and the file put on a minio server for public download. 

![architecture diagram](https://github.com/kurt-hectic/wis2-small-box/blob/develop/doc/diagram.PNG?raw=true)

## notes
The design does not rely on the file-system and can in principle be deployed on a kubernetes cluster to exploit parallelization. 
The fact that data is inserted into the system via MQP allows it to be fronted by a variety of systems, e.g FTP, SFTP or S3.