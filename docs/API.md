# 📚 ManuScan AI - API Reference

Complete API documentation for ManuScan AI's Python and JavaScript interfaces.

## Table of Contents

- [Python API](#python-api)
- [JavaScript/TypeScript API](#javascripttypescript-api)
- [REST API](#rest-api)
- [Data Types](#data-types)
- [Error Handling](#error-handling)

---

## Python API

### MeshProcessor

Main class for 3D mesh processing and preprocessing.

```python
from backend.geometry import MeshProcessor

processor = MeshProcessor(
    use_gpu=True,           # Enable GPU acceleration
    target_vertices=100000, # Target vertex count after decimation
    max_vertices=500000     # Maximum input vertices
)
```

#### Methods

##### `load_mesh(file_path: str) -> o3d.geometry.TriangleMesh`

Load a 3D mesh from STL or STEP file.

**Parameters:**
- `file_path` (str): Path to the mesh file

**Returns:**
- `o3d.geometry.TriangleMesh`: Loaded mesh object

**Example:**
```python
mesh = processor.load_mesh("model.stl")
```

##### `preprocess(mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.TriangleMesh`

Clean and preprocess the mesh for analysis.

**Parameters:**
- `mesh`: Input mesh object

**Returns:**
- Preprocessed mesh with computed normals and cleaned geometry

**Example:**
```python
clean_mesh = processor.preprocess(mesh)
```

##### `compute_metrics(mesh: o3d.geometry.TriangleMesh) -> MeshMetrics`

Compute basic mesh quality metrics.

**Returns:**
- `MeshMetrics` object with vertex count, surface area, volume, etc.

### FeatureDetector

Analyzes geometric features for manufacturability assessment.

```python
from backend.geometry import FeatureDetector

detector = FeatureDetector(
    min_wall_thickness=2.0,    # Minimum acceptable thickness (mm)
    min_draft_angle=3.0,       # Minimum draft angle (degrees)
    sharp_edge_threshold=30.0  # Sharp edge angle threshold
)
```

#### Methods

##### `analyze_wall_thickness(mesh, num_rays=32) -> ThicknessResult`

Analyze wall thickness using ray casting.

**Parameters:**
- `mesh`: Input mesh
- `num_rays` (int): Number of rays per vertex for sampling

**Returns:**
- `ThicknessResult` with thickness map and thin regions

##### `detect_undercuts(mesh) -> List[UndercutRegion]`

Detect undercut regions that prevent mold release.

**Returns:**
- List of undercut regions with severity scores

##### `find_sharp_edges(mesh) -> List[SharpEdge]`

Find sharp edges that may need filleting.

**Returns:**
- List of sharp edges with angles and locations

##### `generate_report(mesh) -> ManufacturabilityReport`

Generate comprehensive manufacturability report.

**Returns:**
- Complete analysis report with overall score

**Example:**
```python
report = detector.generate_report(mesh)
print(f"Overall Score: {report.overall_score}/100")
print(f"Thin Walls: {len(report.thickness.thin_regions)}")
```

---

## JavaScript/TypeScript API

### ManuScanEngine

Main engine class for browser-based analysis.

```typescript
import { ManuScanEngine } from './src/core/engine';

const engine = new ManuScanEngine({
  useWebGL: true,                           // Enable WebGL acceleration
  useWasm: true,                           // Enable WebAssembly
  modelPath: '/models/manuscan_model.json', // Path to TensorFlow.js model
  maxVertices: 500000,                     // Maximum input vertices
  targetVertices: 100000                   // Target vertex count
});
```

#### Methods

##### `initialize(): Promise<void>`

Initialize the engine and load AI models.

**Example:**
```typescript
await engine.initialize();
console.log('Engine ready!');
```

##### `loadModel(file: File): Promise<void>`

Load a 3D model file (STL/STEP).

**Parameters:**
- `file`: File object from input element

**Example:**
```typescript
const fileInput = document.getElementById('file-input') as HTMLInputElement;
const file = fileInput.files[0];
await engine.loadModel(file);
```

##### `analyze(): Promise<AnalysisResult>`

Run manufacturability analysis on loaded model.

**Returns:**
- `AnalysisResult` with scores and detailed analysis

**Example:**
```typescript
const result = await engine.analyze();
console.log(`Score: ${result.overallScore}/100`);
```

##### `getMeshData(): MeshData | null`

Get the currently loaded mesh data.

**Returns:**
- Mesh data for visualization or null if no model loaded

##### `exportJSON(result: AnalysisResult): string`

Export analysis results as JSON.

**Parameters:**
- `result`: Analysis result to export

**Returns:**
- JSON string of the results

### ModelViewer

3D visualization component using Three.js.

```typescript
import { ModelViewer } from './src/visualization/viewer';

const viewer = new ModelViewer({
  container: document.getElementById('viewer'),
  backgroundColor: 0x2a2a2a,
  enableControls: true,
  enableGrid: false
});
```

#### Methods

##### `loadMesh(meshData: MeshData): void`

Load mesh data into the 3D viewer.

##### `applyHeatmap(values: Float32Array, config: HeatmapConfig): void`

Apply color-coded heatmap to the mesh.

**Parameters:**
- `values`: Per-vertex values for coloring
- `config`: Heatmap configuration (colormap, min/max values)

##### `resetColors(): void`

Reset mesh to default colors.

##### `highlightRegions(indices: number[]): void`

Highlight specific regions (vertices/faces).

---

## REST API

Optional backend server for analysis via HTTP requests.

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### `POST /analyze`

Analyze a 3D model file.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@model.stl" \
  -F "min_thickness=2.0" \
  -F "draft_angle=3.0"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "overall_score": 87.0,
    "thickness": {
      "min": 2.3,
      "max": 15.8,
      "mean": 6.2,
      "thin_regions": [12453, 23891, 34567]
    },
    "undercuts": {
      "count": 0,
      "regions": []
    },
    "sharp_edges": {
      "count": 8,
      "locations": [4521, 4522, 8932, 8933]
    },
    "processing_time": 1234.5,
    "timestamp": "2025-10-20T11:30:00Z"
  }
}
```

#### `GET /health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "gpu_available": true
}
```

#### `GET /models`

List available AI models.

**Response:**
```json
{
  "models": [
    {
      "name": "manuscan_v1.0",
      "version": "1.0.0",
      "accuracy": 95.2,
      "size_mb": 15.3
    }
  ]
}
```

---

## Data Types

### Python Types

#### `ThicknessResult`
```python
@dataclass
class ThicknessResult:
    min_thickness: float
    max_thickness: float
    mean_thickness: float
    thin_regions: List[int]      # Vertex indices
    thickness_map: np.ndarray    # Per-vertex thickness
```

#### `ManufacturabilityReport`
```python
@dataclass
class ManufacturabilityReport:
    thickness: ThicknessResult
    undercuts: List[UndercutRegion]
    sharp_edges: List[SharpEdge]
    draft_angles: np.ndarray
    overall_score: float         # 0-100
    issues_summary: Dict[str, int]
```

### TypeScript Types

#### `AnalysisResult`
```typescript
interface AnalysisResult {
  overallScore: number;
  thickness: {
    min: number;
    max: number;
    mean: number;
    thinRegions: number[];
    map: Float32Array;
  };
  undercuts: {
    detected: boolean;
    regions: number[];
    severity: number;
  };
  sharpEdges: {
    count: number;
    locations: number[];
  };
  processingTime: number;
  timestamp: Date;
}
```

#### `MeshData`
```typescript
interface MeshData {
  vertices: number[][];
  normals: number[];
  faces: number[][];
  geometry: THREE.BufferGeometry;
}
```

---

## Error Handling

### Python Exceptions

```python
from backend.exceptions import (
    MeshLoadError,
    ProcessingError,
    InferenceError
)

try:
    mesh = processor.load_mesh("invalid.stl")
except MeshLoadError as e:
    print(f"Failed to load mesh: {e}")
except ProcessingError as e:
    print(f"Processing failed: {e}")
```

### JavaScript Errors

```typescript
try {
  await engine.loadModel(file);
  const result = await engine.analyze();
} catch (error) {
  if (error instanceof ModelLoadError) {
    console.error('Failed to load model:', error.message);
  } else if (error instanceof AnalysisError) {
    console.error('Analysis failed:', error.message);
  }
}
```

### HTTP Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid file format or parameters |
| 413 | Payload Too Large - File exceeds size limit |
| 422 | Unprocessable Entity - Mesh processing failed |
| 500 | Internal Server Error - Analysis engine error |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/analyze` | 10 requests | 1 minute |
| `/health` | 100 requests | 1 minute |
| `/models` | 50 requests | 1 minute |

---

## Examples

### Complete Python Workflow

```python
import open3d as o3d
from backend.geometry import MeshProcessor, FeatureDetector
from backend.models import create_model

# Initialize components
processor = MeshProcessor(use_gpu=True)
detector = FeatureDetector(min_wall_thickness=2.0)

# Load and preprocess
mesh = processor.load_mesh("model.stl")
mesh = processor.preprocess(mesh)

# Analyze features
report = detector.generate_report(mesh)

# Print results
print(f"Overall Score: {report.overall_score}/100")
print(f"Min Thickness: {report.thickness.min_thickness:.2f}mm")
print(f"Thin Regions: {len(report.thickness.thin_regions)}")
print(f"Sharp Edges: {len(report.sharp_edges)}")

# Save visualization
o3d.io.write_triangle_mesh("analyzed_model.ply", mesh)
```

### Complete TypeScript Workflow

```typescript
import { ManuScanEngine } from './src/core/engine';
import { ModelViewer } from './src/visualization/viewer';

class ManuScanApp {
  private engine: ManuScanEngine;
  private viewer: ModelViewer;

  async initialize() {
    // Initialize engine
    this.engine = new ManuScanEngine({
      useWebGL: true,
      modelPath: '/models/manuscan_model.json'
    });
    await this.engine.initialize();

    // Initialize viewer
    this.viewer = new ModelViewer({
      container: document.getElementById('viewer'),
      enableControls: true
    });
  }

  async analyzeModel(file: File) {
    // Load model
    await this.engine.loadModel(file);
    
    // Display in viewer
    const meshData = this.engine.getMeshData();
    if (meshData) {
      this.viewer.loadMesh(meshData);
    }

    // Run analysis
    const result = await this.engine.analyze();
    
    // Apply heatmap
    this.viewer.applyHeatmap(result.thickness.map, {
      colormap: 'redyellowgreen',
      min: result.thickness.min,
      max: result.thickness.max
    });

    return result;
  }
}

// Usage
const app = new ManuScanApp();
await app.initialize();

const fileInput = document.getElementById('file-input') as HTMLInputElement;
fileInput.addEventListener('change', async (event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file) {
    const result = await app.analyzeModel(file);
    console.log(`Analysis complete: ${result.overallScore}/100`);
  }
});
```

---

For more examples and advanced usage, see the [examples directory](../examples/) in the repository.
