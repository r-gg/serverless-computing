from kafka import KafkaProducer, KafkaConsumer

kafka_url = "kafkica.openwhisk.svc.cluster.local"


consumer = KafkaConsumer(
    'federated',
    bootstrap_servers=kafka_url,
    auto_offset_reset='earliest', # Start reading from the earliest messages
    group_id='federated_grp_2'
)

try:
    for message in consumer:
        print(f"Received message: {message.value}")
except Exception:
    consumer.close()