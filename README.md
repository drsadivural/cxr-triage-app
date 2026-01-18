# CXR Triage System

An AI-powered Chest X-ray (CXR) real-time triage and detection web application with full GUI, pretrained deep learning models, and comprehensive clinical workflow support.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Node.js](https://img.shields.io/badge/node-20.x-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## ⚠️ Disclaimer

**This system is intended for research and educational purposes only. It is NOT approved for clinical diagnostic use.**

All AI-generated findings must be reviewed and confirmed by a qualified radiologist. This tool is designed to assist clinical decision-making, not replace professional medical judgment.

## Features

### AI Analysis
- **Multi-label Classification**: Detects 18+ pathologies including pneumothorax, pleural effusion, consolidation, cardiomegaly, edema, nodules, and masses
- **Object Detection**: Localizes abnormalities with bounding boxes
- **Probability Calibration**: Calibrated confidence scores for clinical reliability
- **Triage Levels**: Automatic classification into URGENT, ROUTINE, or NORMAL

### Clinical Workflow
- **DICOM Support**: Native DICOM file handling with metadata extraction
- **Orthanc PACS Integration**: Built-in PACS server for DICOM storage and retrieval
- **Worklist Management**: Track and manage studies with filtering and pagination
- **Export Options**: JSON, PNG overlay, and DICOM SR export formats

### User Interface
- **Modern Web UI**: Next.js-based responsive interface
- **DICOM Viewer**: Cornerstone.js-powered viewer with zoom, pan, and window/level controls
- **Overlay Visualization**: Toggle bounding box overlays on images
- **Real-time Analysis**: Immediate results with processing time metrics

### Administration
- **Settings Management**: Configure AI thresholds, LLM providers, and database connections
- **Audit Logging**: Complete audit trail of all system actions
- **QA Reviews**: Track false positives/negatives for model improvement
- **Latency Metrics**: P50, P95, P99 processing time statistics

### LLM Integration (Optional)
- **Azure OpenAI**: GPT-4 integration for report enhancement
- **Anthropic Claude**: Claude 3 support
- **Google Gemini**: Gemini Pro support
- **Template Fallback**: Deterministic report generation without LLM

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Dashboard │ │ Analyze  │ │ Worklist │ │ Settings │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API (FastAPI)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Routes  │ │ Services │ │  Models  │ │  Audit   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  PostgreSQL  │    │    Redis     │    │   Orthanc    │
│   Database   │    │    Cache     │    │    PACS      │
└──────────────┘    └──────────────┘    └──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Inference Service (PyTorch)                   │
│  ┌──────────────────────┐  ┌──────────────────────┐            │
│  │   TorchXRayVision    │  │   Object Detector    │            │
│  │   (Classification)    │  │   (Localization)     │            │
│  └──────────────────────┘  └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM recommended
- GPU optional (CPU inference supported)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cxr-triage-app.git
   cd cxr-triage-app
   ```

2. **Download AI models**
   ```bash
   python scripts/download_models.py
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start the system**
   ```bash
   ./scripts/start.sh
   # Or manually:
   docker-compose up --build -d
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Orthanc PACS: http://localhost:8042

### Development Setup

For local development without Docker:

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Inference Service
cd inference
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend
pnpm install
pnpm dev
```

## API Reference

### Analysis Endpoints

#### Analyze Image
```http
POST /v1/cxr/analyze
Content-Type: multipart/form-data

file: <image_file>
async_mode: false
```

**Response:**
```json
{
  "study_id": "uuid",
  "status": "completed",
  "result": {
    "triage_level": "ROUTINE",
    "findings": [...],
    "bounding_boxes": [...],
    "report": {...}
  }
}
```

#### Get Result
```http
GET /v1/cxr/result/{study_id}
```

### Worklist Endpoints

#### List Studies
```http
GET /v1/worklist?page=1&page_size=20&triage_level=URGENT
```

#### Get Study Details
```http
GET /v1/study/{study_id}
```

### Settings Endpoints

#### Get Settings
```http
GET /v1/settings
```

#### Update Settings
```http
PUT /v1/settings
Content-Type: application/json

{
  "ai": {...},
  "llm": {...}
}
```

## Configuration

### AI Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `detector_confidence` | 0.25 | Minimum confidence for detections |
| `detector_iou` | 0.45 | IoU threshold for NMS |
| `detector_max_boxes` | 10 | Maximum bounding boxes per image |
| `calibration_enabled` | true | Enable probability calibration |

### Per-Finding Thresholds

| Finding | Triage Threshold | Strong Threshold |
|---------|-----------------|------------------|
| Pneumothorax | 0.30 | 0.70 |
| Pleural Effusion | 0.30 | 0.70 |
| Consolidation | 0.30 | 0.70 |
| Cardiomegaly | 0.40 | 0.80 |
| Edema | 0.30 | 0.70 |
| Nodule | 0.25 | 0.60 |
| Mass | 0.25 | 0.60 |

## Models

### Classification Model
- **Architecture**: DenseNet121
- **Training Data**: Combined dataset (NIH ChestX-ray14, CheXpert, MIMIC-CXR, PadChest)
- **Input Size**: 224x224 pixels
- **Output**: 18 pathology probabilities

### Detection Model
- **Architecture**: Faster R-CNN / Simple Heuristic Detector
- **Training Data**: VinDr-CXR (fallback: image processing)
- **Output**: Bounding boxes with confidence scores

## Deployment

### Production Checklist

1. **Security**
   - [ ] Generate strong `SECRET_KEY` and `ENCRYPTION_KEY`
   - [ ] Enable HTTPS with valid SSL certificates
   - [ ] Configure firewall rules
   - [ ] Enable authentication (not included in base version)

2. **Database**
   - [ ] Use managed PostgreSQL service
   - [ ] Configure regular backups
   - [ ] Enable SSL connections

3. **Scaling**
   - [ ] Use container orchestration (Kubernetes)
   - [ ] Configure horizontal pod autoscaling
   - [ ] Use GPU nodes for inference service

4. **Monitoring**
   - [ ] Set up logging aggregation
   - [ ] Configure alerting for errors
   - [ ] Monitor latency metrics

### GPU Support

To enable GPU inference:

1. Install NVIDIA Container Toolkit
2. Update `docker-compose.yml`:
   ```yaml
   inference:
     deploy:
       resources:
         reservations:
           devices:
             - driver: nvidia
               count: 1
               capabilities: [gpu]
   ```
3. Set `DEVICE=cuda` in environment

## Project Structure

```
cxr-triage-app/
├── backend/                 # FastAPI backend service
│   ├── app/
│   │   ├── main.py         # Application entry point
│   │   ├── config.py       # Configuration management
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── services/       # Business logic services
│   ├── Dockerfile
│   └── requirements.txt
├── inference/              # AI inference service
│   ├── app/
│   │   ├── main.py        # Inference API
│   │   ├── classifier.py  # Classification model
│   │   └── detector.py    # Detection model
│   ├── Dockerfile
│   └── requirements.txt
├── worker/                 # Celery async worker
│   ├── app/
│   │   ├── celery_app.py  # Celery configuration
│   │   └── tasks.py       # Async tasks
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js app router pages
│   │   ├── components/   # React components
│   │   └── lib/          # Utilities and API client
│   ├── Dockerfile
│   └── package.json
├── nginx/                 # Nginx reverse proxy
├── orthanc/              # Orthanc PACS configuration
├── scripts/              # Utility scripts
├── models/               # AI model weights
├── docker-compose.yml    # Docker orchestration
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [TorchXRayVision](https://github.com/mlmed/torchxrayvision) - Pretrained CXR models
- [Cornerstone.js](https://cornerstonejs.org/) - Medical imaging viewer
- [Orthanc](https://www.orthanc-server.com/) - Open-source PACS server
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Next.js](https://nextjs.org/) - React framework

## Citation

If you use this software in your research, please cite:

```bibtex
@software{cxr_triage_2024,
  title = {CXR Triage System},
  year = {2024},
  url = {https://github.com/yourusername/cxr-triage-app}
}
```
