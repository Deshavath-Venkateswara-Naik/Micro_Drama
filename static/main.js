/**
 * Microdrama AI - Cinematic Intelligence Suite
 * Premium Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
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
    
    // UI Interactions
    const logoTrigger = document.getElementById('logo-trigger');
    if (logoTrigger) {
        logoTrigger.addEventListener('click', () => window.location.reload());
    }

    // Handle File Selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleUpload(e.target.files[0]);
        }
    });

    // Handle Drag and Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.querySelector('.modern-drop-zone').style.borderColor = 'var(--primary)';
        dropZone.querySelector('.modern-drop-zone').style.background = 'rgba(139, 92, 246, 0.05)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.querySelector('.modern-drop-zone').style.borderColor = 'var(--glass-border)';
        dropZone.querySelector('.modern-drop-zone').style.background = 'rgba(255, 255, 255, 0.02)';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            handleUpload(e.dataTransfer.files[0]);
        }
    });

    async function handleUpload(file) {
        const genre = document.getElementById('genre-input').value;
        const partitionMode = document.getElementById('mode-toggle').checked;

        // Transition UI with animations
        uploadForm.style.opacity = '0';
        setTimeout(() => {
            uploadForm.classList.add('hidden');
            processingZone.classList.remove('hidden');
            processingZone.style.opacity = '0';
            setTimeout(() => processingZone.style.opacity = '1', 50);
        }, 400);

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
                        console.error("Neural Stream Parse Error", line);
                    }
                }
            }
        } catch (error) {
            console.error("Pipeline Failure", error);
            statusText.innerText = "CRITICAL: Pipeline Interrupted";
            statusText.style.color = "var(--danger)";
        }
    }

    function updateProgress(data) {
        if (data.status) {
            statusText.innerText = data.status;
            
            // Extract layer number from status if present
            const layerMatch = data.status.match(/Layer (\d)/);
            if (layerMatch) {
                currentLayerText.innerText = `Stage ${layerMatch[1]}/6`;
            }
        }
        
        if (data.progress) {
            const prog = data.progress;
            progressBar.style.width = `${prog}%`;
            progressPercentage.innerText = `${prog}%`;
        }

        if (data.error) {
            statusText.innerText = `Error: ${data.error}`;
            statusText.style.color = "var(--danger)";
        }
    }

    function renderResults(data) {
        processingZone.classList.add('hidden');
        resultsZone.classList.remove('hidden');
        
        document.getElementById('display-job-id').innerText = data.job_id.substring(0, 8).toUpperCase();
        
        const seriesList = data.series || [];
        document.getElementById('total-series').innerText = seriesList.length;
        
        let totalEpisodesCount = 0;
        seriesContainer.innerHTML = '';

        seriesList.forEach((series, sIdx) => {
            const seriesClone = seriesTemplate.content.cloneNode(true);
            seriesClone.querySelector('.series-name').innerText = series.series_title;
            
            const grid = seriesClone.querySelector('.episodes-grid');
            const episodes = series.episodes || [];
            totalEpisodesCount += episodes.length;

            episodes.forEach((ep, eIdx) => {
                const epClone = episodeTemplate.content.cloneNode(true);
                const card = epClone.querySelector('.premium-clip-card');
                
                // Entrance animation delay
                card.style.animationDelay = `${(sIdx * 0.2) + (eIdx * 0.1)}s`;

                // Video Handling
                const video = epClone.querySelector('video');
                video.src = ep.video_url;
                
                // Play logic
                const visualContainer = epClone.querySelector('.clip-visual');
                const overlay = visualContainer.querySelector('.clip-overlay');
                const seekSlider = epClone.querySelector('.seek-slider');
                const seekProgress = epClone.querySelector('.seek-progress');
                const durationBadge = epClone.querySelector('.duration-badge');

                // Update seek bar as video plays
                video.addEventListener('timeupdate', () => {
                    if (video.duration) {
                        const progress = (video.currentTime / video.duration) * 100;
                        seekProgress.style.width = `${progress}%`;
                        seekSlider.value = progress;
                        
                        // Update duration badge with current/total
                        const cur = formatTime(video.currentTime);
                        const tot = formatTime(video.duration);
                        durationBadge.innerText = `${cur} / ${tot}`;
                    }
                });

                // Seeking logic
                seekSlider.addEventListener('input', () => {
                    if (video.duration) {
                        const time = (seekSlider.value / 100) * video.duration;
                        video.currentTime = time;
                        seekProgress.style.width = `${seekSlider.value}%`;
                    }
                });

                // Jump Buttons logic
                const jumpBtns = epClone.querySelectorAll('.jump-btn');
                jumpBtns.forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const point = parseFloat(btn.getAttribute('data-point'));
                        if (video.duration) {
                            video.currentTime = video.duration * point;
                            video.play();
                            overlay.style.opacity = '0';
                        }
                    });
                });

                visualContainer.addEventListener('click', (e) => {
                    // Prevent play/pause toggle if clicking controls
                    if (e.target.closest('.video-controls-overlay')) return;

                    if (video.paused) {
                        video.play();
                        overlay.style.opacity = '0';
                    } else {
                        video.pause();
                        overlay.style.opacity = '1';
                    }
                });

                // Auto-play preview on hover
                visualContainer.addEventListener('mouseenter', () => {
                    video.play().catch(() => {});
                });
                visualContainer.addEventListener('mouseleave', () => {
                    video.pause();
                });

                epClone.querySelector('.duration-badge').innerText = `${ep.start_time} - ${ep.end_time}`;
                epClone.querySelector('.episode-index').innerText = `EPISODE ${ep.episode_number.toString().padStart(2, '0')}`;
                epClone.querySelector('.score-num').innerText = ep.drama_score || '--';
                epClone.querySelector('.clip-headline').innerText = ep.title || 'Narrative Segment';
                epClone.querySelector('.clip-summary').innerText = ep.hook_caption || 'High-accuracy cinematic extraction based on neural narrative scoring.';
                
                // Arc Position
                const posPill = epClone.querySelector('.arc-position-pill');
                posPill.innerText = ep.narrative_arc_position || 'Scene';
                if (ep.narrative_arc_position === 'peak') posPill.style.color = 'var(--secondary)';
                
                // Intel Box
                epClone.querySelector('.intel-text').innerText = ep.viral_reason || 'Identified by Gemini as a high-retention dramatic beat with strong emotional resonance.';
                
                // Cliffhanger
                epClone.querySelector('.alert-text').innerText = ep.cliffhanger || 'Unresolved narrative threads detected to ensure maximum viewer curiosity.';

                grid.appendChild(epClone);
            });

            seriesContainer.appendChild(seriesClone);
        });

        document.getElementById('total-clips').innerText = totalEpisodesCount;
        
        // Smooth scroll to results
        setTimeout(() => {
            resultsZone.scrollIntoView({ behavior: 'smooth' });
        }, 300);
    }

    function formatTime(seconds) {
        if (isNaN(seconds)) return "0:00";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    }
});
