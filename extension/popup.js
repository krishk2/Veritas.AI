document.addEventListener('DOMContentLoaded', function () {
    const verifyBtn = document.getElementById('verify-btn');
    const claimInput = document.getElementById('claim-input');
    const loadingDiv = document.getElementById('loading');
    const resultSection = document.getElementById('result-section');
    const errorMsg = document.getElementById('error-msg');
    const detailsBtn = document.getElementById('details-btn');
    const detailsSection = document.getElementById('details-section');

    // Drag, Drop & Media Elements
    const dropZone = document.getElementById('drop-zone');
    const dropZonePrompt = document.getElementById('drop-zone-prompt');
    const imageFileInput = document.getElementById('image-file-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const imageName = document.getElementById('image-name');
    const removeImageBtn = document.getElementById('remove-image-btn');

    let currentMediaBase64 = null;
    let currentSources = [];

    // Auto-fill active tab title if available
    if (chrome && chrome.tabs && chrome.tabs.query) {
        chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
            if (tabs && tabs[0] && tabs[0].title) {
                claimInput.value = tabs[0].title;
            }
        });
    }

    // --- Media Input Handling ---
    function handleMediaFile(file, label) {
        if (!file) return;

        const isImage = file.type.startsWith('image/');
        const isVideo = file.type.startsWith('video/');

        if (!isImage && !isVideo) {
            showError('Please upload a valid image or MP4 video file.');
            return;
        }

        const reader = new FileReader();
        reader.onload = function (e) {
            currentMediaBase64 = e.target.result;
            imagePreview.src = isImage ? currentMediaBase64 : 'icons/icon48.png';
            imageName.textContent = label || file.name || (isImage ? 'Attached Image' : 'Attached Video');

            dropZonePrompt.classList.add('hidden');
            imagePreviewContainer.classList.remove('hidden');
            errorMsg.classList.add('hidden');
        };
        reader.onerror = function () {
            showError('Failed to read media data.');
        };
        reader.readAsDataURL(file);
    }

    function clearAttachedMedia() {
        currentMediaBase64 = null;
        imagePreview.src = '';
        imageFileInput.value = '';
        imagePreviewContainer.classList.add('hidden');
        dropZonePrompt.classList.remove('hidden');
    }

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.classList.remove('hidden');
    }

    // 1. Clipboard Paste (Ctrl+V)
    window.addEventListener('paste', function (e) {
        const clipboardItems = (e.clipboardData || window.clipboardData).items;
        if (!clipboardItems) return;

        for (let i = 0; i < clipboardItems.length; i++) {
            const item = clipboardItems[i];
            if (item.type.indexOf('image') !== -1 || item.type.indexOf('video') !== -1) {
                const blob = item.getAsFile();
                handleMediaFile(blob, 'Pasted Media');
                e.preventDefault();
                break;
            }
        }
    });

    // 2. Drag & Drop Listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', function (e) {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            handleMediaFile(files[0], files[0].name);
        }
    });

    // 3. File Input
    imageFileInput.addEventListener('change', function () {
        if (this.files && this.files[0]) {
            handleMediaFile(this.files[0], this.files[0].name);
        }
    });

    // 4. Remove Button
    removeImageBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        clearAttachedMedia();
    });

    // --- Verify Action ---
    verifyBtn.addEventListener('click', async function () {
        const claim = claimInput.value.trim();

        if (!claim && !currentMediaBase64) {
            showError('Please enter a claim or attach media to verify.');
            return;
        }

        // Reset UI
        errorMsg.classList.add('hidden');
        resultSection.classList.add('hidden');
        loadingDiv.classList.remove('hidden');
        verifyBtn.disabled = true;

        try {
            const isVideo = currentMediaBase64 && currentMediaBase64.startsWith('data:video');
            const payload = {
                claim: claim || undefined,
                image_base64: (!isVideo && currentMediaBase64) ? currentMediaBase64 : undefined,
                video_base64: (isVideo && currentMediaBase64) ? currentMediaBase64 : undefined
            };

            const response = await fetch('http://localhost:8001/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || 'API Error: ' + response.statusText);
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            showError(error.message || 'Failed to connect to Veritas.AI backend.');
        } finally {
            loadingDiv.classList.add('hidden');
            verifyBtn.disabled = false;
        }
    });

    detailsBtn.addEventListener('click', function () {
        detailsSection.classList.toggle('hidden');
        detailsBtn.textContent = detailsSection.classList.contains('hidden') ? 'View Detailed Evidence & Audits' : 'Hide Details';
    });

    // --- Perplexity-Style Result Renderer ---
    function displayResults(data) {
        resultSection.classList.remove('hidden');
        currentSources = data.sources || [];

        // 1. Verdict & Status
        const verdictEl = document.getElementById('verdict');
        verdictEl.textContent = data.verdict;
        verdictEl.className = data.verdict.toLowerCase();

        const statusEl = document.getElementById('review-status');
        statusEl.textContent = data.status || 'VERIFIED';
        statusEl.style.background = data.status === 'VERIFIED' ? '#dcfce7' : '#fef3c7';
        statusEl.style.color = data.status === 'VERIFIED' ? '#15803d' : '#b45309';

        // 2. Truth / Confidence Score
        const confidenceScore = (data.confidence * 100).toFixed(0);
        document.getElementById('confidence-score').textContent = confidenceScore + '%';
        document.getElementById('confidence-bar').style.width = confidenceScore + '%';

        // 3. Render Perplexity-Style Sources Carousel
        renderSourcesCarousel(currentSources);

        // 4. Render Forensics Alert (if applicable)
        renderForensicsAlert(data);

        // 5. Render Cited Explanation with Interactive Citations
        renderCitedExplanation(data.explanation || 'No explanation provided.');

        // 6. Render Evidence & Audits
        renderEvidenceAndCredibility(data);
    }

    function renderSourcesCarousel(sources) {
        const carousel = document.getElementById('sources-carousel');
        const countBadge = document.getElementById('sources-count');
        carousel.innerHTML = '';
        countBadge.textContent = sources.length;

        if (!sources || sources.length === 0) {
            carousel.innerHTML = '<span style="font-size: 11px; color: #94a3b8;">No web sources indexed.</span>';
            return;
        }

        sources.forEach(src => {
            const card = document.createElement('a');
            card.href = src.url || '#';
            card.target = '_blank';
            card.className = 'source-card';
            card.id = `source-card-${src.citation_id}`;

            const topRow = document.createElement('div');
            topRow.className = 'source-card-top';

            const favicon = document.createElement('img');
            favicon.src = src.favicon_url || 'https://www.google.com/s2/favicons?domain=example.com&sz=64';
            favicon.className = 'source-favicon';
            favicon.onerror = () => { favicon.src = 'icons/icon16.png'; };

            const domain = document.createElement('span');
            domain.className = 'source-domain';
            domain.textContent = src.domain || 'Source';

            const citationNum = document.createElement('span');
            citationNum.className = 'source-citation-num';
            citationNum.textContent = src.citation_id;

            topRow.appendChild(favicon);
            topRow.appendChild(domain);
            topRow.appendChild(citationNum);

            const title = document.createElement('div');
            title.className = 'source-title';
            title.textContent = src.title || src.domain;

            const credStatus = (src.credibility_status || 'Neutral').toLowerCase();
            const credPill = document.createElement('span');
            credPill.className = `source-cred-pill cred-${credStatus}`;
            credPill.textContent = src.credibility_status || 'Neutral';

            card.appendChild(topRow);
            card.appendChild(title);
            card.appendChild(credPill);

            carousel.appendChild(card);
        });
    }

    function renderForensicsAlert(data) {
        const banner = document.getElementById('forensic-banner');
        const titleEl = document.getElementById('forensic-title');
        const summaryEl = document.getElementById('forensic-summary');

        const imgForensics = data.image_forensics || {};
        const vidForensics = data.video_forensics || {};

        if (vidForensics.is_deepfake_or_ai) {
            titleEl.textContent = 'Deepfake / AI Video Detected';
            summaryEl.textContent = vidForensics.summary;
            banner.classList.remove('hidden');
        } else if (imgForensics.is_tampered_or_ai) {
            titleEl.textContent = 'Manipulated / AI Image Detected';
            summaryEl.textContent = imgForensics.summary;
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    }

    function renderCitedExplanation(explanationText) {
        const container = document.getElementById('explanation');
        container.innerHTML = '';

        // Match citation patterns like [1], [2], [1, 2]
        const citationRegex = /\[(\d+(?:,\s*\d+)*)\]/g;
        let lastIndex = 0;
        let match;

        while ((match = citationRegex.exec(explanationText)) !== null) {
            // Append preceding text
            if (match.index > lastIndex) {
                container.appendChild(document.createTextNode(explanationText.substring(lastIndex, match.index)));
            }

            // Create interactive citation pill(s)
            const numbers = match[1].split(',').map(n => n.trim());
            numbers.forEach(num => {
                const pill = document.createElement('a');
                pill.href = '#';
                pill.className = 'citation-pill';
                pill.textContent = num;
                pill.title = `Jump to Source [${num}]`;

                pill.addEventListener('click', (e) => {
                    e.preventDefault();
                    highlightSourceCard(num);
                });

                container.appendChild(pill);
            });

            lastIndex = citationRegex.lastIndex;
        }

        // Append remaining text
        if (lastIndex < explanationText.length) {
            container.appendChild(document.createTextNode(explanationText.substring(lastIndex)));
        }
    }

    function highlightSourceCard(citationId) {
        // Remove existing highlights
        document.querySelectorAll('.source-card.highlighted').forEach(el => el.classList.remove('highlighted'));

        const card = document.getElementById(`source-card-${citationId}`);
        if (card) {
            card.classList.add('highlighted');
            card.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            setTimeout(() => {
                card.classList.remove('highlighted');
            }, 2500);
        }
    }

    function renderEvidenceAndCredibility(data) {
        // Evidence list
        const evidenceList = document.getElementById('evidence-list');
        evidenceList.innerHTML = '';
        if (data.evidence && data.evidence.length > 0) {
            data.evidence.forEach(item => {
                const li = document.createElement('li');
                li.textContent = `[${item.label}] ${item.sentence} (${(item.score * 100).toFixed(0)}%)`;
                evidenceList.appendChild(li);
            });
        } else {
            evidenceList.innerHTML = '<li style="color: #94a3b8;">No evidence sentences extracted.</li>';
        }

        // Credibility list
        const credList = document.getElementById('credibility-list');
        credList.innerHTML = '';
        if (data.credibility_report && data.credibility_report.length > 0) {
            data.credibility_report.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${item.domain}</strong>: <span class="cred-${(item.status || 'neutral').toLowerCase()}">${item.status}</span>`;
                credList.appendChild(li);
            });
        } else {
            credList.innerHTML = '<li style="color: #94a3b8;">No domain audits performed.</li>';
        }
    }
});
