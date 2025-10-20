# ManuScan AI - System Architecture

## Overview

ManuScan AI is a full-stack AI system for analyzing 3D CAD models. It combines traditional geometry processing with modern deep learning to provide real-time manufacturability insights.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  File Upload │→ │  Geometry    │→ │  TensorFlow  │      │
│  │  (STL/STEP)  │  │  Processor   │  │  .js Model   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         ↓                  ↓                  ↓              │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Three.js Viewer + Visualization          │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            ↑
                            │ WebAssembly + TensorFlow.js
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Open3D     │→ │    PyTorch   │→ │  Model       │      │
│  │   Geometry   │  │   Geometric  │  │  Export      │      │
│  │   Processing │  │   GNN        │  │  (ONNX/TFJS) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (Browser)

#### Technology Stack
- **TypeScript**: Type-safe development
- **Three.js**: 3D rendering and visualization
- **TensorFlow.js**: In-browser AI inference
- **WebAssembly**: High-performance geometry processing
- **Vite**: Build tool and dev server

#### Core Modules

**Engine (`src/core/engine.ts`)**
- Main orchestration layer
- Coordinates all subsystems
- Manages state and data flow

**Loader (`src/core/loader.ts`)**
- Parses STL files
- Handles STEP files (via WASM)
- Validates geometry

**Geometry Processor (`src/geometry/processor.ts`)**
- Mesh preprocessing
- Feature extraction
- Graph conversion for GNN input

**Inference Engine (`src/core/inference.ts`)**
- Loads TensorFlow.js model
- Runs predictions
- Post-processes results

**Viewer (`src/visualization/viewer.ts`)**
- 3D visualization with Three.js
- Heatmap rendering
- Interactive controls
- Annotation system

### 2. Backend (Python)

#### Technology Stack
- **Python 3.9+**: Core language
- **PyTorch**: Deep learning framework
- **PyTorch Geometric**: Graph neural networks
- **Open3D**: Geometry processing
- **CUDA**: GPU acceleration

#### Core Modules

**Mesh Processor (`backend/geometry/mesh_processor.py`)**
- Load STL/STEP files
- Clean and repair meshes
- Compute normals and curvature
- GPU-accelerated operations

**Feature Detector (`backend/geometry/feature_detection.py`)**
- Wall thickness analysis (ray casting)
- Undercut detection (normal analysis)
- Sharp edge detection
- Draft angle computation

**Graph Converter (`backend/geometry/graph_converter.py`)**
- Convert mesh to graph representation
- Extract node features (position, normal, curvature)
- Build edge connectivity from triangles

**GNN Models (`backend/models/gnn_architecture.py`)**
- MeshGCN: Graph Convolutional Network
- GraphSAGE: Scalable neighbor sampling
- AttentionGNN: Attention-based aggregation
- Multi-task output heads

**Training Pipeline (`backend/models/training.py`)**
- Data loading and batching
- Multi-task loss function
- Training loop with validation
- Checkpoint management

**Model Converter (`backend/export/model_converter.py`)**
- PyTorch → ONNX → TensorFlow → TensorFlow.js
- Model quantization
- WebAssembly wrapper generation

## Data Flow

### Training Pipeline

```
1. Load STL/STEP files
   ↓
2. Preprocess meshes (Open3D)
   ↓
3. Extract geometric features
   ↓
4. Convert to graph representation
   ↓
5. Train GNN model (PyTorch Geometric)
   ↓
6. Save checkpoint
   ↓
7. Convert to TensorFlow.js
```

### Inference Pipeline (Browser)

```
1. User uploads STL file
   ↓
2. Parse with Three.js STLLoader
   ↓
3. Preprocess geometry (WASM)
   ↓
4. Extract node features
   ↓
5. Build edge index
   ↓
6. Run TensorFlow.js model
   ↓
7. Post-process predictions
   ↓
8. Visualize results with heatmaps
```

## Key Algorithms

### Wall Thickness Detection

```python
def analyze_thickness(mesh):
    for each vertex v:
        cast ray from v along -normal
        find intersection with mesh
        distance = thickness at v
    return thickness_map
```

**Implementation**: Ray casting using Open3D's `RaycastingScene`

### Undercut Detection

```python
def detect_undercuts(mesh, draft_direction):
    for each vertex v:
        angle = angle_between(v.normal, draft_direction)
        if angle > 90°:
            v is undercut
    return undercut_regions
```

