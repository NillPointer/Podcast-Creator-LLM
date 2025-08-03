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
    while (true) {
      try {
        const response = await fetch(`/api/v1/podcasts/${jobId}`);
        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || 'Failed to get job status');
        }

        // Update progress bar
        const progress = result.progress || 0;
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;

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

        // Wait before next check
        await new Promise(resolve => setTimeout(resolve, 1000));

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
  }
});