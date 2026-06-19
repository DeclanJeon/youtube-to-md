(() => {
    "use strict";

    const YOUTUBE_PATTERN =
        /^(?:https?:\/\/)?(?:(?:www\.)?youtube\.com\/watch\?v=|(?:www\.)?youtube\.com\/embed\/|(?:www\.)?youtube\.com\/shorts\/|(?:m\.)?youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})(?:[?&].*)?$/;

    // DOM
    const urlInput = document.getElementById("url-input");
    const clearBtn = document.getElementById("clear-btn");
    const convertBtn = document.getElementById("convert-btn");
    const optionsToggle = document.getElementById("options-toggle");
    const optionsPanel = document.getElementById("options-panel");
    const urlError = document.getElementById("url-error");
    const progressSection = document.getElementById("progress-section");
    const progressLabel = document.getElementById("progress-label");
    const progressPercent = document.getElementById("progress-percent");
    const progressEta = document.getElementById("progress-eta");
    const progressBar = document.getElementById("progress-bar");
    const progressIcon = document.getElementById("progress-icon");
    const resultSection = document.getElementById("result");
    const errorSection = document.getElementById("error-result");
    const errorMessage = document.getElementById("error-message");
    const downloadBtn = document.getElementById("download-btn");
    const copyBtn = document.getElementById("copy-btn");
    const newBtn = document.getElementById("new-btn");
    const retryBtn = document.getElementById("retry-btn");
    const preview = document.getElementById("preview");

    let lastResult = null;
    let progressTimer = null;
    let startTime = 0;

    // Progress stages
    const STAGES = [
        { id: "step-url",        label: "URL 분석 중...",          start: 0,   end: 15,  duration: 800 },
        { id: "step-meta",       label: "영상 정보 가져오는 중...", start: 15,  end: 30,  duration: 1200 },
        { id: "step-transcript", label: "자막 추출 중...",          start: 30,  end: 80,  duration: 5000 },
        { id: "step-format",     label: "Markdown 변환 중...",     start: 80,  end: 95,  duration: 800 },
    ];

    function validateUrl(url) {
        return YOUTUBE_PATTERN.test(url.trim());
    }

    function updateInputState() {
        const url = urlInput.value.trim();
        clearBtn.hidden = !url;

        if (!url) {
            urlInput.classList.remove("valid", "invalid");
            convertBtn.disabled = true;
            urlError.textContent = "";
            return;
        }

        if (validateUrl(url)) {
            urlInput.classList.remove("invalid");
            urlInput.classList.add("valid");
            convertBtn.disabled = false;
            urlError.textContent = "";
        } else {
            urlInput.classList.remove("valid");
            urlInput.classList.add("invalid");
            convertBtn.disabled = true;
            urlError.textContent = "올바른 YouTube URL을 입력해주세요.";
        }
    }

    function formatEta(ms) {
        const sec = Math.ceil(ms / 1000);
        if (sec <= 0) return "";
        if (sec < 60) return `약 ${sec}초 남음`;
        const min = Math.floor(sec / 60);
        const rem = sec % 60;
        return rem > 0 ? `약 ${min}분 ${rem}초 남음` : `약 ${min}분 남음`;
    }

    function resetProgressSteps() {
        document.querySelectorAll(".progress-step").forEach(el => {
            el.classList.remove("active", "done");
        });
    }

    function showProgress() {
        progressSection.hidden = false;
        resultSection.hidden = true;
        errorSection.hidden = true;
        convertBtn.disabled = true;
        startTime = Date.now();
        resetProgressSteps();

        let currentStage = 0;
        let progress = 0;

        function tick() {
            const elapsed = Date.now() - startTime;
            const stage = STAGES[currentStage];
            if (!stage) return;

            // Calculate progress within this stage
            const stageElapsed = elapsed - STAGES.slice(0, currentStage).reduce((s, st) => s + st.duration, 0);
            const stageProgress = Math.min(stageElapsed / stage.duration, 1);
            progress = stage.start + (stage.end - stage.start) * stageProgress;

            // Update UI
            progressBar.style.width = `${progress}%`;
            progressPercent.textContent = `${Math.round(progress)}%`;
            progressLabel.textContent = stage.label;
            progressIcon.textContent = "⏳";

            // ETA
            const totalEstimated = STAGES.reduce((s, st) => s + st.duration, 0);
            const remaining = Math.max(0, totalEstimated - elapsed);
            progressEta.textContent = formatEta(remaining);

            // Mark steps
            STAGES.forEach((s, i) => {
                const el = document.getElementById(s.id);
                if (i < currentStage) {
                    el.classList.add("done");
                    el.classList.remove("active");
                } else if (i === currentStage) {
                    el.classList.add("active");
                    el.classList.remove("done");
                } else {
                    el.classList.remove("active", "done");
                }
            });

            // Move to next stage
            if (stageProgress >= 1 && currentStage < STAGES.length - 1) {
                document.getElementById(stage.id).classList.add("done");
                document.getElementById(stage.id).classList.remove("active");
                currentStage++;
            }

            progressTimer = requestAnimationFrame(tick);
        }

        progressTimer = requestAnimationFrame(tick);
    }

    function hideProgress() {
        if (progressTimer) {
            cancelAnimationFrame(progressTimer);
            progressTimer = null;
        }
        // Animate to 100%
        progressBar.style.width = "100%";
        progressPercent.textContent = "100%";
        progressLabel.textContent = "완료!";
        progressIcon.textContent = "✅";
        progressEta.textContent = "";

        // Mark all steps done
        STAGES.forEach(s => {
            const el = document.getElementById(s.id);
            el.classList.add("done");
            el.classList.remove("active");
        });

        // Hide after short delay
        setTimeout(() => {
            progressSection.hidden = true;
        }, 600);
    }

    function showResult(data) {
        hideProgress();
        resultSection.hidden = false;
        errorSection.hidden = true;
        convertBtn.disabled = false;

        document.getElementById("result-title").textContent = data.title;
        document.getElementById("result-channel").textContent = data.channel;
        document.getElementById("result-stats").textContent =
            `${data.segment_count}개 세그먼트 · ${data.word_count.toLocaleString()}자`;
        preview.textContent = data.markdown;
    }

    function showError(msg) {
        hideProgress();
        resultSection.hidden = true;
        errorSection.hidden = false;
        convertBtn.disabled = false;
        errorMessage.textContent = msg;
    }

    function resetToInput() {
        if (progressTimer) {
            cancelAnimationFrame(progressTimer);
            progressTimer = null;
        }
        progressSection.hidden = true;
        resultSection.hidden = true;
        errorSection.hidden = true;
        urlInput.value = "";
        urlInput.classList.remove("valid", "invalid");
        convertBtn.disabled = true;
        clearBtn.hidden = true;
        urlError.textContent = "";
        lastResult = null;
        urlInput.focus();
    }

    // Events
    urlInput.addEventListener("input", updateInputState);

    urlInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !convertBtn.disabled) {
            convert();
        }
    });

    clearBtn.addEventListener("click", () => {
        urlInput.value = "";
        updateInputState();
        urlInput.focus();
    });

    optionsToggle.addEventListener("click", () => {
        optionsPanel.hidden = !optionsPanel.hidden;
    });

    convertBtn.addEventListener("click", convert);
    downloadBtn.addEventListener("click", download);
    copyBtn.addEventListener("click", copyToClipboard);
    newBtn.addEventListener("click", resetToInput);
    retryBtn.addEventListener("click", resetToInput);

    async function convert() {
        const url = urlInput.value.trim();
        if (!validateUrl(url)) return;

        showProgress();

        const language = document.getElementById("opt-language").value || null;
        const includeTimestamps = document.getElementById("opt-timestamps").checked;
        const includeMetadata = document.getElementById("opt-metadata").checked;

        try {
            const resp = await fetch("/api/transcript", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url,
                    language,
                    include_timestamps: includeTimestamps,
                    include_metadata: includeMetadata,
                }),
            });

            const data = await resp.json();

            if (!resp.ok || !data.success) {
                const err = data.error || {};
                throw new Error(err.message || "변환에 실패했습니다.");
            }

            lastResult = data.data;
            showResult(data.data);
        } catch (err) {
            showError(err.message || "서버 오류가 발생했습니다.");
        }
    }

    function download() {
        if (!lastResult) return;
        const blob = new Blob([lastResult.markdown], { type: "text/markdown;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = lastResult.download_filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function copyToClipboard() {
        if (!lastResult) return;
        try {
            await navigator.clipboard.writeText(lastResult.markdown);
            copyBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                복사됨!`;
            setTimeout(() => {
                copyBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    복사`;
            }, 2000);
        } catch {
            const textarea = document.createElement("textarea");
            textarea.value = lastResult.markdown;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }
    }
})();
