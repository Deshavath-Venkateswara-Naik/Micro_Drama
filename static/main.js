/**
 * Microdrama AI - Professional Cinematic Intelligence
 * Main Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const uploadForm = document.getElementById('upload-form');
    const processingZone = document.getElementById('processing-zone');
    const resultsZone = document.getElementById('results-zone');
    
    const statusText = document.getElementById('status-text');
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    const currentLayerText = document.getElementById('current-layer');
    
    const seriesContainer = document.getElementById('series-container');
    const seriesTemplate = document.getElementById('series-template');
    const episodeTemplate = document.getElementById('episode-template');
    
    // Handle File Selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleUpload(e.target.files[0]);
        }
    });

    // Handle Drag and Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            handleUpload(e.dataTransfer.files[0]);
        }
    });

    async function handleUpload(file) {
        const genre = document.getElementById('genre-input').value;
        const partitionMode = document.getElementById('mode-toggle').checked;

        // Transition UI
        uploadForm.classList.add('hidden');
        processingZone.classList.remove('hidden');
        resultsZone.classList.add('hidden');

        const formData = new FormData();
        formData.append('video', file);
        formData.append('genre', genre);
        formData.append('partition_mode', partitionMode);

        try {
            const response = await fetch('/api/v1/process', {
                method: 'POST',
                body: formData
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        updateProgress(data);
                        if (data.result) {
                            renderResults(data.result);
                        }
                    } catch (e) {
                        console.error("JSON Parse Error", line);
                    }
                }
            }
        } catch (error) {
            console.error("Upload Error", error);
            statusText.innerText = "Error: Pipeline Interrupted";
            statusText.style.color = "var(--accent)";
        }
    }

    function updateProgress(data) {
        if (data.status) {
            statusText.innerText = data.status;
            
            // Extract layer number from status if present
            const layerMatch = data.status.match(/Layer (\d)/);
            if (layerMatch) {
                currentLayerText.innerText = `Layer ${layerMatch[1]}/6`;
            }
        }
        
        if (data.progress) {
            const prog = data.progress;
            progressBar.style.width = `${prog}%`;
            progressPercentage.innerText = `${prog}%`;
        }

        if (data.error) {
            statusText.innerText = `Error: ${data.error}`;
            statusText.style.color = "var(--accent)";
        }
    }

    function renderResults(data) {
        processingZone.classList.add('hidden');
        resultsZone.classList.remove('hidden');
        
        document.getElementById('display-job-id').innerText = data.job_id.substring(0, 8) + '...';
        
        const seriesList = data.series || [];
        document.getElementById('total-series').innerText = seriesList.length;
        
        let totalEpisodesCount = 0;
        seriesContainer.innerHTML = '';

        seriesList.forEach(series => {
            const seriesClone = seriesTemplate.content.cloneNode(true);
            seriesClone.querySelector('.series-title').innerText = series.series_title;
            
            const grid = seriesClone.querySelector('.storyboard-grid');
            const episodes = series.episodes || [];
            totalEpisodesCount += episodes.length;

            episodes.forEach(ep => {
                const epClone = episodeTemplate.content.cloneNode(true);
                
                // Video Handling
                const video = epClone.querySelector('video');
                video.src = ep.video_url;
                
                // Card Media Overlay click to play
                const mediaContainer = epClone.querySelector('.card-media');
                mediaContainer.addEventListener('click', () => {
                    if (video.paused) {
                        video.play();
                        mediaContainer.querySelector('.video-overlay').style.opacity = '0';
                    } else {
                        video.pause();
                        mediaContainer.querySelector('.video-overlay').style.opacity = '1';
                    }
                });

                epClone.querySelector('.timestamp-tag').innerText = `${ep.start_time} - ${ep.end_time}`;
                epClone.querySelector('.ep-num').innerText = `EPISODE ${ep.episode_number.toString().padStart(2, '0')}`;
                epClone.querySelector('.score-value').innerText = ep.drama_score || '--';
                epClone.querySelector('.clip-title').innerText = ep.title || 'Narrative Segment';
                epClone.querySelector('.clip-description').innerText = ep.hook_caption || 'High-accuracy cinematic extraction.';
                
                // Insight Box
                epClone.querySelector('.insight-text').innerText = ep.viral_reason || 'Identified by Gemini as a high-retention dramatic beat.';
                
                // Cliffhanger
                epClone.querySelector('.cliff-text').innerText = ep.cliffhanger || 'Unresolved ending ensures viewer curiosity.';

                grid.appendChild(epClone);
            });

            seriesContainer.appendChild(seriesClone);
        });

        document.getElementById('total-clips').innerText = totalEpisodesCount;
        
        // Smooth scroll to results
        resultsZone.scrollIntoView({ behavior: 'smooth' });
    }
});
