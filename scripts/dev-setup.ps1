# SkySentinel Development Setup Script (PowerShell)
# This script sets up the development environment for SkySentinel

param(
    [switch]$SkipDocker,
    [switch]$SkipPython,
    [switch]$AutoStart
)

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    White = "White"
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Colors.Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor $Colors.Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Colors.Red
}

function Write-Header {
    param([string]$Message)
    Write-Host "================================" -ForegroundColor $Colors.Blue
    Write-Host "$Message" -ForegroundColor $Colors.Blue
    Write-Host "================================" -ForegroundColor $Colors.Blue
}

# Check if Docker is installed
function Test-Docker {
    if (-not $SkipDocker) {
        try {
            $null = Get-Command docker -ErrorAction Stop
            $null = Get-Command docker-compose -ErrorAction Stop
            Write-Status "Docker and Docker Compose are installed"
        }
        catch {
            Write-Error "Docker or Docker Compose is not installed. Please install Docker Desktop first."
            exit 1
        }
    }
}

# Check if Python is installed
function Test-Python {
    if (-not $SkipPython) {
        try {
            $pythonVersion = python --version 2>&1
            Write-Status "Python $pythonVersion is installed"
        }
        catch {
            Write-Error "Python is not installed. Please install Python 3 first."
            exit 1
        }
    }
}

# Create virtual environment
function New-VirtualEnvironment {
    Write-Header "Creating Python Virtual Environment"
    
    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Status "Virtual environment created"
    }
    else {
        Write-Status "Virtual environment already exists"
    }
    
    # Activate virtual environment
    & .\venv\Scripts\Activate.ps1
    Write-Status "Virtual environment activated"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    Write-Status "Pip upgraded"
}

# Install Python dependencies
function Install-Dependencies {
    Write-Header "Installing Python Dependencies"
    
    # Install shared dependencies
    if (Test-Path "shared\requirements.txt") {
        pip install -r shared\requirements.txt
        Write-Status "Shared dependencies installed"
    }
    
    # Install graph engine dependencies
    if (Test-Path "graph-engine\requirements.txt") {
        pip install -r graph-engine\requirements.txt
        Write-Status "Graph engine dependencies installed"
    }
    
    # Install event collector dependencies
    if (Test-Path "event-collectors\aws\requirements.txt") {
        pip install -r event-collectors\aws\requirements.txt
        Write-Status "AWS event collector dependencies installed"
    }
    
    if (Test-Path "event-collectors\mock\requirements.txt") {
        pip install -r event-collectors\mock\requirements.txt
        Write-Status "Mock event collector dependencies installed"
    }
}

# Create environment files
function New-EnvironmentFiles {
    Write-Header "Creating Environment Files"
    
    # Create .env file for development
    if (-not (Test-Path ".env")) {
        @"
# SkySentinel Development Environment Variables

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=skysentinel

# AWS Configuration (for real AWS integration)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Development Settings
LOG_LEVEL=DEBUG
FLASK_ENV=development
FLASK_DEBUG=1

# Mock Configuration
MOCK_AWS_ACCOUNTS=123456789012,123456789013
MOCK_SERVICES=ec2,s3,iam,rds,lambda
EVENT_GENERATION_INTERVAL=5
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Status ".env file created"
    }
    else {
        Write-Status ".env file already exists"
    }
    
    # Create .env.local file for local overrides
    if (-not (Test-Path ".env.local")) {
        @"
# Local environment overrides
# This file is not tracked in git
"@ | Out-File -FilePath ".env.local" -Encoding UTF8
        Write-Status ".env.local file created"
    }
}

# Create development directories
function New-DevelopmentDirectories {
    Write-Header "Creating Development Directories"
    
    $dirs = @(
        "logs",
        "data\neo4j",
        "data\redis",
        "data\prometheus",
        "data\grafana"
    )
    
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Status "Development directories created"
}

# Build Docker images
function Build-DockerImages {
    Write-Header "Building Docker Images"
    
    docker-compose -f docker-compose.dev.yml build
    
    Write-Status "Docker images built successfully"
}

