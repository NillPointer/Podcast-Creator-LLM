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
  const podcastListContainer = document.getElementById('podcastListContainer');
  const podcastList = document.getElementById('podcastList');
  const arxivUrlsContainer = document.getElementById('arxivUrlsContainer');

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

  // Arxiv URL input field management
  function updateArxivUrlsUI() {
    const urlInputs = arxivUrlsContainer.querySelectorAll('.arxiv-url');
    const nonEmptyUrls = Array.from(urlInputs).filter(input => input.value.trim() !== '');

    // If all inputs have non-whitespace text, add another input
    if (nonEmptyUrls.length === urlInputs.length && urlInputs.length > 0) {
      addArxivUrlInput();
    }

    // If there are 2 or more empty inputs, remove the last one
    const emptyUrls = Array.from(urlInputs).filter(input => input.value.trim() === '');
    if (emptyUrls.length >= 2) {
      emptyUrls[emptyUrls.length - 1].parentElement.remove();
    }
  }

  function addArxivUrlInput() {
    const urlGroup = document.createElement('div');
    urlGroup.className = 'url-input-group';
    urlGroup.innerHTML = `
      <input type="text" class="arxiv-url" name="arxiv_urls" placeholder="" value="">
    `;
    arxivUrlsContainer.appendChild(urlGroup);

    // Add event listener to the new input
    urlGroup.querySelector('.arxiv-url').addEventListener('input', updateArxivUrlsUI);
  }

  // Initialize URL input field management
  arxivUrlsContainer.querySelector('.arxiv-url').addEventListener('input', updateArxivUrlsUI);

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

    // Append Arxiv URLs
    const arxivUrls = [];
    document.querySelectorAll('.arxiv-url').forEach(input => {
      const url = input.value.trim();
      if (url) {
        arxivUrls.push(url);
      }
    });
    arxivUrls.forEach(url => {
      formData.append('arxiv_urls', url);
    });

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
    const POLL_INTERVAL = 5000; // 5 second between polls

    while (true) {
      try {
        const response = await fetch(`/api/v1/podcasts/status/${jobId}`);
        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || 'Failed to get job status');
        }

        // Update UI with detailed status information
        updateProgressUI(result);

        if (result.status === 'completed') {
          // Show download link
          downloadLink.href = `/api/v1/podcasts/download/${result.result_file}`;
          resultContainer.style.display = 'block';
          progressContainer.style.display = 'none';
          submitBtn.disabled = false;
          submitBtn.textContent = 'Create Podcast';
          await fetchPodcastList();
          break;
        } else if (result.status === 'failed') {
          throw new Error(result.error || 'Processing failed');
        }
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

  // Function to format file size for display
  function formatFileSizeForDisplay(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Function to format date for display
  function formatDateForDisplay(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  }

  // Function to fetch and display podcast list
  async function fetchPodcastList() {
    try {
      const response = await fetch('/api/v1/podcasts');
      const podcasts = await response.json();

      if (!response.ok) {
        throw new Error('Failed to fetch podcast list');
      }

      displayPodcastList(podcasts);
    } catch (error) {
      console.error('Error fetching podcast list:', error);
      podcastListContainer.style.display = 'block';
      podcastList.innerHTML = '<p class="error">Failed to load podcast list. Please try again later.</p>';
    }
  }

  // Function to display podcast list
  function displayPodcastList(podcasts) {
    podcastList.innerHTML = '';

    if (podcasts.length === 0) {
      podcastList.innerHTML = '<p class="no-podcasts">No podcasts available. Create one by uploading PDF files.</p>';
      return;
    }

    podcasts.forEach(podcast => {
      const podcastItem = document.createElement('div');
      podcastItem.className = 'podcast-item';

      podcastItem.innerHTML = `
          <div class="podcast-info">
            <div class="podcast-name">${podcast.filename}</div>
            <div class="podcast-details">
              <span class="podcast-size">${formatFileSizeForDisplay(podcast.size)}</span>
              <span class="podcast-date">${formatDateForDisplay(podcast.created_at)}</span>
            </div>
          </div>
          <div class="podcast-controls">
            <button class="podcast-play" data-filename="${encodeURIComponent(podcast.filename)}" title="Play">
              <i class="play-icon">▶</i>
            </button>
            <a class="podcast-download" href="/api/v1/podcasts/download/${encodeURIComponent(podcast.filename)}" download>
              <i class="download-icon">⬇</i>
            </a>
            <button class="podcast-delete" data-filename="${encodeURIComponent(podcast.filename)}">
              <i class="delete-icon">×</i>
            </button>
          </div>
        `;

      podcastList.appendChild(podcastItem);
    });

    podcastListContainer.style.display = 'block';

    // Add event listeners for delete buttons
    document.querySelectorAll('.podcast-delete').forEach(button => {
      button.addEventListener('click', handleDeleteButtonClick);
    });
    // Add event listeners for play buttons
    document.querySelectorAll('.podcast-play').forEach(button => {
      button.addEventListener('click', handlePlayButtonClick);
    });
  }

  // Function to handle play button clicks
  function handlePlayButtonClick() {
    const filename = this.getAttribute('data-filename');

    // Check if there's already an active audio element
    const existingAudio = document.querySelector('audio[data-filename]');
    if (existingAudio) {
      // If clicking the same button, pause/play toggle
      if (existingAudio.getAttribute('data-filename') === filename) {
        if (existingAudio.paused) {
          existingAudio.play();
        } else {
          existingAudio.pause();
        }
        return;
      } else {
        // If playing a different podcast, stop the current one
        existingAudio.pause();
        existingAudio.remove();
      }
    }

    // Create new audio element
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.style.display = 'block';
    audio.style.marginTop = '10px';
    audio.style.width = '100%';
    audio.setAttribute('data-filename', filename);

    // Create source element
    const source = document.createElement('source');
    source.src = `/api/v1/podcasts/download/${filename}`;
    source.type = 'audio/mpeg';

    // Append source to audio
    audio.appendChild(source);

    // Insert audio element before the podcast item
    this.parentElement.parentElement.insertBefore(audio, this.parentElement);

    // Play the audio
    audio.play();

    // Add event listeners for play/pause and time updates
    audio.addEventListener('play', () => {
      updatePlayButtonState(this, true);
    });

    audio.addEventListener('pause', () => {
      updatePlayButtonState(this, false);
    });

    audio.addEventListener('seeking', () => {
      updatePlayButtonState(this, true);
    });

    audio.addEventListener('ended', () => {
      updatePlayButtonState(this, false);
    });
  }

  // Function to update play/pause button state
  function updatePlayButtonState(button, isPlaying) {
    const icon = button.querySelector('.play-icon');
    if (icon) {
      icon.textContent = isPlaying ? '⏸' : '▶';
      button.setAttribute('title', isPlaying ? 'Pause' : 'Play');
    }

    // Remove audio element when paused
    if (!isPlaying) {
      const filename = button.getAttribute('data-filename');
      const audio = document.querySelector(`audio[data-filename="${filename}"]`);
      if (audio) {
        audio.pause();
        audio.remove();
      }
    }
  }

  // Function to handle delete button clicks
  async function handleDeleteButtonClick() {
    const filename = this.getAttribute('data-filename');

    try {
      const response = await fetch(`/api/v1/podcasts/delete/${filename}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || 'Failed to delete podcast');
      }

      // Refresh the podcast list
      await fetchPodcastList();

      // Show success message
      statusMessage.textContent = 'Podcast deleted successfully!';
      statusMessage.className = 'success';
      statusMessage.style.display = 'block';

      setTimeout(() => {
        statusMessage.style.display = 'none';
      }, 3000);

    } catch (error) {
      console.error('Error deleting podcast:', error);
      statusMessage.textContent = `Error: ${error.message}`;
      statusMessage.className = 'error';
      statusMessage.style.display = 'block';
    }
  }

  // Initial fetch of podcast list when page loads
  fetchPodcastList();
});