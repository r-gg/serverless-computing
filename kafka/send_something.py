from kafka import KafkaProducer

kafka_url = "kafkica.openwhisk.svc.cluster.local"


producer = KafkaProducer(
    bootstrap_servers=kafka_url
)


producer.send('federated', b'Your message')
producer.flush()
