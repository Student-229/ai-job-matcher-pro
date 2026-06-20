// ── Global Data Store ──
let globalData = null;
let allJobs = [];
let currentUser = null;

// ── File Upload Handling ──
const fileInput = document.getElementById('fileInput');
const uploadBox = document.getElementById('uploadBox');

// Get current user from page
function getCurrentUser() {
    const userScript = document.querySelector('script[data-user]');
    if (userScript) {
        return JSON.parse(userScript.dataset.user);
    }
    return null;
}

// Drag and Drop
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
        handleFileSelect(file);
    } else {
        showNotification('Please upload a PDF file only!', 'error');
    }
});

// File Input Change
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFileSelect(file);
});

// Handle File Selection
function handleFileSelect(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showNotification('Only PDF files are allowed!', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showNotification('File too large! Max 10MB allowed.', 'error');
        return;
    }

    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
    document.getElementById('uploadBox').style.display = 'none';
    document.getElementById('fileSelected').style.display = 'block';

    fileInput._selectedFile = file;
}

// Remove File
function removeFile() {
    fileInput.value = '';
    fileInput._selectedFile = null;
    document.getElementById('uploadBox').style.display = 'block';
    document.getElementById('fileSelected').style.display = 'none';
}

// ── Analyze Resume ──
async function analyzeResume() {
    const file = fileInput._selectedFile || fileInput.files[0];

    if (!file) {
        showNotification('Please select a file first!', 'error');
        return;
    }

    document.getElementById('uploadContainer').style.display = 'none';
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';

    animateLoadingSteps();

    const formData = new FormData();
    formData.append('resume', file);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.status === 'upgrade_required') {
            // User exceeded free tier
            document.getElementById('loadingState').style.display = 'none';
            document.getElementById('uploadContainer').style.display = 'block';
            openUpgradeModal();
            showNotification('You\'ve used all free analyses. Please upgrade!', 'info');
            return;
        }

        if (data.success) {
            globalData = data;
            allJobs = data.matched_jobs;
            displayResults(data);
        } else {
            showError(data.error || 'Something went wrong. Please try again.');
        }

    } catch (error) {
        showError('Network error. Please check your connection and try again.');
    }
}

// ── Animate Loading Steps ──
function animateLoadingSteps() {
    const steps = ['step1', 'step2', 'step3'];
    const texts = [
        'Reading your resume...',
        'AI is extracting your skills...',
        'Finding best job matches...'
    ];

    let current = 0;

    const interval = setInterval(() => {
        if (current > 0) {
            document.getElementById(steps[current - 1]).classList.remove('active');
            document.getElementById(steps[current - 1]).classList.add('done');
            document.getElementById(steps[current - 1]).querySelector('i').className = 'fas fa-check-circle';
        }

        if (current < steps.length) {
            document.getElementById(steps[current]).classList.add('active');
            document.getElementById('loadingText').textContent = texts[current];
            current++;
        } else {
            clearInterval(interval);
        }
    }, 2000);
}

// ── Display Results ──
function displayResults(data) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';

    const { resume_data, matched_jobs, feedback, skill_advice, roadmap } = data;

    document.getElementById('profileEducation').textContent = resume_data.education || 'Not specified';
    document.getElementById('profileExperience').textContent = resume_data.experience_years || 'Not specified';
    document.getElementById('profileRoles').textContent = (resume_data.previous_roles || []).join(', ') || 'Not specified';
    document.getElementById('profileSummary').textContent = resume_data.summary || 'Professional with diverse skills';

    if (feedback && feedback.score) {
        document.getElementById('resumeScore').textContent = `Score: ${feedback.score}/100`;
    }

    const skillsWrap = document.getElementById('detectedSkills');
    skillsWrap.innerHTML = '';
    (resume_data.skills || []).forEach(skill => {
        const span = document.createElement('span');
        span.className = 'skill-tag';
        span.textContent = skill;
        skillsWrap.appendChild(span);
    });

    if (feedback) {
        const tipsContainer = document.getElementById('resumeTips');
        tipsContainer.innerHTML = '';

        const tipIcons = ['💡', '📝', '🎯'];
        (feedback.tips || []).forEach((tip, i) => {
            tipsContainer.innerHTML += `
                <div class="tip-item">
                    <span class="tip-icon">${tipIcons[i] || '💡'}</span>
                    <span>${tip}</span>
                </div>
            `;
        });

        if (feedback.strong_points && feedback.strong_points.length > 0) {
            const strongContainer = document.getElementById('strongPoints');
            strongContainer.innerHTML = '<label>✅ Strong Points</label>';
            feedback.strong_points.forEach(point => {
                strongContainer.innerHTML += `<span class="strong-tag">${point}</span>`;
            });
        }
    }

    document.getElementById('jobCount').textContent = `${matched_jobs.length} matches found`;
    renderJobs(matched_jobs, skill_advice);

    if (roadmap && roadmap.month1) {
        document.getElementById('roadmapCard').style.display = 'block';
        renderRoadmap(roadmap);
    }

    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// ── Render Jobs ──
