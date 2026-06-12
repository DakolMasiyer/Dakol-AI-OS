import uuid
from typing import Any
from core.workflows import WorkflowEngine
from core.workflow_policy import WorkflowPolicyEngine
from workflows.media_pipelines import create_publishing_job

def create_worldcup_generation_workflow(app_id: str, workflow_id: str = None) -> WorkflowEngine:
    if not workflow_id:
        workflow_id = str(uuid.uuid4())
        
    policy = WorkflowPolicyEngine({
        "GENERATE": ["PUBLISH", "COMPLETED"],
        "PUBLISH": ["COMPLETED"],
        "COMPLETED": []
    })
    
    engine = WorkflowEngine(app_id, workflow_id, policy, "GENERATE")
    
    def generate_stage(payload: dict[str, Any]) -> dict[str, Any]:
        from skills.worldcup_skill import generate_worldcup_content
        res = generate_worldcup_content(
            match_id=payload["match_id"],
            content_type=payload.get("content_type", "twitter_thread"),
            user_id=payload.get("user_id", "anonymous"),
            brand_profile=payload.get("brand_profile")
        )
        payload["generation_result"] = res
        next_stage = "PUBLISH" if payload.get("auto_publish") else "COMPLETED"
        return {"status": "success", "result": res, "next_stage": next_stage}

    def publish_stage(payload: dict[str, Any]) -> dict[str, Any]:
        job = create_publishing_job(
            asset_id=workflow_id,
            platform=payload.get("platform", "twitter"),
            payload=payload.get("generation_result", {})
        )
        return {"status": "success", "publishing_job": job, "next_stage": "COMPLETED"}

    engine.register_stage("GENERATE", generate_stage)
    engine.register_stage("PUBLISH", publish_stage)
    
    return engine


def create_listening_farm_ingestion_workflow(app_id: str, workflow_id: str = None) -> WorkflowEngine:
    if not workflow_id:
        workflow_id = str(uuid.uuid4())

    policy = WorkflowPolicyEngine({
        "INGEST": ["EVALUATE", "COMPLETED"],
        "EVALUATE": ["COMPLETED"],
        "COMPLETED": []
    })

    engine = WorkflowEngine(app_id, workflow_id, policy, "INGEST")

    def ingest_stage(payload: dict[str, Any]) -> dict[str, Any]:
        # Track metadata and audio URL is received
        track_id = payload.get("track_id", str(uuid.uuid4()))
        payload["track_id"] = track_id
        return {"status": "success", "next_stage": "EVALUATE"}

    def evaluate_stage(payload: dict[str, Any]) -> dict[str, Any]:
        from farm.listener_pipeline import process_uploaded_track
        res = process_uploaded_track(
            track_id=payload["track_id"],
            audio_url=payload["audio_url"],
            synthetic=payload.get("synthetic", False)
        )
        payload["evaluation_result"] = res
        return {"status": "success", "result": res, "next_stage": "COMPLETED"}

    engine.register_stage("INGEST", ingest_stage)
    engine.register_stage("EVALUATE", evaluate_stage)

    return engine


def create_syncmaster_submission_workflow(app_id: str, workflow_id: str = None) -> WorkflowEngine:
    if not workflow_id:
        workflow_id = str(uuid.uuid4())

    policy = WorkflowPolicyEngine({
        "SUBMIT": ["GENERATE_RECOMMENDATION"],
        "GENERATE_RECOMMENDATION": ["HUMAN_REVIEW"],
        "HUMAN_REVIEW": ["EXPORT", "COMPLETED"],
        "EXPORT": ["COMPLETED"],
        "COMPLETED": []
    })

    engine = WorkflowEngine(app_id, workflow_id, policy, "SUBMIT")

    def submit_stage(payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "GENERATE_RECOMMENDATION"}

    def generate_rec_stage(payload: dict[str, Any]) -> dict[str, Any]:
        # Mock recommendation generation
        payload["recommendation"] = {"sync_fit": "high", "score": 95}
        return {"status": "success", "next_stage": "HUMAN_REVIEW"}

    def human_review_stage(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload.get("approved"):
            return {"status": "WAITING_FOR_APPROVAL", "next_stage": "HUMAN_REVIEW"}
        
        # User approved
        return {"status": "success", "next_stage": "EXPORT"}

    def export_stage(payload: dict[str, Any]) -> dict[str, Any]:
        job = create_publishing_job(
            asset_id=workflow_id,
            platform="syncmaster_export",
            payload=payload.get("recommendation", {})
        )
        return {"status": "success", "export_job": job, "next_stage": "COMPLETED"}

    engine.register_stage("SUBMIT", submit_stage)
    engine.register_stage("GENERATE_RECOMMENDATION", generate_rec_stage)
    engine.register_stage("HUMAN_REVIEW", human_review_stage)
    engine.register_stage("EXPORT", export_stage)

    return engine
