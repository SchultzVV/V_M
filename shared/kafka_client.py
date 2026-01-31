"""
Kafka utilities para event bus
"""
import json
from typing import Optional, Callable
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from shared.config import settings


class KafkaEventBus:
    """Cliente Kafka para event bus"""
    
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
    
    def _get_producer(self) -> KafkaProducer:
        """Lazy initialization do producer"""
        if not self.producer:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                acks='all',
                retries=3
            )
        return self.producer
    
    def publish(self, topic: str, message: dict, key: Optional[str] = None) -> bool:
        """Publica mensagem em um tópico"""
        try:
            producer = self._get_producer()
            key_bytes = key.encode('utf-8') if key else None
            future = producer.send(topic, value=message, key=key_bytes)
            future.get(timeout=10)  # Bloqueia até confirmação
            return True
        except KafkaError as e:
            print(f"Kafka publish error: {e}")
            return False
    
    def publish_event(self, event: dict) -> bool:
        """Publica evento de tracking"""
        return self.publish(
            topic=settings.KAFKA_TOPIC_EVENTS,
            message=event,
            key=event.get('user_id')
        )
    
    def publish_profile_update(self, profile: dict) -> bool:
        """Publica atualização de perfil"""
        return self.publish(
            topic=settings.KAFKA_TOPIC_PROFILES,
            message=profile,
            key=profile.get('user_id')
        )
    
    def consume(
        self, 
        topic: str, 
        group_id: str,
        handler: Callable[[dict], None],
        auto_commit: bool = True
    ):
        """Consome mensagens de um tópico"""
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=auto_commit
        )
        
        print(f"📥 Consuming from topic: {topic} (group: {group_id})")
        
        try:
            for message in consumer:
                try:
                    handler(message.value)
                except Exception as e:
                    print(f"Error handling message: {e}")
        except KeyboardInterrupt:
            print("Stopping consumer...")
        finally:
            consumer.close()
    
    def close(self):
        """Fecha conexões"""
        if self.producer:
            self.producer.close()


# Instância global
event_bus = KafkaEventBus()