**Implementation**: Vector dot product and clustering

### GNN Architecture

```
Input: Graph G = (V, E)
  V: vertices with features [x, y, z, nx, ny, nz]
  E: edges from mesh triangles

Layers:
  1. Input projection: 6 → 128 dimensions
  2. GCN layers (4x):
     - Message passing
     - Batch normalization
     - ReLU activation
     - Residual connections
  3. Multi-task heads:
     - Thickness regression
     - Undercut classification
     - Sharp edge classification

Output: Per-vertex predictions
```

## Performance Optimizations

### Backend

1. **GPU Acceleration**
   - CUDA kernels for ray casting
   - Batch processing
   - Tensor operations on GPU

2. **Algorithm Optimization**
   - Spatial indexing (KD-tree, Octree)
   - Efficient neighbor search
   - Vectorized operations with NumPy

3. **Model Optimization**
   - Layer pruning
   - Weight quantization
   - Graph sparsification

### Frontend

1. **WebAssembly**
   - Compiled C++ geometry code
   - Near-native performance
   - Multi-threaded operations

2. **TensorFlow.js Optimization**
   - WebGL backend for GPU
   - Model quantization (uint8)
   - Weight sharding (4MB chunks)
   - Model caching

3. **Rendering Optimization**
   - Level of detail (LOD)
   - Frustum culling
   - Vertex buffer optimization
   - 60 FPS target

## Deployment Architecture

### Development

```
┌─────────────┐         ┌─────────────┐
│   Frontend  │         │   Backend   │
│   (Vite)    │         │  (Python)   │
│   :3000     │         │  Training   │
└─────────────┘         └─────────────┘
```

### Production

```
┌─────────────────────────────────┐
│     Static Hosting (CDN)        │
│  - HTML/CSS/JS bundles          │
│  - TensorFlow.js model          │
│  - WASM modules                 │
│  - 100% client-side execution   │
└─────────────────────────────────┘
```

### Docker Deployment

```yaml
services:
  backend:     # Training environment
  frontend:    # Development server
  notebook:    # Jupyter for experiments
```

## Scalability Considerations

### Handling Large Meshes

1. **Progressive Loading**
   - Stream large files in chunks
   - Display low-res preview first
   - Refine progressively

2. **Mesh Decimation**
   - Reduce vertex count for display
   - Preserve important features
   - Target: 100k-500k vertices

3. **Graph Sampling**
   - Sample subgraphs for GNN
   - Neighbor sampling (GraphSAGE)
   - Batch processing

### Browser Memory Management

- Dispose tensors after use
- Stream processing for large files
- Web Workers for background tasks
- Limit concurrent models

## Security Considerations

1. **File Validation**
   - Check file size limits
   - Validate file format
   - Sanitize filenames

2. **Client-Side Processing**
   - No data sent to servers
   - All processing in browser
   - User privacy preserved

3. **Model Integrity**
   - Verify model checksums
   - Use HTTPS for model loading
   - Version control for models

## Future Enhancements

1. **Real-time Collaboration**
   - WebRTC for multi-user sessions
   - Shared annotations
   - Real-time updates

2. **Cloud Training**
   - User uploads labeled data
   - Train custom models
   - Federated learning

3. **Mobile Support**
   - Progressive Web App (PWA)
   - Touch controls
   - Optimized for mobile GPUs

4. **Advanced Features**
   - Support more file formats (IGES, Parasolid)
   - Assembly analysis
   - Cost estimation
   - Tool path generation

## Technology Choices Rationale

| Choice | Rationale |
|--------|-----------|
| **PyTorch Geometric** | Best library for graph neural networks on meshes |
| **Open3D** | Fast, GPU-accelerated geometry operations |
| **TensorFlow.js** | Only mature browser ML framework |
| **Three.js** | Industry standard for WebGL 3D graphics |
| **TypeScript** | Type safety critical for complex geometry code |
| **Vite** | Fastest build tool for modern web apps |
| **WebAssembly** | Near-native performance for compute-intensive tasks |

## References

- Open3D: http://www.open3d.org/
- PyTorch Geometric: https://pytorch-geometric.readthedocs.io/
- TensorFlow.js: https://www.tensorflow.org/js
- Three.js: https://threejs.org/
