# wis2-small-box

This small box can receive incoming messages in CSV via an incoming message queue. It then converts them into BUFR, crafts a WIS 2.0 compatible notification and publishes it on its broker. The file is made available on the web via an integrated minio storage.

## startup
```docker-compose up ```

Send data: Send CSV file to exchange *incoming* on vhost "internal" via AMQP.

## architecture
The box consists of two main components, the converter and the publisher, orchestrated by a rabbitmq broker. Files are inserted into the box by sending them to the *incoming* exchange. The converter converts a CSV file into BUFR whereas the publisher is responsible for publishing the message in WIS 2.0 compatible format. These components are supported by an internal redis cache, which holds station metadata needed for the conversion and which is populated initially by a launch component (launchpad). The components communicate via the internal exchanges *incoming* and *publishing* hosted on the internal rabbitmq virtual-host.. The final message is published on a topic exchange on the public rabbitmq virtual-host. 

The design does not rely on the file-system and can in principle be deployed on a kubernetes cluster to exploit parallelization. 