function renderJobs(jobs, topAdvice = '') {
    const jobsList = document.getElementById('jobsList');
    jobsList.innerHTML = '';

    if (jobs.length === 0) {
        jobsList.innerHTML = `
            <div style="text-align:center; padding:2rem; color:rgba(255,255,255,0.4);">
                <i class="fas fa-search" style="font-size:2rem; margin-bottom:1rem; display:block;"></i>
                No jobs found with current filter. Try lowering the minimum match percentage.
            </div>
        `;
        return;
    }

    jobs.forEach((job, index) => {
        const pct = job.match_percent;
        let badgeClass, barColor;

        if (pct >= 70) {
            badgeClass = 'match-high';
            barColor = 'linear-gradient(90deg, #48bb78, #38a169)';
        } else if (pct >= 40) {
            badgeClass = 'match-mid';
            barColor = 'linear-gradient(90deg, #ed8936, #dd6b20)';
        } else {
            badgeClass = 'match-low';
            barColor = 'linear-gradient(90deg, #fc8181, #e53e3e)';
        }

        const matchedHTML = job.matched_skills.map(s =>
            `<span class="skill-green">✅ ${s}</span>`
        ).join('') || '<span style="color:rgba(255,255,255,0.3); font-size:0.82rem;">None yet</span>';

        const missingHTML = job.missing_skills.map(s =>
            `<span class="skill-red">❌ ${s}</span>`
        ).join('') || '<span class="skill-green">🎉 Perfect Match!</span>';

        const adviceHTML = (index === 0 && topAdvice) ? `
            <div class="advice-box">
                <strong>💡 How to improve for this role:</strong>
                ${topAdvice}
            </div>
        ` : job.missing_skills.length > 0 ? `
            <button class="get-advice-btn" onclick="getAdviceForJob('${job.job_title}', ${JSON.stringify(job.missing_skills)}, ${JSON.stringify(job.matched_skills)}, this)">
                <i class="fas fa-lightbulb"></i> Get Skill Gap Advice
            </button>
        ` : '';

        jobsList.innerHTML += `
            <div class="job-card" id="job-${index}">
                <div class="job-card-header">
                    <div class="job-left">
                        <div class="job-rank-badge">#${index + 1}</div>
                        <div>
                            <div class="job-title">${job.job_title}</div>
                            <div class="job-meta">
                                <i class="fas fa-tag"></i> ${job.category || 'General'}
                            </div>
                        </div>
                    </div>
                    <span class="match-badge ${badgeClass}">${pct}% Match</span>
                </div>

                <div class="progress-bar-wrap">
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill"
                            style="width:0%; background:${barColor}"
                            data-width="${pct}">
                        </div>
                    </div>
                </div>

                <div class="job-salary">
                    <i class="fas fa-rupee-sign"></i> ${job.salary_range || 'Competitive'}
                </div>

                <div class="job-description">${job.description}</div>

                <div class="job-skills-grid">
                    <div class="job-skills-col">
                        <label>Skills You Have (${job.matched_skills.length})</label>
                        <div>${matchedHTML}</div>
                    </div>
                    <div class="job-skills-col">
                        <label>Missing Skills (${job.missing_skills.length})</label>
                        <div>${missingHTML}</div>
                    </div>
                </div>

                ${adviceHTML}
            </div>
        `;
    });

    setTimeout(() => {
        document.querySelectorAll('.progress-bar-fill').forEach(bar => {
            bar.style.width = bar.dataset.width + '%';
        });
    }, 100);
}

// ── Get Advice For Specific Job ──
async function getAdviceForJob(jobTitle, missingSkills, currentSkills, btn) {
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting advice...';
    btn.disabled = true;

    try {
        const response = await fetch('/job-advice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_title: jobTitle,
                missing_skills: missingSkills,
                current_skills: currentSkills
            })
        });

        const data = await response.json();

        if (data.success) {
            btn.parentElement.innerHTML += `
                <div class="advice-box" style="margin-top:0.8rem;">
                    <strong>💡 How to improve for ${jobTitle}:</strong>
                    ${data.advice}
                </div>
            `;
            btn.remove();
        }
    } catch (error) {
        btn.innerHTML = '<i class="fas fa-lightbulb"></i> Get Skill Gap Advice';
        btn.disabled = false;
    }
}

