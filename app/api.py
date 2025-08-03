from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
import uuid
import os
from typing import Dict, List
from io import BytesIO
from app.pdf_processor import extract_text_from_pdf, validate_pdf_file
from app.llm_client import LLMClient
from app.tts_client import TTSClient
from app.audio_stitcher import AudioStitcher
from app.config.settings import settings
from app.logger import setup_logger

router = APIRouter()

# Setup logging
logger = setup_logger('podcast_creator_api')

# In-memory storage for job tracking (in production, use a database)
jobs = {}

@router.post("/podcasts")
async def create_podcast(
    file: UploadFile = File(...),
    speaker_a_voice: str = settings.HOST_A_NAME,
    speaker_b_voice: str = settings.HOST_B_NAME,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Upload a PDF file and initiate podcast generation.

    Args:
        file: PDF file to process
        speaker_a_voice: Voice ID for speaker A
        speaker_b_voice: Voice ID for speaker B

    Returns:
        Job information with status
    """
    # Validate file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file content
    content = await file.read()
    logger.info("Got content")

    # Validate PDF
    if not validate_pdf_file(content):
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    # Create job ID
    job_id = str(uuid.uuid4())

    # Store job info
    from datetime import datetime
    jobs[job_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "result_file": None
    }

    # Process in background
    background_tasks.add_task(process_podcast_job, job_id, content, speaker_a_voice, speaker_b_voice)

    logger.info("Added to background tasks")

    return {
        "job_id": job_id,
        "status": "processing",
        "created_at": jobs[job_id]["created_at"]
    }

@router.get("/podcasts/{job_id}")
async def get_podcast_status(job_id: str):
    """
    Get the status of a podcast generation job.

    Args:
        job_id: Unique identifier for the job

    Returns:
        Job status information
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = jobs[job_id]

    # Don't log status checks as they are too noisy
    # Status checks are intentionally not logged to reduce noise

    return {
        "job_id": job_id,
        "status": job_info["status"],
        "progress": job_info["progress"],
        "result_url": job_info["result_file"] if job_info["result_file"] else None
    }

@router.get("/podcasts/{job_id}/download")
async def download_podcast(job_id: str):
    """
    Download the generated podcast file.

    Args:
        job_id: Unique identifier for the job

    Returns:
        MP3 file response
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = jobs[job_id]

    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Podcast not ready for download")

    if not job_info["result_file"]:
        raise HTTPException(status_code=404, detail="Result file not found")

    if not os.path.exists(job_info["result_file"]):
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        job_info["result_file"],
        media_type="audio/mpeg",
        filename=f"podcast_{job_id}.mp3"
    )

@router.get("/podcasts")
async def list_podcasts():
    """
    List all podcast generation jobs.

    Returns:
        List of job information
    """
    return [
        {
            "job_id": job_id,
            "status": job_info["status"],
            "created_at": job_info["created_at"],
            "updated_at": job_info["updated_at"]
        }
        for job_id, job_info in jobs.items()
    ]

async def process_podcast_job(job_id: str, file_content: bytes,
                            speaker_a_voice: str, speaker_b_voice: str):
    """
    Background task to process podcast generation.

    Args:
        job_id: Unique identifier for the job
        file_content: PDF file content
        speaker_a_voice: Voice ID for speaker A
        speaker_b_voice: Voice ID for speaker B
    """
    try:
        # Update job status
        logger.info("processing job")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10

        # Step 1: Extract text from PDF
        file_stream = BytesIO(file_content)
        logger.info("extracing pdf content")
        text_content = extract_text_from_pdf(file_stream)
        logger.info("extraced Pdf content")
        jobs[job_id]["progress"] = 25

        # Step 2: Generate podcast script with LLM
        logger.info("Init LLM Client")
        llm_client = LLMClient()
        logger.info("Have LLM Client, genearting script")
        dialogue = llm_client.generate_podcast_script(text_content, speaker_a_voice, speaker_b_voice)
        logger.info("Generated Script")
        jobs[job_id]["progress"] = 50

        # Step 3: Generate audio segments with TTS
        tts_client = TTSClient()
        audio_files = tts_client.generate_audio_segments(
            dialogue, speaker_a_voice, speaker_b_voice
        )
        jobs[job_id]["progress"] = 75

        # Step 4: Stitch audio segments
        stitcher = AudioStitcher()
        output_file = stitcher.stitch_audio_segments(
            audio_files, f"podcast_{job_id}.mp3"
        )
        jobs[job_id]["progress"] = 90

        # Step 5: Cleanup temporary files
        stitcher.cleanup_temp_files(audio_files)
        jobs[job_id]["progress"] = 100

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result_file"] = output_file

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"Error processing job {job_id}: {str(e)}")