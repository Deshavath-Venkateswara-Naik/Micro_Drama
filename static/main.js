/**
 * Microdrama AI - Cinematic Intelligence Suite
 * Premium Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentJobId = null;

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

    // Click to open file picker
    dropZone.addEventListener('click', () => {
        fileInput.click();
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
        const targetMoment = document.getElementById('moment-input').value;
        const starCast = document.getElementById('star-cast-input').value;

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
        formData.append('target_moment', targetMoment);
        if (starCast) {
            formData.append('star_cast', starCast);
        }

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
        
        // Store job_id for trailer generation
        currentJobId = data.job_id;
        
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
                epClone.querySelector('.score-num').innerText = Math.round(ep.drama_score) || '--';
                epClone.querySelector('.clip-headline').innerText = ep.title || 'Narrative Segment';
                epClone.querySelector('.clip-summary').innerText = ep.hook_caption || 'High-accuracy cinematic extraction based on neural narrative scoring.';
                
                // Render Moment Badges dynamically
                const badgesGroup = epClone.querySelector('.moment-badges-group');
                badgesGroup.innerHTML = '';
                const moments = ep.moment_types || [ep.narrative_arc] || [];
                const processedMoments = Array.isArray(moments) ? moments : [moments];
                
                processedMoments.forEach(m => {
                    if (!m) return;
                    const mLower = m.toLowerCase();
                    const badge = document.createElement('span');
                    badge.className = `moment-badge badge-${mLower}`;
                    
                    let icon = '🎬';
                    let name = m;
                    if (mLower.includes('action')) { icon = '🔥'; name = 'Action'; badge.className = 'moment-badge badge-action'; }
                    else if (mLower.includes('comedy')) { icon = '⚡'; name = 'Comedy'; badge.className = 'moment-badge badge-comedy'; }
                    else if (mLower.includes('dialogue')) { icon = '💬'; name = 'Dialogue'; badge.className = 'moment-badge badge-dialogue'; }
                    else if (mLower.includes('suspense')) { icon = '⏳'; name = 'Suspense'; badge.className = 'moment-badge badge-suspense'; }
                    else if (mLower.includes('celebrity') || mLower.includes('star')) { icon = '🌟'; name = 'Star Cast'; badge.className = 'moment-badge badge-celebrity'; }
                    
                    badge.innerHTML = `${icon} ${name}`;
                    badgesGroup.appendChild(badge);
                });
                
                if (ep.primary_celebrities && ep.primary_celebrities.length > 0) {
                    ep.primary_celebrities.forEach(star => {
                        const celebBadge = document.createElement('span');
                        celebBadge.className = 'moment-badge badge-celebrity';
                        celebBadge.innerHTML = `👤 ${star}`;
                        badgesGroup.appendChild(celebBadge);
                    });
                }

                // Arc Position
                const posPill = epClone.querySelector('.arc-position-pill');
                posPill.innerText = ep.narrative_arc_position || 'Scene';
                if (ep.narrative_arc_position === 'peak') posPill.style.color = 'var(--secondary)';
                
                // Intel Box
                epClone.querySelector('.intel-text').innerText = ep.why_this_clip_performs || ep.viral_reason || 'Identified by Gemini as a high-retention dramatic beat with strong emotional resonance.';
                
                // Cliffhanger
                epClone.querySelector('.alert-text').innerText = ep.cliffhanger_ending || ep.cliffhanger || 'Unresolved narrative threads detected to ensure maximum viewer curiosity.';

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

    // --- Trailer Generation ---
    const trailerBtn = document.getElementById('trailer-generate-btn');
    const trailerBtnLoader = document.getElementById('trailer-btn-loader');

    trailerBtn.addEventListener('click', async () => {
        const trailerLength = parseInt(document.getElementById('trailer-length-input').value);
        const targetStyle = document.getElementById('trailer-style-input').value;

        // If we already have a processed job, go directly to trailer generation
        if (currentJobId) {
            await generateTrailer(currentJobId, trailerLength, targetStyle);
            return;
        }

        // Otherwise, check if a file is selected — run full pipeline first
        const fileInput = document.getElementById('file-input');
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select a video file first, then click to generate a trailer.');
            return;
        }

        // Run full pipeline, then generate trailer
        trailerBtn.disabled = true;
        trailerBtnLoader.classList.remove('hidden');
        trailerBtn.querySelector('.trailer-btn-text').innerText = 'Processing Pipeline...';

        const genre = document.getElementById('genre-input').value;
        const partitionMode = document.getElementById('mode-toggle').checked;
        const targetMoment = document.getElementById('moment-input').value;
        const starCast = document.getElementById('star-cast-input').value;

        // Transition UI
        uploadForm.style.opacity = '0';
        setTimeout(() => {
            uploadForm.classList.add('hidden');
            processingZone.classList.remove('hidden');
            processingZone.style.opacity = '0';
            setTimeout(() => processingZone.style.opacity = '1', 50);
        }, 400);

        const formData = new FormData();
        formData.append('video', fileInput.files[0]);
        formData.append('genre', genre);
        formData.append('partition_mode', partitionMode);
        formData.append('target_moment', targetMoment);
        if (starCast) formData.append('star_cast', starCast);

        try {
            const response = await fetch('/api/v1/process', {
                method: 'POST',
                body: formData
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let pipelineResult = null;

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
                            pipelineResult = data.result;
                            currentJobId = data.result.job_id;
                            renderResults(data.result);
                        }
                    } catch (e) {
                        console.error("Neural Stream Parse Error", line);
                    }
                }
            }

            // Pipeline done — now generate trailer
            if (currentJobId) {
                trailerBtn.querySelector('.trailer-btn-text').innerText = 'Generating Trailer...';
                await generateTrailer(currentJobId, trailerLength, targetStyle);
            }
        } catch (error) {
            console.error("Pipeline + Trailer Failure", error);
            statusText.innerText = "CRITICAL: Pipeline Interrupted";
            statusText.style.color = "var(--danger)";
        } finally {
            trailerBtn.disabled = false;
            trailerBtnLoader.classList.add('hidden');
            trailerBtn.querySelector('.trailer-btn-text').innerText = 'Short-Form Trailer Generation';
        }
    });

    async function generateTrailer(jobId, trailerLength, targetStyle) {
        trailerBtn.disabled = true;
        trailerBtnLoader.classList.remove('hidden');
        trailerBtn.querySelector('.trailer-btn-text').innerText = 'Generating Trailer...';

        // Show processing zone if hidden
        if (processingZone.classList.contains('hidden')) {
            processingZone.classList.remove('hidden');
            processingZone.style.opacity = '1';
        }

        try {
            const response = await fetch('/api/v1/generate-trailer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    trailer_length: trailerLength,
                    target_style: targetStyle
                })
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
                            renderTrailerResult(data.result, trailerLength, targetStyle);
                        }
                        if (data.error) {
                            console.error("Trailer Error:", data.error);
                        }
                    } catch (e) {
                        console.error("Trailer Stream Parse Error", line);
                    }
                }
            }
        } catch (error) {
            console.error("Trailer Generation Failed", error);
            statusText.innerText = "Trailer generation failed";
            statusText.style.color = "var(--danger)";
        } finally {
            trailerBtn.disabled = false;
            trailerBtnLoader.classList.add('hidden');
            trailerBtn.querySelector('.trailer-btn-text').innerText = 'Short-Form Trailer Generation';
        }
    }

    function renderTrailerResult(result, trailerLength, targetStyle) {
        processingZone.classList.add('hidden');
        resultsZone.classList.remove('hidden');

        // Create trailer section at the top of results
        const trailerSection = document.createElement('div');
        trailerSection.className = 'series-wrapper trailer-result-section';
        trailerSection.innerHTML = `
            <div class="series-meta">
                <div class="meta-decoration" style="background: linear-gradient(135deg, #ec4899, #8b5cf6);"></div>
                <div class="meta-content">
                    <span class="narrative-tag">GENERATED TRAILER</span>
                    <h3 class="series-name">🎬 Generated Trailer (${trailerLength}s - ${targetStyle})</h3>
                </div>
            </div>
            <div class="episodes-grid">
                <div class="premium-clip-card trailer-card">
                    <div class="clip-visual">
                        <video preload="metadata" controls src="${result.video_url}"></video>
                        <div class="duration-badge">${trailerLength}s</div>
                        <div class="score-badge">
                            <span class="score-num">${result.total_clips_used || '--'}</span>
                            <span class="score-txt">CLIPS</span>
                        </div>
                    </div>
                    <div class="clip-info">
                        <div class="info-header">
                            <span class="episode-index">TRAILER</span>
                            <div class="moment-badges-group">
                                <span class="moment-badge badge-action">🎬 ${targetStyle}</span>
                            </div>
                        </div>
                        <h4 class="clip-headline">Short-Form Trailer (${trailerLength}s)</h4>
                        <p class="clip-summary">Auto-assembled from ${result.total_clips_used || 0} top-ranked clips using narrative structure: hook → escalation → engagement → ending.</p>
                        ${result.clips ? `
                        <div class="ai-intel">
                            <div class="intel-header">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                                CLIP BREAKDOWN
                            </div>
                            <div class="intel-text" style="font-size: 0.8rem;">
                                ${result.clips.map(c => `<div style="margin-bottom:4px;"><strong>[${c.narrative_role}]</strong> ${c.start_time} → ${c.end_time} (Score: ${c.drama_score})</div>`).join('')}
                            </div>
                        </div>` : ''}
                    </div>
                </div>
            </div>
        `;

        // Insert at the top of results
        seriesContainer.insertBefore(trailerSection, seriesContainer.firstChild);
        resultsZone.scrollIntoView({ behavior: 'smooth' });
    }

    // Store job_id when pipeline completes (hook into existing renderResults)
});
