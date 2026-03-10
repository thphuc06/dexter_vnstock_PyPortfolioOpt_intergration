# ============================================================
# Dexter + VNStock — Single Container (Option 2 / Supervisord)
# ============================================================
# Runtime layout:
#   supervisord
#   ├── vnstock   (uvicorn + FastAPI)   → localhost:8050
#   └── dexter   (bun server.ts)        → 0.0.0.0:3000
# ============================================================

FROM python:3.11-slim

# Avoid interactive apt prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.bun/bin:$PATH"

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Bun installer needs curl + unzip
    curl \
    unzip \
    # Process supervisor
    supervisor \
    # Playwright / Chromium runtime libs
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxss1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# ── Install Bun ──────────────────────────────────────────────
RUN curl -fsSL https://bun.sh/install | bash

# ── Python dependencies ──────────────────────────────────────
# VNStock service (FastAPI + vnstock lib)
COPY vnstock/requirements.txt /tmp/vnstock-requirements.txt
# PyPortfolioOpt (portfolio optimizer called via spawn)
COPY dexter/src/investment_advisor/python/requirements.txt /tmp/pypfopt-requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/vnstock-requirements.txt \
    -r /tmp/pypfopt-requirements.txt

# ── Bun / Node dependencies ──────────────────────────────────
WORKDIR /app/dexter
COPY dexter/package.json dexter/bun.lock* ./
RUN bun install --frozen-lockfile

# Install Playwright Chromium browser (baked into image)
RUN bunx playwright install chromium --with-deps 2>/dev/null || \
    bunx playwright install chromium

# ── Copy source code ─────────────────────────────────────────
COPY dexter/ /app/dexter/
COPY vnstock/ /app/vnstock/

# ── Supervisord config ────────────────────────────────────────
COPY supervisord.conf /etc/supervisor/conf.d/dexter-all.conf

# App Runner expects port 3000
EXPOSE 3000

# Health check — App Runner pings /health
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fs http://localhost:3000/health || exit 1

CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
