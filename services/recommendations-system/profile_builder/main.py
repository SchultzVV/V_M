"""
Profile Builder - Job batch que constrói perfis de usuários
"""
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict
import openai

from shared.database import SessionLocal, ProfileModel, EventModel, IngestLogModel, EventType
from shared.config import settings
from shared.kafka_client import event_bus

# Configurar OpenAI
openai.api_key = settings.OPENAI_API_KEY


async def generate_embedding(text: str) -> list[float]:
    """Gera embedding usando OpenAI"""
    try:
        response = await openai.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return []


def aggregate_click_stats(db: Session, user_id: str) -> Dict[str, int]:
    """Agrega estatísticas de cliques do usuário"""
    click_events = db.query(EventModel).filter(
        EventModel.user_id == user_id,
        EventModel.event_type == EventType.CLICK
    ).all()
    
    stats = {}
    for event in click_events:
        item_id = event.item_id
        stats[item_id] = stats.get(item_id, 0) + 1
    
    return stats


def aggregate_impression_stats(db: Session, user_id: str) -> Dict[str, int]:
    """Agrega estatísticas de impressões do usuário"""
    impression_events = db.query(EventModel).filter(
        EventModel.user_id == user_id,
        EventModel.event_type == EventType.IMPRESSION
    ).all()
    
    stats = {}
    for event in impression_events:
        item_id = event.item_id
        stats[item_id] = stats.get(item_id, 0) + 1
    
    return stats


def build_embedding_text(db: Session, user_id: str) -> str:
    """
    Constrói texto para embedding a partir de:
    - Bio do Instagram
    - Últimas captions
    """
    # Buscar último ingest
    ingest_log = db.query(IngestLogModel).filter(
        IngestLogModel.user_id == user_id,
        IngestLogModel.status == "success"
    ).order_by(IngestLogModel.ingested_at.desc()).first()
    
    if not ingest_log or not ingest_log.profile_data:
        return ""
    
    profile_data = ingest_log.profile_data
    
    # Bio
    bio = profile_data.get("bio", "")
    
    # Captions (últimas N)
    # Note: captions não estão no profile_data, precisaríamos outro campo
    # Por simplicidade, vamos usar só a bio no MVP
    
    embedding_text = f"Bio: {bio}"
    
    return embedding_text


async def build_profile(user_id: str, db: Session) -> bool:
    """
    Constrói perfil completo do usuário
    
    Steps:
    1. Agregar eventos (clicks, impressões)
    2. Construir texto de embedding (bio + captions)
    3. Gerar embedding
    4. Salvar perfil
    """
    try:
        print(f"🔨 Building profile for user: {user_id}")
        
        # 1. Agregar eventos
        click_stats = aggregate_click_stats(db, user_id)
        impression_stats = aggregate_impression_stats(db, user_id)
        
        # 2. Construir texto
        embedding_text = build_embedding_text(db, user_id)
        
        if not embedding_text:
            print(f"⚠️  No data for user {user_id}, skipping")
            return False
        
        # 3. Gerar embedding
        embedding_vector = await generate_embedding(embedding_text)
        
        if not embedding_vector:
            print(f"❌ Failed to generate embedding for user {user_id}")
            return False
        
        # 4. Salvar perfil
        profile = db.query(ProfileModel).filter(
            ProfileModel.user_id == user_id
        ).first()
        
        if profile:
            # Atualizar existente
            profile.embedding_text = embedding_text
            profile.embedding_vector = embedding_vector
            profile.click_stats = click_stats
            profile.impression_stats = impression_stats
            profile.last_updated = datetime.utcnow()
        else:
            # Criar novo
            profile = ProfileModel(
                user_id=user_id,
                embedding_text=embedding_text,
                embedding_vector=embedding_vector,
                click_stats=click_stats,
                impression_stats=impression_stats,
                last_updated=datetime.utcnow()
            )
            db.add(profile)
        
        db.commit()
        
        print(f"✅ Profile built for user {user_id}")
        
        # Publicar atualização no Kafka
        event_bus.publish_profile_update({
            "user_id": user_id,
            "updated_at": datetime.utcnow().isoformat(),
            "click_count": sum(click_stats.values()),
            "impression_count": sum(impression_stats.values())
        })
        
        return True
    
    except Exception as e:
        print(f"❌ Error building profile for {user_id}: {e}")
        db.rollback()
        return False


async def build_all_profiles():
    """
    Job principal: constrói perfis para todos os usuários
    
    Executar periodicamente (cron, Airflow, etc.)
    """
    db = SessionLocal()
    
    try:
        # Buscar todos os usuários que tiveram ingest
        ingest_logs = db.query(IngestLogModel).filter(
            IngestLogModel.status == "success"
        ).distinct(IngestLogModel.user_id).all()
        
        user_ids = list(set([log.user_id for log in ingest_logs]))
        
        print(f"📊 Building profiles for {len(user_ids)} users")
        
        success_count = 0
        
        for user_id in user_ids:
            success = await build_profile(user_id, db)
            if success:
                success_count += 1
            
            # Rate limiting para OpenAI
            await asyncio.sleep(0.5)
        
        print(f"✅ Profile building complete: {success_count}/{len(user_ids)} successful")
    
    finally:
        db.close()


async def event_consumer():
    """
    Consumer Kafka: processa eventos em tempo real
    
    Atualiza stats incrementalmente (opcional para MVP)
    """
    def handle_event(event_data: dict):
        """Handler para eventos"""
        db = SessionLocal()
        try:
            user_id = event_data.get("user_id")
            event_type = event_data.get("event_type")
            item_id = event_data.get("item_id")
            
            # Buscar perfil
            profile = db.query(ProfileModel).filter(
                ProfileModel.user_id == user_id
            ).first()
            
            if not profile:
                return
            
            # Atualizar stats incrementalmente
            if event_type == "click":
                profile.click_stats[item_id] = profile.click_stats.get(item_id, 0) + 1
            elif event_type == "impression":
                profile.impression_stats[item_id] = profile.impression_stats.get(item_id, 0) + 1
            
            profile.last_updated = datetime.utcnow()
            db.commit()
            
            print(f"📊 Updated profile for {user_id}: {event_type} on {item_id}")
        
        except Exception as e:
            print(f"❌ Error handling event: {e}")
            db.rollback()
        finally:
            db.close()
    
    # Consumir eventos
    event_bus.consume(
        topic=settings.KAFKA_TOPIC_EVENTS,
        group_id="profile-builder",
        handler=handle_event
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # Modo batch: constrói todos os perfis
        print("🚀 Running profile builder in BATCH mode")
        asyncio.run(build_all_profiles())
    else:
        # Modo consumer: processa eventos em tempo real
        print("🚀 Running profile builder in CONSUMER mode")
        asyncio.run(event_consumer())
