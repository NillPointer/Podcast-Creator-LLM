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
        logger.warning(f"File too large: {file.size} bytes > {settings.MAX_FILE_SIZE} bytes")
        raise HTTPException(status_code=413, detail="File too large")

    # Validate file type
    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file content
    content = await file.read()
    logger.debug(f"Successfully read file content. Size: {len(content)} bytes")

    # Validate PDF
    if not validate_pdf_file(content):
        logger.warning("Invalid PDF file detected")
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    # Create job ID
    job_id = str(uuid.uuid4())
    logger.info(f"Created new job: {job_id}")

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

    logger.info(f"Job {job_id} added to background processing queue")

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
        logger.warning(f"Job not found: {job_id}")
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
        logger.warning(f"Job not found during download: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")

    job_info = jobs[job_id]

    if job_info["status"] != "completed":
        logger.warning(f"Attempt to download incomplete job: {job_id} (status: {job_info['status']})")
        raise HTTPException(status_code=400, detail="Podcast not ready for download")

    if not job_info["result_file"]:
        logger.warning(f"Result file missing for job: {job_id}")
        raise HTTPException(status_code=404, detail="Result file not found")

    if not os.path.exists(job_info["result_file"]):
        logger.warning(f"Result file not found on disk: {job_info['result_file']}")
        raise HTTPException(status_code=404, detail="Result file not found")

    logger.info(f"Initiating download for completed job: {job_id}")
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
    logger.debug("Listing all podcast jobs")
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
        logger.info(f"Starting processing for job: {job_id}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 10

        # Step 1: Extract text from PDF
        file_stream = BytesIO(file_content)
        logger.debug(f"Extracting text from PDF for job: {job_id}")
        text_content = extract_text_from_pdf(file_stream)
        logger.debug(f"Successfully extracted text from PDF for job: {job_id}")
        jobs[job_id]["progress"] = 25

        # Step 2: Generate podcast script with LLM
        logger.info(f"Generating podcast script for job: {job_id}")
        llm_client = LLMClient()
        dialogue = llm_client.generate_podcast_script(text_content, speaker_a_voice, speaker_b_voice)
        logger.info(f"Successfully generated podcast script for job: {job_id}")
        jobs[job_id]["progress"] = 50

        # Step 3: Generate audio segments with TTS
        logger.info(f"Generating audio segments for job: {job_id}")
        tts_client = TTSClient()
        audio_files = tts_client.generate_audio_segments(
            dialogue, speaker_a_voice, speaker_b_voice
        )
        logger.info(f"Successfully generated audio segments for job: {job_id}")
        jobs[job_id]["progress"] = 75

        # Step 4: Stitch audio segments
        logger.info(f"Stitching audio segments for job: {job_id}")
        stitcher = AudioStitcher()
        output_file = stitcher.stitch_audio_segments(
            audio_files, f"podcast_{job_id}.mp3"
        )
        logger.info(f"Successfully stitched audio segments for job: {job_id}")
        jobs[job_id]["progress"] = 90

        # Step 5: Cleanup temporary files
        logger.debug(f"Cleaning up temporary files for job: {job_id}")
        stitcher.cleanup_temp_files(audio_files)
        jobs[job_id]["progress"] = 100

        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result_file"] = output_file
        logger.info(f"Job completed successfully: {job_id}")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)