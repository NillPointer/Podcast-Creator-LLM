// script.js
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('uploadForm');
  const statusMessage = document.getElementById('statusMessage');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');
  const resultContainer = document.getElementById('resultContainer');
  const downloadLink = document.getElementById('downloadLink');
  const submitBtn = document.getElementById('submitBtn');
  const dropArea = document.getElementById('dropArea');
  const pdfFilesInput = document.getElementById('pdfFiles');
  const selectedFilesContainer = document.getElementById('selectedFiles');

  // Keep track of selected files
  let selectedFiles = [];

  // Set up drag and drop events
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
  });

  function highlight() {
    dropArea.classList.add('highlight');
  }

  function unhighlight() {
    dropArea.classList.remove('highlight');
  }

  // Handle dropped files
  dropArea.addEventListener('drop', handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
  }

  // Handle selected files via click
  pdfFilesInput.addEventListener('change', function () {
    handleFiles(this.files);
  });

  // Click on drop area to trigger file selection
  dropArea.addEventListener('click', function () {
    pdfFilesInput.click();
  });

  function handleFiles(files) {
    // Filter for PDF files only
    const pdfFiles = Array.from(files).filter(file => file.type === 'application/pdf');

    // Add to selected files array
    pdfFiles.forEach(file => {
      if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
        selectedFiles.push(file);
      }
    });

    // Update UI to show selected files
    updateSelectedFilesUI();
  }

  function updateSelectedFilesUI() {
    selectedFilesContainer.innerHTML = '';

    if (selectedFiles.length === 0) {
      selectedFilesContainer.innerHTML = '<p class="no-files">No files selected</p>';
      return;
    }

    selectedFiles.forEach((file, index) => {
      const fileElement = document.createElement('div');
      fileElement.className = 'selected-file';
      fileElement.innerHTML = `
        <span class="file-name">${file.name}</span>
        <span class="file-size">(${formatFileSize(file.size)})</span>
        <button class="remove-file" data-index="${index}">×</button>
      `;
      selectedFilesContainer.appendChild(fileElement);
    });

    // Add event listeners to remove buttons
    document.querySelectorAll('.remove-file').forEach(button => {
      button.addEventListener('click', function () {
        const index = parseInt(this.getAttribute('data-index'));
        removeFile(index);
      });
    });
  }

  function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateSelectedFilesUI();
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    // Reset UI
    statusMessage.style.display = 'none';
    progressContainer.style.display = 'block';
    resultContainer.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    // Create FormData with selected files
    const formData = new FormData();

    // Append all selected files
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });

    // Append other form fields
    formData.append('speaker_a_voice', document.getElementById('speakerAVoice').value);
    formData.append('speaker_b_voice', document.getElementById('speakerBVoice').value);

    try {
      // Upload file and start processing
      const response = await fetch('/api/v1/podcasts', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || 'Failed to create podcast');
      }

      // Show progress updates
      await monitorProgress(result.job_id);

    } catch (error) {
      console.error('Error:', error);
      statusMessage.textContent = `Error: ${error.message}`;
      statusMessage.className = 'error';
      statusMessage.style.display = 'block';
      progressContainer.style.display = 'none';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create Podcast';
    }
  });

  async function monitorProgress(jobId) {
    const MAX_POLL_ATTEMPTS = 180; // 3 minute max polling time per status
    let pollAttempts = 0;
    const POLL_INTERVAL = 1000; // 1 second between polls

    // Store previous status to detect changes
    let previousStatus = null;

    while (pollAttempts < MAX_POLL_ATTEMPTS) {
      try {
        const response = await fetch(`/api/v1/podcasts/${jobId}`);
        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || 'Failed to get job status');
        }

        // Update UI with detailed status information
        updateProgressUI(result);

        // Check for status changes
        if (previousStatus !== result.status) {
          console.log(`Job status changed to: ${result.status}`);
          previousStatus = result.status;
          pollAttempts = 0
        }

        if (result.status === 'completed') {
          // Show download link
          downloadLink.href = `/api/v1/podcasts/${jobId}/download`;
          resultContainer.style.display = 'block';
          progressContainer.style.display = 'none';
          submitBtn.disabled = false;
          submitBtn.textContent = 'Create Podcast';
          break;
        } else if (result.status === 'failed') {
          throw new Error(result.error || 'Processing failed');
        }

        // Increment poll attempts and wait before next check
        pollAttempts++;
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));

      } catch (error) {
        console.error('Error monitoring progress:', error);
        statusMessage.textContent = `Error: ${error.message}`;
        statusMessage.className = 'error';
        statusMessage.style.display = 'block';
        progressContainer.style.display = 'none';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Podcast';
        break;
      }
    }

    // If we exit the loop without completion, show a timeout message
    if (pollAttempts >= MAX_POLL_ATTEMPTS) {
      statusMessage.textContent = 'Processing timed out. Please try again later.';
      statusMessage.className = 'warning';
      statusMessage.style.display = 'block';
      progressContainer.style.display = 'none';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create Podcast';
    }
  }

  function updateProgressUI(result) {
    // Update progress bar
    let progress = result.progress || 0;

    // Ensure progress is a valid number between 0 and 100
    progress = Math.min(100, Math.max(0, parseFloat(progress) || 0));

    // Update UI with progress
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${Math.round(progress)}%`;

    // Update status message with more detailed information
    let statusMessageText = '';
    switch (result.status) {
      case 'queued':
        statusMessageText = 'Job queued for processing...';
        break;
      case 'processing':
        statusMessageText = `Processing: ${result.current_step || 'Starting'}...`;
        break;
      case 'completed':
        statusMessageText = 'Processing completed successfully!';
        break;
      case 'failed':
        statusMessageText = 'Processing failed.';
        break;
      default:
        statusMessageText = `Status: ${result.status}`;
    }

    // Update the status message element
    if (statusMessage) {
      statusMessage.textContent = statusMessageText;
      statusMessage.className = result.status === 'failed' ? 'error' :
        result.status === 'completed' ? 'success' :
          'info';
      statusMessage.style.display = 'block';
    }
  }
});