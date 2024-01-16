from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaProducer, KafkaConsumer
import pickle

kafka_url = "kafkica.openwhisk.svc.cluster.local"


admin_client = KafkaAdminClient(
    bootstrap_servers=kafka_url, 
    client_id='myAdminClient' # can be set to any value
)

topics = admin_client.list_topics()

topic_list = [NewTopic(name="federated", num_partitions=1, replication_factor=1)]
admin_client.create_topics(new_topics=topic_list, validate_only=False)


producer = KafkaProducer(
    bootstrap_servers=kafka_url
)


producer.send('federated', b'Your message')
producer.flush()

consumer = KafkaConsumer(
    'federated',
    bootstrap_servers=kafka_url,
    #auto_offset_reset='earliest', # Start reading from the earliest messages
    group_id='federated_grp_4',
    #value_deserializer=lambda m: pickle.loads(m)
)

for message in consumer:
    print(f"Received message: {message.value[:100]}")
    print(f"Unpickled: {pickle.loads(message.value)}")

consumer.close()