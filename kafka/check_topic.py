from kafka import KafkaProducer, KafkaConsumer

kafka_url = "kafkica.openwhisk.svc.cluster.local"


consumer = KafkaConsumer(
    'federated',
    bootstrap_servers=kafka_url,
    auto_offset_reset='earliest', # Start reading from the earliest messages
    group_id='federated_grp'
)

for message in consumer:
    print(f"Received message: {message.value}")