// ── Render Roadmap ──
function renderRoadmap(roadmap) {
    const content = document.getElementById('roadmapContent');

    content.innerHTML = `
        <div class="roadmap-grid">
            ${['month1', 'month2', 'month3'].map((month, i) => {
                const m = roadmap[month];
                if (!m) return '';
                return `
                    <div class="roadmap-month">
                        <div class="month-label">Month ${i + 1}</div>
                        <div class="month-focus">${m.focus}</div>
                        <ul class="month-tasks">
                            ${(m.tasks || []).map(t => `<li>${t}</li>`).join('')}
                        </ul>
                        <div class="month-resource">
                            <i class="fas fa-book"></i> ${m.resource}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
        ${roadmap.final_goal ? `
            <div class="roadmap-goal">
                🎯 Goal: ${roadmap.final_goal}
            </div>
        ` : ''}
    `;
}

// ── Filter Jobs ──
function filterJobs(value) {
    document.getElementById('filterValue').textContent = value + '%';
    const filtered = allJobs.filter(j => j.match_percent >= parseInt(value));
    renderJobs(filtered);
}

// ── Download Report ──
function downloadReport() {
    if (!globalData) return;

    const report = {
        generated_on: new Date().toLocaleString(),
        profile: globalData.resume_data,
        resume_score: globalData.feedback?.score || 'N/A',
        improvement_tips: globalData.feedback?.tips || [],
        top_job_matches: globalData.matched_jobs.slice(0, 5).map(j => ({
            title: j.job_title,
            match_percentage: j.match_percent,
            salary_range: j.salary_range,
            matched_skills: j.matched_skills,
            missing_skills: j.missing_skills
        })),
        top_skill_advice: globalData.skill_advice,
        career_roadmap: globalData.roadmap
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `job_report_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);

    showNotification('Report downloaded successfully!', 'success');
}

// ── Reset All ──
function resetAll() {
    globalData = null;
    allJobs = [];
    fileInput.value = '';
    fileInput._selectedFile = null;

    document.getElementById('uploadContainer').style.display = 'block';
    document.getElementById('uploadBox').style.display = 'block';
    document.getElementById('fileSelected').style.display = 'none';
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('roadmapCard').style.display = 'none';

    ['step1', 'step2', 'step3'].forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove('active', 'done');
        el.querySelector('i').className = 'fas fa-circle';
    });

    document.getElementById('uploadSection').scrollIntoView({ behavior: 'smooth' });
}

// ── Show Error ──
function showError(message) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('uploadContainer').style.display = 'block';
    document.getElementById('uploadBox').style.display = 'block';
    document.getElementById('fileSelected').style.display = 'none';
    showNotification(message, 'error');
}

// ── UPGRADE MODAL FUNCTIONS ← NEW ← ──

function openUpgradeModal() {
    document.getElementById('upgradeModal').classList.remove('hidden');
    loadSubscriptionPlans();
}

function closeUpgradeModal() {
    document.getElementById('upgradeModal').classList.add('hidden');
}

async function loadSubscriptionPlans() {
    try {
        const response = await fetch('/get-plans');
        const plans = await response.json();
        
        let html = '';
        for (const [planId, plan] of Object.entries(plans)) {
            const isPopular = planId === 'plan_3month';
            html += `
                <div class="plan-card ${isPopular ? 'popular' : ''}">
                    ${isPopular ? '<div class="popular-badge">⭐ BEST VALUE</div>' : ''}
                    <h3>${plan.name}</h3>
                    <div class="plan-price">₹${plan.price}</div>
                    <div class="plan-duration">${plan.duration_days} days access</div>
                    <ul class="plan-features">
                        ${plan.features.map(f => `<li>✅ ${f}</li>`).join('')}
                    </ul>
                    <button class="plan-btn" onclick="initiatePayment('${planId}', ${plan.price})">
                        Subscribe Now
                    </button>
                </div>
            `;
        }
        
        document.getElementById('plansContainer').innerHTML = html;
    } catch (error) {
        console.error('Error loading plans:', error);
        showNotification('Failed to load plans', 'error');
    }
}

async function initiatePayment(planId, amount) {
    try {
        const orderResponse = await fetch('/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan_id: planId })
        });
        
        const orderData = await orderResponse.json();
        
        if (orderData.status !== 'success') {
            showNotification('Error creating order: ' + orderData.message, 'error');
            return;
        }
        
        const options = {
            key: orderData.key,
            amount: orderData.amount,
            currency: 'INR',
            name: 'AI Job Matcher Pro',
            description: orderData.plan_name,
            order_id: orderData.order_id,
            handler: async function(response) {
                await verifyPayment(response, planId);
            },
            prefill: {
                email: document.body.dataset.userEmail || '',
                contact: document.body.dataset.userPhone || ''
            },
            theme: {
                color: '#667eea'
            }
        };
        
        const razorpay = new Razorpay(options);
        razorpay.open();
    } catch (error) {
        console.error('Payment error:', error);
        showNotification('Error initiating payment', 'error');
    }
}

