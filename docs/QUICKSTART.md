# ManuScan AI - Quick Start Guide

Get up and running with ManuScan AI in minutes!

## Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **CUDA Toolkit** (optional, for GPU training)
- **8GB+ RAM** recommended
- Modern web browser (Chrome, Firefox, Edge)

## Quick Installation

### 1. Clone and Setup Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import open3d; import torch; print('✅ Backend ready!')"
```

### 2. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will open at `http://localhost:3000`

## First Analysis

### Option A: Use the Web Interface

1. **Upload a Model**
   - Click "Upload STL/STEP File"
   - Select a 3D model (.stl file)
   - Wait for loading

2. **Run Analysis**
   - Click "Analyze Manufacturability"
   - View results in ~100ms

3. **Explore Visualizations**
   - Switch between visualization modes
   - See thickness heatmaps
   - Identify problem areas

### Option B: Use Python API

```python
from backend.geometry.mesh_processor import MeshProcessor
from backend.geometry.feature_detection import FeatureDetector

# Load and process mesh
processor = MeshProcessor(use_gpu=True)
mesh = processor.load_mesh("model.stl")
mesh = processor.preprocess(mesh)

# Analyze manufacturability
detector = FeatureDetector()
report = detector.generate_report(mesh)

# View results
print(f"Manufacturability Score: {report.overall_score}/100")
print(f"Min Thickness: {report.thickness.min_thickness}mm")
print(f"Undercuts: {len(report.undercuts)}")
```

## Training Your Own Model

### 1. Prepare Dataset

```bash
# Place STL files in backend/data/raw/
mkdir -p backend/data/raw
# Copy your .stl files here
```

### 2. Train Model

```bash
# Using the training script
./scripts/train_model.sh

# Or directly with Python
python -m backend.models.training \
    --model-type gcn \
    --epochs 100 \
    --batch-size 8
```

### 3. Convert for Browser

```bash
# Convert PyTorch model to TensorFlow.js
python backend/export/model_converter.py \
    -i checkpoints/best_model.pth \
    -o frontend/public/models \
    --quantize
```

### 4. Use in Frontend

The converted model is automatically loaded by the frontend from `frontend/public/models/`

## Performance Testing

```bash
# Run benchmark suite
python scripts/benchmark.py
```

Expected performance:
- **Loading**: <2s for 500k vertices
- **Preprocessing**: <50ms (GPU)
- **Inference**: <100ms
- **Total Pipeline**: <200ms

## Troubleshooting

### GPU Not Detected

```python
# Check CUDA availability
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

If False, install CUDA toolkit or use CPU mode:
```python
processor = MeshProcessor(use_gpu=False)
```

### Frontend Not Loading

```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Model Loading Errors

Ensure model is converted and placed in correct directory:
```bash
ls -la frontend/public/models/
```

Should contain:
- `model.json`
- `group1-shard*of*.bin`
- `metadata.json`

## Next Steps

1. **Read Documentation**: Check `docs/` for detailed guides
2. **Explore Examples**: See `examples/` for sample analyses
3. **Customize Models**: Modify architecture in `backend/models/`
4. **Integrate**: Use the API in your own applications

## Docker Quick Start

Prefer Docker? Use the all-in-one setup:

```bash
# Start all services
docker-compose up

# Access:
# - Frontend: http://localhost:3000
# - Jupyter: http://localhost:8888
```

## Getting Help

- **Documentation**: `docs/`
- **Issues**: GitHub Issues
- **Examples**: `examples/`
- **API Reference**: `docs/api_reference.md`

---

**Ready to analyze! 🚀**

Upload a 3D model and see manufacturability insights in under 100ms.
