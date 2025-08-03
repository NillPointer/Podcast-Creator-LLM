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

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    // Reset UI
    statusMessage.style.display = 'none';
    progressContainer.style.display = 'block';
    resultContainer.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    const formData = new FormData(form);

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
      statusMessage.className = 'success';
      statusMessage.style.display = 'block';
      progressContainer.style.display = 'none';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Create Podcast';
    }
  });

  async function monitorProgress(jobId) {
    const MAX_POLL_ATTEMPTS = 60; // 1 minute max polling time
    let pollAttempts = 0;
    const POLL_INTERVAL = 1000; // 1 second between polls

    while (pollAttempts < MAX_POLL_ATTEMPTS) {
      try {
        const response = await fetch(`/api/v1/podcasts/${jobId}`);
        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || 'Failed to get job status');
        }

        // Validate and update progress bar
        let progress = result.progress || 0;

        // Ensure progress is a valid number between 0 and 100
        progress = Math.min(100, Math.max(0, parseFloat(progress) || 0));

        // Update UI with progress
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${Math.round(progress)}%`;

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
});