async function verifyPayment(response, planId) {
    try {
        const verifyResponse = await fetch('/verify-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_signature: response.razorpay_signature,
                plan_id: planId
            })
        });
        
        const result = await verifyResponse.json();
        
        if (result.status === 'success') {
            closeUpgradeModal();
            showNotification('✅ Payment successful! Your premium plan is now active.', 'success');
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            showNotification('❌ Payment verification failed: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('Verification error:', error);
        showNotification('Error verifying payment', 'error');
    }
}

// ── Notification Toast ──
function showNotification(message, type = 'info') {
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();

    const colors = {
        success: { bg: 'rgba(72,187,120,0.15)', border: 'rgba(72,187,120,0.4)', color: '#68d391' },
        error: { bg: 'rgba(252,129,129,0.15)', border: 'rgba(252,129,129,0.4)', color: '#fc8181' },
        info: { bg: 'rgba(102,126,234,0.15)', border: 'rgba(102,126,234,0.4)', color: '#a78bfa' }
    };

    const c = colors[type] || colors.info;
    const icons = { success: 'check-circle', error: 'exclamation-circle', info: 'info-circle' };

    const notif = document.createElement('div');
    notif.className = 'notification';
    notif.style.cssText = `
        position: fixed; top: 80px; right: 20px; z-index: 9999;
        background: ${c.bg}; border: 1px solid ${c.border};
        color: ${c.color}; padding: 12px 20px; border-radius: 12px;
        font-size: 0.88rem; font-weight: 500; max-width: 350px;
        backdrop-filter: blur(20px); display: flex; align-items: center;
        gap: 8px; animation: slideIn 0.3s ease;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    `;
    notif.innerHTML = `<i class="fas fa-${icons[type]}"></i> ${message}`;
    document.body.appendChild(notif);

    setTimeout(() => {
        notif.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notif.remove(), 300);
    }, 4000);
}

// ── Helper Functions ──
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ── CSS Animations ──
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideOut {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(20px); }
    }
    
    /* Upgrade Modal Styles */
    .upgrade-modal {
        position: fixed;
        top: 0; left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        backdrop-filter: blur(5px);
    }
    
    .upgrade-modal.hidden {
        display: none;
    }
    
    .upgrade-modal-content {
        background: rgba(10,10,15,0.95);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 24px;
        padding: 2.5rem;
        max-width: 1000px;
        width: 90%;
        max-height: 90vh;
        overflow-y: auto;
        backdrop-filter: blur(20px);
        position: relative;
    }
    
    .modal-close {
        position: absolute;
        top: 20px;
        right: 20px;
        background: rgba(255,255,255,0.08);
        border: none;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        font-size: 24px;
        cursor: pointer;
        transition: all 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .modal-close:hover {
        background: rgba(255,255,255,0.15);
    }
    
    .modal-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .modal-header h2 {
        font-size: 2rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.5rem;
    }
    
    .modal-header p {
        color: rgba(255,255,255,0.6);
        font-size: 1rem;
    }
    
    .plans-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .plan-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.8rem;
        text-align: center;
        position: relative;
        transition: all 0.3s;
    }
    
    .plan-card:hover {
        border-color: rgba(102,126,234,0.4);
        transform: translateY(-4px);
        box-shadow: 0 8px 32px rgba(102,126,234,0.15);
    }
    
    .plan-card.popular {
        border-color: rgba(102,126,234,0.6);
        background: rgba(102,126,234,0.08);
    }
    
    .popular-badge {
        position: absolute;
        top: -12px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 4px 16px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    
    .plan-card h3 {
        font-size: 1.2rem;
        font-weight: 600;
        color: white;
        margin-bottom: 0.5rem;
    }
    
    .plan-price {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem;
    }
    
    .plan-duration {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.5);
        margin-bottom: 1rem;
    }
    
    .plan-features {
        list-style: none;
        margin: 1rem 0;
        text-align: left;
    }
    
    .plan-features li {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.7);
        padding: 6px 0;
    }
    
    .plan-btn {
        width: 100%;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s;
        margin-top: 1rem;
    }
    
    .plan-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(102,126,234,0.4);
    }
    
    .modal-footer {
        text-align: center;
        border-top: 1px solid rgba(255,255,255,0.06);
        padding-top: 1.5rem;
    }
`;
document.head.appendChild(style);