# Start development environment
function Start-DevelopmentEnvironment {
    Write-Header "Starting Development Environment"
    
    docker-compose -f docker-compose.dev.yml up -d
    
    Write-Status "Development environment started"
    
    # Wait for Neo4j to be ready
    Write-Status "Waiting for Neo4j to be ready..."
    Start-Sleep -Seconds 30
    
    # Check if Neo4j is accessible
    try {
        $result = docker-compose -f docker-compose.dev.yml exec -T neo4j cypher-shell -u neo4j -p skysentinel "RETURN 1" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Neo4j is ready"
        }
        else {
            Write-Warning "Neo4j might not be fully ready yet"
        }
    }
    catch {
        Write-Warning "Neo4j might not be fully ready yet"
    }
}

# Show development URLs
function Show-DevelopmentURLs {
    Write-Header "Development URLs"
    
    Write-Host "Neo4j Browser:     http://localhost:7474" -ForegroundColor $Colors.Green
    Write-Host "Neo4j Bolt:        bolt://localhost:7687" -ForegroundColor $Colors.Green
    Write-Host "API Gateway:        http://localhost:3000" -ForegroundColor $Colors.Green
    Write-Host "Graph Engine:       http://localhost:8080" -ForegroundColor $Colors.Green
    Write-Host "Dashboard:          http://localhost:3001" -ForegroundColor $Colors.Green
    Write-Host "Mock Collector:     http://localhost:8081" -ForegroundColor $Colors.Green
    Write-Host "Prometheus:         http://localhost:9090" -ForegroundColor $Colors.Green
    Write-Host "Grafana:           http://localhost:3002" -ForegroundColor $Colors.Green
    Write-Host "Redis:             localhost:6379" -ForegroundColor $Colors.Green
    
    Write-Host ""
    Write-Host "Default Credentials:" -ForegroundColor $Colors.Yellow
    Write-Host "Neo4j:           neo4j / skysentinel" -ForegroundColor $Colors.Yellow
    Write-Host "Grafana:          admin / skysentinel" -ForegroundColor $Colors.Yellow
}

# Create helper scripts
function New-HelperScripts {
    Write-Header "Creating Helper Scripts"
    
    # Create start script
    @"
@echo off
echo Starting SkySentinel development environment...
docker-compose -f docker-compose.dev.yml up -d
echo Development environment started!
call scripts\show-urls.bat
"@ | Out-File -FilePath "scripts\start-dev.bat" -Encoding ASCII
    
    # Create stop script
    @"
@echo off
echo Stopping SkySentinel development environment...
docker-compose -f docker-compose.dev.yml down
echo Development environment stopped!
"@ | Out-File -FilePath "scripts\stop-dev.bat" -Encoding ASCII
    
    # Create logs script
    @"
@echo off
if "%1"=="" (
    echo Usage: %1 ^<service-name^>
    echo Available services: neo4j, graph-engine, api-gateway, dashboard, event-collector-mock, redis, prometheus, grafana
    exit /b 1
)
docker-compose -f docker-compose.dev.yml logs -f %1
"@ | Out-File -FilePath "scripts\logs.bat" -Encoding ASCII
    
    # Create reset script
    @"
@echo off
echo Resetting SkySentinel development environment...
docker-compose -f docker-compose.dev.yml down -v
docker system prune -f
echo Development environment reset!
"@ | Out-File -FilePath "scripts\reset-dev.bat" -Encoding ASCII
    
    Write-Status "Helper scripts created"
}

# Main execution
function Main {
    Write-Header "SkySentinel Development Setup"
    
    Test-Docker
    Test-Python
    New-VirtualEnvironment
    Install-Dependencies
    New-EnvironmentFiles
    New-DevelopmentDirectories
    New-HelperScripts
    
    if ($AutoStart) {
        Build-DockerImages
        Start-DevelopmentEnvironment
        Show-DevelopmentURLs
    }
    else {
        $response = Read-Host "Do you want to build and start the development environment? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Build-DockerImages
            Start-DevelopmentEnvironment
            Show-DevelopmentURLs
        }
        else {
            Write-Status "Setup complete. Run 'scripts\start-dev.bat' to start the development environment."
        }
    }
    
    Write-Header "Setup Complete!"
    Write-Status "SkySentinel development environment is ready!"
}

# Run main function
Main
