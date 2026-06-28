"""FastAPI application entry point with landing page, dashboard, and API docs."""
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.routers import auth, openai_proxy, admin
from prometheus_client import make_asgi_app

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="OpenAI-compatible API gateway with API key management, backed by LocalAI",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
# Add a direct route to avoid potential mount-related redirects
@app.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc) if settings.DEBUG else "Something went wrong"}
    )


# ============ LANDING PAGE ============

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Beautiful landing page for the API gateway."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LocalAI Gateway — OpenAI-Compatible API</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            --bg: #0a0a0f;
            --bg-card: #12121a;
            --bg-elevated: #1a1a28;
            --border: #252538;
            --text: #e2e2f0;
            --text-muted: #8b8ba7;
            --primary: #6366f1;
            --primary-glow: rgba(99,102,241,0.3);
            --secondary: #a855f7;
            --accent: #22d3ee;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            overflow-x: hidden;
        }
        .gradient-bg {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: 
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.15), transparent),
                radial-gradient(ellipse 60% 40% at 80% 50%, rgba(168,85,247,0.1), transparent),
                radial-gradient(ellipse 50% 30% at 20% 80%, rgba(34,211,238,0.08), transparent);
            pointer-events: none; z-index: 0;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 24px; position: relative; z-index: 1; }

        /* Navbar */
        .navbar {
            position: fixed; top: 0; width: 100%; z-index: 100;
            background: rgba(10,10,15,0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
        }
        .navbar-inner { display: flex; align-items: center; justify-content: space-between; height: 64px; }
        .logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.2rem; }
        .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--primary), var(--secondary)); border-radius: 8px; display: flex; align-items: center; justify-content: center; }
        .logo-icon i { color: white; font-size: 14px; }
        .nav-links { display: flex; gap: 32px; align-items: center; }
        .nav-links a { color: var(--text-muted); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: color 0.2s; }
        .nav-links a:hover { color: var(--text); }
        .nav-cta {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white !important; padding: 8px 20px; border-radius: 8px;
            font-weight: 600; font-size: 0.85rem; border: none; cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .nav-cta:hover { transform: translateY(-1px); box-shadow: 0 4px 20px var(--primary-glow); }

        /* Hero */
        .hero { padding: 160px 0 100px; text-align: center; }
        .hero-badge {
            display: inline-flex; align-items: center; gap: 8px;
            background: var(--bg-elevated); border: 1px solid var(--border);
            padding: 6px 16px; border-radius: 100px; font-size: 0.8rem;
            color: var(--accent); margin-bottom: 32px;
        }
        .hero-badge .dot { width: 6px; height: 6px; background: var(--success); border-radius: 50%; animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        .hero h1 { font-size: 4rem; font-weight: 800; line-height: 1.1; margin-bottom: 24px; letter-spacing: -0.02em; }
        .hero h1 span { background: linear-gradient(135deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
        .hero p { font-size: 1.25rem; color: var(--text-muted); max-width: 600px; margin: 0 auto 40px; }
        .hero-cta { display: flex; gap: 16px; justify-content: center; margin-bottom: 60px; }
        .btn {
            padding: 14px 32px; border-radius: 12px; font-weight: 600; font-size: 0.95rem;
            text-decoration: none; transition: all 0.2s; cursor: pointer; border: none;
            display: inline-flex; align-items: center; gap: 8px;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white; box-shadow: 0 4px 20px var(--primary-glow);
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px var(--primary-glow); }
        .btn-secondary {
            background: var(--bg-elevated); color: var(--text);
            border: 1px solid var(--border);
        }
        .btn-secondary:hover { background: var(--border); }

        /* Code Block */
        .code-block {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 16px; padding: 24px; max-width: 700px; margin: 0 auto;
            font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
            position: relative; overflow: hidden;
        }
        .code-block::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, var(--primary), var(--accent), transparent);
        }
        .code-header { display: flex; gap: 8px; margin-bottom: 16px; }
        .code-dot { width: 12px; height: 12px; border-radius: 50%; }
        .code-dot.red { background: var(--danger); }
        .code-dot.yellow { background: var(--warning); }
        .code-dot.green { background: var(--success); }
        .code-content { color: var(--text-muted); line-height: 1.8; }
        .code-content .comment { color: #6b7280; }
        .code-content .keyword { color: var(--accent); }
        .code-content .string { color: var(--success); }
        .code-content .var { color: var(--secondary); }

        /* Features */
        .features { padding: 100px 0; }
        .section-header { text-align: center; margin-bottom: 60px; }
        .section-header h2 { font-size: 2.5rem; font-weight: 700; margin-bottom: 12px; }
        .section-header p { color: var(--text-muted); font-size: 1.1rem; }
        .features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; }
        .feature-card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 16px; padding: 32px; transition: all 0.3s;
        }
        .feature-card:hover {
            border-color: var(--primary); transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .feature-icon {
            width: 48px; height: 48px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 20px; font-size: 1.2rem;
        }
        .feature-icon.purple { background: rgba(99,102,241,0.15); color: var(--primary); }
        .feature-icon.cyan { background: rgba(34,211,238,0.15); color: var(--accent); }
        .feature-icon.green { background: rgba(34,197,94,0.15); color: var(--success); }
        .feature-icon.orange { background: rgba(245,158,11,0.15); color: var(--warning); }
        .feature-card h3 { font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }
        .feature-card p { color: var(--text-muted); font-size: 0.9rem; }

        /* Endpoints */
        .endpoints { padding: 100px 0; }
        .endpoints-table {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 16px; overflow: hidden;
        }
        .endpoint-row {
            display: grid; grid-template-columns: 100px 1fr 200px;
            padding: 16px 24px; border-bottom: 1px solid var(--border);
            align-items: center; transition: background 0.2s;
        }
        .endpoint-row:hover { background: var(--bg-elevated); }
        .endpoint-row:last-child { border-bottom: none; }
        .method { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 6px; text-align: center; }
        .method.get { background: rgba(34,197,94,0.15); color: var(--success); }
        .method.post { background: rgba(99,102,241,0.15); color: var(--primary); }
        .method.delete { background: rgba(239,68,68,0.15); color: var(--danger); }
        .endpoint-path { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text); }
        .endpoint-desc { color: var(--text-muted); font-size: 0.85rem; }

        /* Footer */
        .footer {
            border-top: 1px solid var(--border); padding: 40px 0;
            text-align: center; color: var(--text-muted); font-size: 0.85rem;
        }

        @media (max-width: 768px) {
            .hero h1 { font-size: 2.5rem; }
            .hero-cta { flex-direction: column; align-items: center; }
            .nav-links { display: none; }
            .endpoint-row { grid-template-columns: 80px 1fr; gap: 8px; }
            .endpoint-desc { grid-column: 1 / -1; }
        }
    </style>
</head>
<body>
    <div class="gradient-bg"></div>

    <nav class="navbar">
        <div class="container navbar-inner">
            <div class="logo">
                <div class="logo-icon"><i class="fas fa-bolt"></i></div>
                LocalAI Gateway
            </div>
            <div class="nav-links">
                <a href="#features">Features</a>
                <a href="#endpoints">Endpoints</a>
                <a href="/docs">API Docs</a>
                <a href="/dashboard">Dashboard</a>
                <a href="/docs" class="nav-cta">Get Started</a>
            </div>
        </div>
    </nav>

    <section class="hero">
        <div class="container">
            <div class="hero-badge">
                <span class="dot"></span>
                OpenAI-Compatible API Gateway
            </div>
            <h1>Run AI <span>Locally</span>,<br>Scale Globally</h1>
            <p>A production-ready FastAPI gateway with API key management, rate limiting, and usage tracking — all backed by LocalAI and Neon PostgreSQL.</p>
            <div class="hero-cta">
                <a href="/docs" class="btn btn-primary"><i class="fas fa-rocket"></i> API Documentation</a>
                <a href="/dashboard" class="btn btn-secondary"><i class="fas fa-chart-line"></i> Dashboard</a>
            </div>
            <div class="code-block">
                <div class="code-header">
                    <span class="code-dot red"></span>
                    <span class="code-dot yellow"></span>
                    <span class="code-dot green"></span>
                </div>
                <div class="code-content">
<span class="comment"># Chat with any model</span><br>
<span class="var">curl</span> -X POST <span class="string">"/v1/chat/completions"</span> \\<br>
  -H <span class="string">"Authorization: Bearer localai_xxx"</span> \\<br>
  -d <span class="string">'{"model":"gpt-4","messages":[{"role":"user","content":"Hello!"}]}'</span>
                </div>
            </div>
        </div>
    </section>

    <section class="features" id="features">
        <div class="container">
            <div class="section-header">
                <h2>Everything You Need</h2>
                <p>Built for production deployments with enterprise-grade features</p>
            </div>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon purple"><i class="fas fa-key"></i></div>
                    <h3>API Key Management</h3>
                    <p>Create, revoke, and manage API keys with per-key rate limits and expiration dates. All stored securely in Neon PostgreSQL.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon cyan"><i class="fas fa-bolt"></i></div>
                    <h3>OpenAI Compatible</h3>
                    <p>Drop-in replacement for OpenAI API. Chat completions, embeddings, audio, images, assistants, threads — all supported.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon green"><i class="fas fa-shield-halved"></i></div>
                    <h3>Rate Limiting</h3>
                    <p>Token bucket rate limiting per API key with configurable requests per minute and burst capacity.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon orange"><i class="fas fa-chart-bar"></i></div>
                    <h3>Usage Analytics</h3>
                    <p>Track every request with tokens, latency, endpoints, and models. Full visibility into your AI usage.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon purple"><i class="fas fa-server"></i></div>
                    <h3>LocalAI Backend</h3>
                    <p>Run models locally with LocalAI. No data leaves your infrastructure. Full privacy and control.</p>
                </div>
                <div class="feature-card">
                    <div class="feature-icon cyan"><i class="fas fa-cloud"></i></div>
                    <h3>Fly.io Deploy</h3>
                    <p>One-command deployment to Fly.io with auto-scaling, health checks, and zero-downtime updates.</p>
                </div>
            </div>
        </div>
    </section>

    <section class="endpoints" id="endpoints">
        <div class="container">
            <div class="section-header">
                <h2>Supported Endpoints</h2>
                <p>Full OpenAI API compatibility with LocalAI backend</p>
            </div>
            <div class="endpoints-table">
                <div class="endpoint-row">
                    <span class="method get">GET</span>
                    <span class="endpoint-path">/v1/models</span>
                    <span class="endpoint-desc">List available models</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/chat/completions</span>
                    <span class="endpoint-desc">Chat completions (streaming supported)</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/completions</span>
                    <span class="endpoint-desc">Legacy text completions</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/embeddings</span>
                    <span class="endpoint-desc">Text embeddings</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/audio/transcriptions</span>
                    <span class="endpoint-desc">Speech-to-text (Whisper)</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/audio/speech</span>
                    <span class="endpoint-desc">Text-to-speech</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/images/generations</span>
                    <span class="endpoint-desc">Image generation</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/files</span>
                    <span class="endpoint-desc">File upload</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/assistants</span>
                    <span class="endpoint-desc">Create assistant</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/threads</span>
                    <span class="endpoint-desc">Create thread</span>
                </div>
                <div class="endpoint-row">
                    <span class="method post">POST</span>
                    <span class="endpoint-path">/v1/fine_tuning/jobs</span>
                    <span class="endpoint-desc">Fine-tuning jobs</span>
                </div>
            </div>
        </div>
    </section>

    <footer class="footer">
        <div class="container">
            <p>Built with FastAPI + LocalAI + Neon PostgreSQL. Deployed on Fly.io.</p>
        </div>
    </footer>
</body>
</html>
    """


# ============ SWAGGER UI (Custom Styled) ============

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Custom Swagger UI with dark theme."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="/favicon.ico",
        init_oauth={},
        swagger_ui_parameters={
            "deepLinking": True,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
        },
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc API documentation."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
        redoc_favicon_url="/favicon.ico",
    )


# ============ DASHBOARD ============

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Admin dashboard for monitoring API usage and keys."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard — LocalAI Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        :root {
            --bg: #0a0a0f; --bg-card: #12121a; --bg-elevated: #1a1a28;
            --border: #252538; --text: #e2e2f0; --text-muted: #8b8ba7;
            --primary: #6366f1; --primary-glow: rgba(99,102,241,0.3);
            --secondary: #a855f7; --accent: #22d3ee;
            --success: #22c55e; --warning: #f59e0b; --danger: #ef4444;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); }
        .dashboard { display: flex; min-height: 100vh; }

        /* Sidebar */
        .sidebar {
            width: 260px; background: var(--bg-card); border-right: 1px solid var(--border);
            padding: 24px; position: fixed; height: 100vh; overflow-y: auto;
        }
        .sidebar-logo { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.1rem; margin-bottom: 40px; }
        .sidebar-logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, var(--primary), var(--secondary)); border-radius: 8px; display: flex; align-items: center; justify-content: center; }
        .sidebar-logo-icon i { color: white; font-size: 14px; }
        .nav-section { margin-bottom: 24px; }
        .nav-section-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 12px; padding-left: 12px; }
        .nav-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 8px; color: var(--text-muted); text-decoration: none; font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: all 0.2s; margin-bottom: 4px; }
        .nav-item:hover, .nav-item.active { background: var(--bg-elevated); color: var(--text); }
        .nav-item i { width: 20px; text-align: center; }
        .nav-item.active { border-left: 3px solid var(--primary); }

        /* Main Content */
        .main { flex: 1; margin-left: 260px; padding: 32px 40px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
        .header h1 { font-size: 1.5rem; font-weight: 700; }
        .header-actions { display: flex; gap: 12px; }
        .btn-sm { padding: 8px 16px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
        .btn-primary-sm { background: linear-gradient(135deg, var(--primary), var(--secondary)); color: white; }
        .btn-secondary-sm { background: var(--bg-elevated); color: var(--text); border: 1px solid var(--border); }

        /* Stats Cards */
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px; }
        .stat-card {
            background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px;
            padding: 24px; position: relative; overflow: hidden;
        }
        .stat-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        }
        .stat-card.primary::before { background: linear-gradient(90deg, var(--primary), var(--secondary)); }
        .stat-card.success::before { background: linear-gradient(90deg, var(--success), var(--accent)); }
        .stat-card.warning::before { background: linear-gradient(90deg, var(--warning), var(--danger)); }
        .stat-card.accent::before { background: linear-gradient(90deg, var(--accent), var(--primary)); }
        .stat-label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
        .stat-value { font-size: 2rem; font-weight: 700; margin-bottom: 4px; }
        .stat-change { font-size: 0.8rem; display: flex; align-items: center; gap: 4px; }
        .stat-change.up { color: var(--success); }
        .stat-change.down { color: var(--danger); }

        /* Charts */
        .chart-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; margin-bottom: 24px; }
        .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .chart-header h3 { font-size: 1rem; font-weight: 600; }
        .chart-filters { display: flex; gap: 8px; }
        .filter-btn { padding: 4px 12px; border-radius: 6px; font-size: 0.75rem; border: 1px solid var(--border); background: transparent; color: var(--text-muted); cursor: pointer; }
        .filter-btn.active { background: var(--primary); color: white; border-color: var(--primary); }

        /* Tables */
        .table-container { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; }
        .table-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; border-bottom: 1px solid var(--border); }
        .table-header h3 { font-size: 1rem; font-weight: 600; }
        .search-box { background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; color: var(--text); font-size: 0.85rem; width: 240px; }
        .search-box::placeholder { color: var(--text-muted); }
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; padding: 12px 24px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600; border-bottom: 1px solid var(--border); }
        td { padding: 14px 24px; font-size: 0.85rem; border-bottom: 1px solid var(--border); }
        tr:last-child td { border-bottom: none; }
        tr:hover td { background: var(--bg-elevated); }
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
        .badge-success { background: rgba(34,197,94,0.15); color: var(--success); }
        .badge-warning { background: rgba(245,158,11,0.15); color: var(--warning); }
        .badge-danger { background: rgba(239,68,68,0.15); color: var(--danger); }
        .badge-info { background: rgba(99,102,241,0.15); color: var(--primary); }
        .key-prefix { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--accent); }
        .action-btn { background: transparent; border: none; color: var(--text-muted); cursor: pointer; padding: 4px; transition: color 0.2s; }
        .action-btn:hover { color: var(--text); }

        /* Responsive */
        @media (max-width: 1024px) {
            .sidebar { transform: translateX(-100%); transition: transform 0.3s; }
            .main { margin-left: 0; }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <aside class="sidebar">
            <div class="sidebar-logo">
                <div class="sidebar-logo-icon"><i class="fas fa-bolt"></i></div>
                LocalAI Gateway
            </div>
            <div class="nav-section">
                <div class="nav-section-title">Overview</div>
                <a href="#" class="nav-item active" onclick="showSection('overview')">
                    <i class="fas fa-chart-pie"></i> Dashboard
                </a>
                <a href="#" class="nav-item" onclick="showSection('analytics')">
                    <i class="fas fa-chart-line"></i> Analytics
                </a>
                <a href="#" class="nav-item" onclick="showSection('logs')">
                    <i class="fas fa-list"></i> Request Logs
                </a>
            </div>
            <div class="nav-section">
                <div class="nav-section-title">Management</div>
                <a href="#" class="nav-item" onclick="showSection('keys')">
                    <i class="fas fa-key"></i> API Keys
                </a>
                <a href="#" class="nav-item" onclick="showSection('models')">
                    <i class="fas fa-brain"></i> Models
                </a>
                <a href="#" class="nav-item" onclick="showSection('settings')">
                    <i class="fas fa-cog"></i> Settings
                </a>
            </div>
            <div class="nav-section">
                <div class="nav-section-title">Resources</div>
                <a href="/docs" class="nav-item" target="_blank">
                    <i class="fas fa-book"></i> API Docs
                </a>
                <a href="/" class="nav-item">
                    <i class="fas fa-home"></i> Landing Page
                </a>
            </div>
        </aside>

        <main class="main">
            <div class="header">
                <h1>Dashboard</h1>
                <div class="header-actions">
                    <button class="btn-secondary-sm" onclick="refreshData()"><i class="fas fa-refresh"></i> Refresh</button>
                    <button class="btn-primary-sm" onclick="createKey()"><i class="fas fa-plus"></i> New API Key</button>
                </div>
            </div>

            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card primary">
                    <div class="stat-label">Total Requests</div>
                    <div class="stat-value" id="total-requests">--</div>
                    <div class="stat-change up"><i class="fas fa-arrow-up"></i> <span id="requests-change">--%</span> vs last 7d</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-label">Total Tokens</div>
                    <div class="stat-value" id="total-tokens">--</div>
                    <div class="stat-change up"><i class="fas fa-arrow-up"></i> <span id="tokens-change">--%</span> vs last 7d</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-label">Avg Latency</div>
                    <div class="stat-value" id="avg-latency">--<span style="font-size:1rem;color:var(--text-muted)">ms</span></div>
                    <div class="stat-change down"><i class="fas fa-arrow-down"></i> <span id="latency-change">--%</span> vs last 7d</div>
                </div>
                <div class="stat-card accent">
                    <div class="stat-label">Active Keys</div>
                    <div class="stat-value" id="active-keys">--</div>
                    <div class="stat-change up"><i class="fas fa-check"></i> <span id="keys-status">All healthy</span></div>
                </div>
            </div>

            <!-- Charts -->
            <div class="chart-container">
                <div class="chart-header">
                    <h3>Request Volume</h3>
                    <div class="chart-filters">
                        <button class="filter-btn active">24h</button>
                        <button class="filter-btn">7d</button>
                        <button class="filter-btn">30d</button>
                    </div>
                </div>
                <canvas id="requestsChart" height="80"></canvas>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
                <div class="chart-container">
                    <div class="chart-header">
                        <h3>Top Models</h3>
                    </div>
                    <canvas id="modelsChart" height="200"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-header">
                        <h3>Endpoint Breakdown</h3>
                    </div>
                    <canvas id="endpointsChart" height="200"></canvas>
                </div>
            </div>

            <!-- API Keys Table -->
            <div class="table-container" style="margin-top: 24px;">
                <div class="table-header">
                    <h3>API Keys</h3>
                    <input type="text" class="search-box" placeholder="Search keys..." id="keySearch">
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Prefix</th>
                            <th>Requests</th>
                            <th>Tokens</th>
                            <th>Rate Limit</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="keysTableBody">
                        <tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:40px;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Recent Logs -->
            <div class="table-container" style="margin-top: 24px;">
                <div class="table-header">
                    <h3>Recent Requests</h3>
                    <input type="text" class="search-box" placeholder="Filter logs..." id="logSearch">
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Endpoint</th>
                            <th>Method</th>
                            <th>Model</th>
                            <th>Status</th>
                            <th>Tokens</th>
                            <th>Latency</th>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody id="logsTableBody">
                        <tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:40px;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </main>
    </div>

    <script>
        // Chart.js defaults for dark theme
        Chart.defaults.color = '#8b8ba7';
        Chart.defaults.borderColor = '#252538';
        Chart.defaults.font.family = 'Inter';

        // Mock data for demo (replace with real API calls)
        const mockStats = {
            totalRequests: 12453,
            totalTokens: 8923401,
            avgLatency: 245,
            activeKeys: 12,
            requestsChange: 23.5,
            tokensChange: 18.2,
            latencyChange: -12.3
        };

        // Update stats
        document.getElementById('total-requests').textContent = mockStats.totalRequests.toLocaleString();
        document.getElementById('total-tokens').textContent = (mockStats.totalTokens / 1000000).toFixed(1) + 'M';
        document.getElementById('avg-latency').innerHTML = mockStats.avgLatency + '<span style="font-size:1rem;color:var(--text-muted)">ms</span>';
        document.getElementById('active-keys').textContent = mockStats.activeKeys;
        document.getElementById('requests-change').textContent = mockStats.requestsChange + '%';
        document.getElementById('tokens-change').textContent = mockStats.tokensChange + '%';
        document.getElementById('latency-change').textContent = Math.abs(mockStats.latencyChange) + '%';

        // Requests Chart
        const ctx1 = document.getElementById('requestsChart').getContext('2d');
        new Chart(ctx1, {
            type: 'line',
            data: {
                labels: ['00:00','04:00','08:00','12:00','16:00','20:00','23:59'],
                datasets: [{
                    label: 'Requests',
                    data: [120, 85, 340, 520, 480, 390, 210],
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99,102,241,0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, grid: { color: '#252538' } }, x: { grid: { display: false } } }
            }
        });

        // Models Chart
        const ctx2 = document.getElementById('modelsChart').getContext('2d');
        new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: ['GPT-4', 'Claude', 'Llama', 'Other'],
                datasets: [{
                    data: [45, 30, 15, 10],
                    backgroundColor: ['#6366f1', '#a855f7', '#22d3ee', '#22c55e'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right' } }
            }
        });

        // Endpoints Chart
        const ctx3 = document.getElementById('endpointsChart').getContext('2d');
        new Chart(ctx3, {
            type: 'bar',
            data: {
                labels: ['/chat', '/embed', '/audio', '/image', '/files'],
                datasets: [{
                    label: 'Requests',
                    data: [8500, 2100, 800, 600, 453],
                    backgroundColor: ['#6366f1', '#a855f7', '#22d3ee', '#22c55e', '#f59e0b'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, grid: { color: '#252538' } }, x: { grid: { display: false } } }
            }
        });

        // Populate Keys Table
        const mockKeys = [
            { name: 'Production App', prefix: 'localai_prod...', requests: 8450, tokens: 5200000, rate: '120/min', status: 'active', created: '2026-06-20' },
            { name: 'Staging', prefix: 'localai_stag...', requests: 2100, tokens: 1200000, rate: '60/min', status: 'active', created: '2026-06-22' },
            { name: 'Dev Testing', prefix: 'localai_dev...', requests: 890, tokens: 450000, rate: '30/min', status: 'active', created: '2026-06-24' },
            { name: 'Legacy Key', prefix: 'localai_old...', requests: 1013, tokens: 2050000, rate: '60/min', status: 'revoked', created: '2026-06-01' },
        ];

        const keysBody = document.getElementById('keysTableBody');
        keysBody.innerHTML = mockKeys.map(k => `
            <tr>
                <td><strong>${k.name}</strong></td>
                <td><span class="key-prefix">${k.prefix}</span></td>
                <td>${k.requests.toLocaleString()}</td>
                <td>${(k.tokens/1000000).toFixed(1)}M</td>
                <td>${k.rate}</td>
                <td><span class="badge badge-${k.status === 'active' ? 'success' : 'danger'}">${k.status}</span></td>
                <td>${k.created}</td>
                <td>
                    <button class="action-btn" title="Edit"><i class="fas fa-pen"></i></button>
                    <button class="action-btn" title="Revoke"><i class="fas fa-ban"></i></button>
                    <button class="action-btn" title="Delete"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `).join('');

        // Populate Logs Table
        const mockLogs = [
            { time: '2 min ago', endpoint: '/v1/chat/completions', method: 'POST', model: 'gpt-4', status: 200, tokens: 452, latency: '234ms', ip: '192.168.1.1' },
            { time: '5 min ago', endpoint: '/v1/embeddings', method: 'POST', model: 'text-embedding', status: 200, tokens: 128, latency: '89ms', ip: '192.168.1.2' },
            { time: '8 min ago', endpoint: '/v1/audio/transcriptions', method: 'POST', model: 'whisper', status: 200, tokens: 0, latency: '1.2s', ip: '192.168.1.3' },
            { time: '12 min ago', endpoint: '/v1/chat/completions', method: 'POST', model: 'claude', status: 429, tokens: 0, latency: '45ms', ip: '192.168.1.4' },
            { time: '15 min ago', endpoint: '/v1/images/generations', method: 'POST', model: 'sd-xl', status: 200, tokens: 0, latency: '4.5s', ip: '192.168.1.5' },
        ];

        const logsBody = document.getElementById('logsTableBody');
        logsBody.innerHTML = mockLogs.map(l => `
            <tr>
                <td>${l.time}</td>
                <td><span class="key-prefix">${l.endpoint}</span></td>
                <td><span class="badge badge-${l.method === 'GET' ? 'info' : 'warning'}">${l.method}</span></td>
                <td>${l.model}</td>
                <td><span class="badge badge-${l.status === 200 ? 'success' : 'danger'}">${l.status}</span></td>
                <td>${l.tokens}</td>
                <td>${l.latency}</td>
                <td>${l.ip}</td>
            </tr>
        `).join('');

        function showSection(section) {
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            event.target.closest('.nav-item').classList.add('active');
        }

        function refreshData() {
            location.reload();
        }

        function createKey() {
            alert('Create key modal would open here. Use POST /auth/keys with admin key.');
        }
    </script>
</body>
</html>
    """


# ============ HEALTH & API INFO ============

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


@app.get("/api-info")
async def api_info():
    """API information and capabilities."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "OpenAI-compatible API gateway with LocalAI backend",
        "endpoints": {
            "landing": "/",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "dashboard": "/dashboard",
            "health": "/health",
            "auth": "/auth",
            "openai_api": "/v1",
            "admin": "/admin",
        },
        "features": [
            "OpenAI-compatible API",
            "API key management",
            "Rate limiting",
            "Usage tracking",
            "Streaming support",
            "Multi-model support"
        ],
        "authentication": {
            "methods": ["Bearer token", "X-API-Key header"],
            "admin_key": "Set via ADMIN_API_KEY env var"
        }
    }


# Include routers
app.include_router(auth.router)
app.include_router(openai_proxy.router)
app.include_router(admin.router)
