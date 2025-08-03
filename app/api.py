from fastapi import APIRouter, UploadFile, File, HTTPException, Path
from fastapi.responses import FileResponse
import uuid
import os
import tempfile
from typing import Dict, List
from io import BytesIO
import threading
from datetime import datetime
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
    files: List[UploadFile] = File(...),
    speaker_a_voice: str = settings.HOST_A_NAME,
    speaker_b_voice: str = settings.HOST_B_NAME,
):
    """
    Upload PDF files and initiate podcast generation.

    Args:
        files: List of PDF files to process
        speaker_a_voice: Voice ID for speaker A
        speaker_b_voice: Voice ID for speaker B

    Returns:
        Job information with status
    """
    # Validate that at least one file is provided
    if not files:
        logger.warning("No files provided")
        raise HTTPException(status_code=400, detail="At least one PDF file is required")

    # Read and validate all files
    file_contents = []
    for file in files:
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

        file_contents.append(content)

    # Create job ID
    job_id = str(uuid.uuid4())
    logger.info(f"Created new job: {job_id}")

    # Store job info
    jobs[job_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "result_file": None
    }

    # Start processing in a new thread
    threading.Thread(
        target=process_podcast_job,
        args=(job_id, file_contents, speaker_a_voice, speaker_b_voice),
        daemon=True
    ).start()

    logger.info(f"Job {job_id} started in background thread")

    return {
        "job_id": job_id,
        "status": "processing",
        "created_at": jobs[job_id]["created_at"]
    }

@router.get("/podcasts/status/{job_id}")
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

    return {
        "job_id": job_id,
        "status": job_info["status"],
        "progress": job_info["progress"],
        "result_url": job_info["result_file"] if job_info["result_file"] else None
    }

@router.get("/podcasts/download/{filename}")
async def download_podcast(filename: str = Path(..., title="Filename of the podcast to download")):
    """
    Download the generated podcast file.

    Args:
        filename: Filename of the podcast to download

    Returns:
        MP3 file response
    """
    # Construct the full path
    file_path = os.path.join(settings.AUDIO_STORAGE_PATH, filename)

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"Initiating download for file: {filename}")
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename=filename
    )

@router.get("/podcasts")
async def list_podcasts():
    """
    List all generated podcasts.

    Returns:
        List of podcast information including name, size, and creation date
    """
    logger.debug("Listing all podcast files")

    podcasts = []
    try:
        # Scan the audio storage directory
        if not os.path.exists(settings.AUDIO_STORAGE_PATH):
            logger.warning(f"Audio storage path does not exist: {settings.AUDIO_STORAGE_PATH}")
            return []

        for filename in os.listdir(settings.AUDIO_STORAGE_PATH):
            file_path = os.path.join(settings.AUDIO_STORAGE_PATH, filename)

            # Skip non-files and non-mp3 files
            if not os.path.isfile(file_path) or not filename.lower().endswith('.mp3'):
                continue

            # Get file stats
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            created_at = datetime.fromtimestamp(file_stat.st_ctime).isoformat()

            podcasts.append({
                "filename": filename,
                "size": file_size,
                "created_at": created_at
            })

        return podcasts

    except Exception as e:
        logger.error(f"Error listing podcasts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing podcasts")

def process_podcast_job(job_id: str, file_contents: List[bytes],
                      speaker_a_voice: str, speaker_b_voice: str):
    """
    Background task to process podcast generation for multiple PDFs.

    Args:
        job_id: Unique identifier for the job
        file_contents: List of PDF file contents
        speaker_a_voice: Voice ID for speaker A
        speaker_b_voice: Voice ID for speaker B
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            # Update job status
            logger.info(f"Starting processing for job: {job_id}")
            jobs[job_id]["status"] = "processing"
            jobs[job_id]["progress"] = 5  # Initial progress

            total_pdfs = len(file_contents)
            all_audio_files = []  # Will store all audio segments from all PDFs

            # Step 1: Extract text from all PDFs
            logger.info(f"Extracting text from all {total_pdfs} PDFs for job: {job_id}")
            text_contents = []
            progress_increment = 15 / total_pdfs
            for index, file_content in enumerate(file_contents):
                file_stream = BytesIO(file_content)
                logger.debug(f"Extracting text from PDF {index + 1}/{total_pdfs} for job: {job_id}")
                text_content = extract_text_from_pdf(file_stream)
                logger.debug(f"Successfully extracted text from PDF {index + 1}/{total_pdfs} for job: {job_id}")
                text_contents.append(text_content)
                jobs[job_id]["progress"] += progress_increment

            # Step 2: Generate podcast scripts with LLM for all PDFs
            logger.info(f"Generating podcast scripts for all {total_pdfs} PDFs for job: {job_id}")
            all_dialogues = []
            llm_client = LLMClient()
            progress_increment = 30 / total_pdfs
            for index, text_content in enumerate(text_contents):
                # Set intro/outro based on position
                intro = False
                outro = False
                if index == 0:  # First PDF
                    intro = True
                elif index == total_pdfs - 1:  # Last PDF
                    outro = True

                logger.debug(f"Generating script for PDF {index + 1}/{total_pdfs} for job: {job_id}")
                dialogue = llm_client.generate_podcast_script(
                    text_content,
                    speaker_a_voice,
                    speaker_b_voice,
                    intro,
                    outro,
                    tmpdirname)
                logger.debug(f"Successfully generated script for PDF {index + 1}/{total_pdfs} for job: {job_id}")
                all_dialogues.append(dialogue)
                jobs[job_id]["progress"] += progress_increment

            # Step 3: Generate audio segments with TTS for all PDFs
            logger.info(f"Generating audio segments for all {total_pdfs} PDFs for job: {job_id}")
            tts_client = TTSClient()
            progress_increment = 30 / total_pdfs
            for index, dialogue in enumerate(all_dialogues):
                logger.debug(f"Generating audio for PDF {index + 1}/{total_pdfs} for job: {job_id}")
                audio_files = tts_client.generate_audio_segments(
                    dialogue,
                    index,
                    speaker_a_voice,
                    speaker_b_voice,
                    tmpdirname
                )
                logger.debug(f"Successfully generated audio for PDF {index + 1}/{total_pdfs} for job: {job_id}")
                all_audio_files.extend(audio_files)
                jobs[job_id]["progress"] += progress_increment

            # Step 4: Stitch all audio segments into final output
            logger.info(f"Stitching all audio segments for job: {job_id}")
            stitcher = AudioStitcher()
            output_file = stitcher.stitch_audio_segments(
                all_audio_files, f"podcast_{job_id}.mp3"
            )
            logger.info(f"Successfully stitched all audio segments for job: {job_id}")

            # Update job status
            jobs[job_id]["result_file"] = output_file
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            logger.info(f"Job completed successfully: {job_id}")

        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)