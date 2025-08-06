from fastapi import APIRouter, UploadFile, File, HTTPException, Path, Form
from fastapi.responses import FileResponse
import uuid
import os
import tempfile
from typing import Dict, List, Optional
from io import BytesIO
import threading
from datetime import datetime
from app.pdf_processor import PDFProcessor
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
    files: Optional[List[UploadFile]] = File(None),
    arxiv_urls: Optional[List[str]] = Form(None)
):
    """
    Upload PDF files and Arxiv URLs to initiate podcast generation.

    Args:
        files: List of PDF files to process
        arxiv_urls: List of Arxiv URLs to process

    Returns:
        Job information with status
    """
    # Validate that at least one file or URL is provided
    if not files and not arxiv_urls:
        logger.warning("No files or URLs provided")
        raise HTTPException(status_code=400, detail="At least one PDF file or Arxiv URL is required")

    # Read and validate all files
    file_contents = []
    if files:
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

            file_contents.append(content)

    # Validate Arxiv URLs
    valid_arxiv_urls = []
    if arxiv_urls:
        for url in arxiv_urls:
            if not url.strip():
                continue
            if not url.startswith("https://arxiv.org/pdf/"):
                logger.warning(f"Invalid Arxiv URL format: {url}")
                raise HTTPException(status_code=400, detail="Only Arxiv PDF URLs are supported")
            valid_arxiv_urls.append(url.strip())

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
        args=(job_id, file_contents, valid_arxiv_urls),
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
        "result_file": job_info["result_file"] if job_info["result_file"] else None
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

@router.delete("/podcasts/delete/{filename}")
async def delete_podcast(filename: str = Path(..., title="Filename of the podcast to delete")):
    """
    Delete a generated podcast file.

    Args:
        filename: Filename of the podcast to delete

    Returns:
        Success message if file was deleted, 404 if file doesn't exist
    """
    # Construct the full path
    file_path = os.path.join(settings.AUDIO_STORAGE_PATH, filename)

    if not os.path.exists(file_path):
        logger.warning(f"File not found for deletion: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")

    try:
        os.remove(file_path)
        logger.info(f"Successfully deleted file: {filename}")
        return {"detail": "File deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting file")

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

        # Sort podcasts by created_at in descending order (newest first)
        sorted_podcasts = sorted(podcasts, key=lambda x: x['created_at'], reverse=True)
        return sorted_podcasts

    except Exception as e:
        logger.error(f"Error listing podcasts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing podcasts")

def process_podcast_job(job_id: str, file_contents: List[bytes], arxiv_urls: List[str]):
    """
    Background task to process podcast generation for PDFs and Arxiv URLs.

    Args:
        job_id: Unique identifier for the job
        file_contents: List of PDF file contents
        arxiv_urls: List of Arxiv URLs
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        try:
            # Update job status
            logger.info(f"Starting processing for job: {job_id}")
            jobs[job_id]["status"] = "processing"
            jobs[job_id]["progress"] = 0  # Initial progress

            total_sources = len(file_contents) + len(arxiv_urls)
            if total_sources == 0:
                jobs[job_id]["status"] = "failed"
                raise ValueError("No valid sources provided for processing")

            all_audio_files = []  # Will store all audio segments from all sources

            # Initialize PDF processor
            pdf_processor = PDFProcessor()

            # Step 1: Extract text from all PDFs and Arxiv URLs
            logger.info(f"Extracting text from all {total_sources} sources for job: {job_id}")
            text_contents = []
            progress_increment = 15 / total_sources

            # Process PDF files
            for index, file_content in enumerate(file_contents):
                file_stream = BytesIO(file_content)
                logger.debug(f"Extracting text from PDF {index + 1}/{total_sources} for job: {job_id}")
                text_content = pdf_processor.extract_text_from_pdf(file_stream)
                logger.debug(f"Successfully extracted text from PDF {index + 1}/{total_sources} for job: {job_id}")
                text_contents.append(text_content)
                jobs[job_id]["progress"] += progress_increment

            # Process Arxiv URLs
            for index, url in enumerate(arxiv_urls):
                logger.debug(f"Extracting text from Arxiv URL {index + 1}/{total_sources} for job: {job_id}")
                text_content = pdf_processor.extract_text_from_arxiv(url)
                logger.debug(f"Successfully extracted text from Arxiv URL {index + 1}/{total_sources} for job: {job_id}")
                text_contents.append(text_content)
                jobs[job_id]["progress"] += progress_increment

            # Progress 15% Point

            # Step 2: Generate podcast scripts with LLM for all sources
            logger.info(f"Generating podcast scripts for all {total_sources} sources for job: {job_id}")
            llm_client = LLMClient()
            all_dialogues = llm_client.generate_podcast_script(text_contents, jobs[job_id])
            jobs[job_id]["progress"] = 55

            # Step 3: Generate audio segments with TTS for all sources
            logger.info(f"Generating audio segments for all {total_sources} sources for job: {job_id}")
            tts_client = TTSClient()
            audio_files = tts_client.generate_audio_segments(
                all_dialogues,
                jobs[job_id],
                tmpdirname
            )
            logger.debug(f"Successfully generated audio for source {index + 1}/{total_sources} for job: {job_id}")
            all_audio_files.extend(audio_files)
            jobs[job_id]["progress"] = 95

            # Step 4: Stitch all audio segments into final output
            logger.info(f"Stitching all audio segments for job: {job_id}")
            stitcher = AudioStitcher()
            output_filename = f"podcast_{datetime.utcnow().strftime('%Y%m%d%H%M')}.mp3"
            output_file = stitcher.stitch_audio_segments(
                all_audio_files, output_filename
            )
            logger.info(f"Successfully stitched all audio segments for job: {job_id}")

            # Update job status
            jobs[job_id]["result_file"] = output_filename
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            logger.info(f"Job completed successfully: {job_id}")

        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["detail"] = str(e)
            logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)