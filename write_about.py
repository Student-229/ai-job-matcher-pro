content = open('templates/about.html', 'w', encoding='utf-8')
content.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - AI Job Matcher Pro</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <div class="nav-logo">
                <div class="logo-icon">🤖</div>
                <span class="logo-text">AI Job Matcher <span class="pro-badge">PRO</span></span>
            </div>
            <div class="nav-links">
                <a href="/">Home</a>
                <a href="/#features">Features</a>
                <a href="/about">About</a>
                <a href="/#upload-section" class="nav-cta">Try Free</a>
            </div>
        </div>
    </nav>

    <section class="hero" style="min-height:50vh; padding-top:8rem;">
        <div class="hero-bg">
            <div class="hero-orb orb1"></div>
            <div class="hero-orb orb2"></div>
        </div>
        <div class="hero-content">
            <div class="hero-badge">
                <span class="badge-dot"></span>
                About This Project
            </div>
            <h1 class="hero-title" style="font-size:2.5rem;">
                About <span class="gradient-text">AI Job Matcher Pro</span>
            </h1>
            <p class="hero-subtitle">
                A smart AI-powered tool that helps job seekers find their perfect career match
            </p>
        </div>
    </section>

    <section style="padding:4rem 0;">
        <div class="container">

            <div class="result-card" style="margin-bottom:2rem;">
                <div class="card-header">
                    <h3><i class="fas fa-info-circle"></i> What is AI Job Matcher Pro?</h3>
                </div>
                <p style="color:rgba(255,255,255,0.7); line-height:1.8; font-size:0.95rem;">
                    AI Job Matcher Pro is an intelligent career matching platform that uses
                    advanced AI to analyze your resume and match you with the most suitable
                    job opportunities. Simply upload your PDF resume and our AI will extract
                    your skills, experience, and education then match you with the best jobs
                    from our database instantly.
                </p>
            </div>

            <div class="result-card" style="margin-bottom:2rem;">
                <div class="card-header">
                    <h3><i class="fas fa-cogs"></i> How Does It Work?</h3>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px,1fr)); gap:1rem;">
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:1.2rem; text-align:center;">
                        <div style="font-size:2rem; margin-bottom:0.8rem;">📄</div>
                        <h4 style="color:white; margin-bottom:0.5rem;">PDF Parsing</h4>
                        <p style="color:rgba(255,255,255,0.5); font-size:0.82rem;">Advanced PDF reading extracts all text from your resume</p>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:1.2rem; text-align:center;">
                        <div style="font-size:2rem; margin-bottom:0.8rem;">🤖</div>
                        <h4 style="color:white; margin-bottom:0.5rem;">AI Analysis</h4>
                        <p style="color:rgba(255,255,255,0.5); font-size:0.82rem;">Groq AI LLaMA 3.3 intelligently extracts skills</p>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:1.2rem; text-align:center;">
                        <div style="font-size:2rem; margin-bottom:0.8rem;">🎯</div>
                        <h4 style="color:white; margin-bottom:0.5rem;">Smart Matching</h4>
                        <p style="color:rgba(255,255,255,0.5); font-size:0.82rem;">Algorithm matches skills with 20 plus job categories</p>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:1.2rem; text-align:center;">
                        <div style="font-size:2rem; margin-bottom:0.8rem;">💡</div>
                        <h4 style="color:white; margin-bottom:0.5rem;">Gap Analysis</h4>
                        <p style="color:rgba(255,255,255,0.5); font-size:0.82rem;">AI tells exactly what to learn for your dream job</p>
                    </div>
                </div>
            </div>

            <div class="result-card" style="margin-bottom:2rem;">
                <div class="card-header">
                    <h3><i class="fas fa-code"></i> Technology Used</h3>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:10px;">
                    <span class="skill-tag">Python</span>
                    <span class="skill-tag">Flask</span>
                    <span class="skill-tag">Groq AI</span>
                    <span class="skill-tag">LLaMA 3.3</span>
                    <span class="skill-tag">pdfplumber</span>
                    <span class="skill-tag">HTML5</span>
                    <span class="skill-tag">CSS3</span>
                    <span class="skill-tag">JavaScript</span>
                    <span class="skill-tag">Pandas</span>
                </div>
            </div>

            <div class="result-card" style="margin-bottom:2rem;">
                <div class="card-header">
                    <h3><i class="fas fa-shield-alt"></i> Privacy and Security</h3>
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                    <div class="tip-item">
                        <span class="tip-icon">🔒</span>
                        <span style="color:rgba(255,255,255,0.7); font-size:0.88rem;">Your resume is never stored on our servers</span>
                    </div>
                    <div class="tip-item">
                        <span class="tip-icon">🗑️</span>
                        <span style="color:rgba(255,255,255,0.7); font-size:0.88rem;">All data deleted after analysis</span>
                    </div>
                    <div class="tip-item">
                        <span class="tip-icon">🔐</span>
                        <span style="color:rgba(255,255,255,0.7); font-size:0.88rem;">No personal data shared with third parties</span>
                    </div>
                    <div class="tip-item">
                        <span class="tip-icon">✅</span>
                        <span style="color:rgba(255,255,255,0.7); font-size:0.88rem;">100 percent safe and secure to use</span>
                    </div>
                </div>
            </div>

            <div style="text-align:center; padding:2rem;">
                <a href="/#upload-section" class="hero-cta">
                    <i class="fas fa-rocket"></i>
                    Try It Now - Its Free
                </a>
            </div>
        </div>
    </section>

    <footer class="footer">
        <div class="container">
            <div class="footer-content">
                <div class="footer-logo">
                    <span>🤖 AI Job Matcher Pro</span>
                    <p>Helping people find their perfect career with AI</p>
                </div>
                <div class="footer-links">
                    <a href="/">Home</a>
                    <a href="/about">About</a>
                    <a href="/#features">Features</a>
                </div>
            </div>
            <div class="footer-bottom">
                <p>2026 AI Job Matcher Pro - Made with love using Flask and Groq AI</p>
            </div>
        </div>
    </footer>
</body>
</html>""")
content.close()
print("About page created successfully!")
