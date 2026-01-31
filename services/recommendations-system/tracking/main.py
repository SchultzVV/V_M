"""
Tracking Service - Rastreia eventos (impressões, cliques)
"""
from fastapi import FastAPI, HTTPException
from datetime import datetime
import uuid

from shared.schemas import TrackingEvent, TrackingResponse, EventType
from shared.kafka_client import event_bus

app = FastAPI(title="Tracking Service", version="1.0.0")


@app.on_event("startup")
async def startup_event():
    """Inicializa serviço"""
    print("✅ Tracking Service started")


@app.post("/track", response_model=TrackingResponse)
async def track_event(event: TrackingEvent):
    """
    Rastreia evento do usuário
    
    Tipos de eventos:
    - IMPRESSION: Item foi exibido
    - CLICK: Item foi clicado
    - PURCHASE: Item foi comprado (futuro)
    
    Eventos são publicados no Kafka para processamento assíncrono
    """
    try:
        event_id = str(uuid.uuid4())
        
        # Preparar mensagem
        event_message = {
            "event_id": event_id,
            "user_id": event.user_id,
            "event_type": event.event_type.value,
            "item_id": event.item_id,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata or {}
        }
        
        # Publicar no Kafka
        success = event_bus.publish_event(event_message)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to publish event to Kafka"
            )
        
        return TrackingResponse(
            event_id=event_id,
            status="tracked"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tracking error: {str(e)}"
        )


@app.post("/track/batch")
async def track_batch_events(events: list[TrackingEvent]):
    """
    Rastreia múltiplos eventos em batch
    
    Útil para rastrear múltiplas impressões de uma vez
    """
    try:
        results = []
        
        for event in events:
            event_id = str(uuid.uuid4())
            
            event_message = {
                "event_id": event_id,
                "user_id": event.user_id,
                "event_type": event.event_type.value,
                "item_id": event.item_id,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata or {}
            }
            
            success = event_bus.publish_event(event_message)
            
            results.append({
                "event_id": event_id,
                "status": "tracked" if success else "failed"
            })
        
        return {
            "total": len(events),
            "results": results
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch tracking error: {str(e)}"
        )


@app.get("/track/stats")
async def get_tracking_stats():
    """
    Retorna estatísticas de tracking
    
    TODO: Implementar contadores em Redis
    """
    return {
        "status": "not_implemented",
        "message": "Stats will be implemented in phase 2"
    }


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "tracking"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
