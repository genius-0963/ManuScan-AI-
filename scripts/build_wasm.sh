#!/bin/bash

# Build WebAssembly modules from Open3D
# Requires Emscripten SDK

set -e

echo "🔧 Building WebAssembly modules for ManuScan AI..."

# Check if Emscripten is installed
if ! command -v emcc &> /dev/null; then
    echo "❌ Emscripten not found. Please install Emscripten SDK first."
    echo "Visit: https://emscripten.org/docs/getting_started/downloads.html"
    exit 1
fi

echo "✓ Emscripten SDK found"

# Directories
BUILD_DIR="frontend/wasm/build"
OUTPUT_DIR="frontend/public/wasm"

mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Compile geometry processing functions
echo "📦 Compiling geometry processor..."

cat > "$BUILD_DIR/geometry_processor.cpp" << 'EOF'
#include <emscripten/bind.h>
#include <emscripten/val.h>
#include <vector>
#include <cmath>

using namespace emscripten;

// Compute vertex normals
std::vector<float> computeNormals(
    const std::vector<float>& vertices,
    const std::vector<int>& indices
) {
    int numVertices = vertices.size() / 3;
    std::vector<float> normals(vertices.size(), 0.0f);
    
    // Compute face normals and accumulate to vertices
    for (size_t i = 0; i < indices.size(); i += 3) {
        int i0 = indices[i] * 3;
        int i1 = indices[i + 1] * 3;
        int i2 = indices[i + 2] * 3;
        
        float v0[3] = {vertices[i0], vertices[i0+1], vertices[i0+2]};
        float v1[3] = {vertices[i1], vertices[i1+1], vertices[i1+2]};
        float v2[3] = {vertices[i2], vertices[i2+1], vertices[i2+2]};
        
        // Edge vectors
        float e1[3] = {v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]};
        float e2[3] = {v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]};
        
        // Cross product
        float normal[3] = {
            e1[1]*e2[2] - e1[2]*e2[1],
            e1[2]*e2[0] - e1[0]*e2[2],
            e1[0]*e2[1] - e1[1]*e2[0]
        };
        
        // Accumulate to vertices
        normals[i0] += normal[0]; normals[i0+1] += normal[1]; normals[i0+2] += normal[2];
        normals[i1] += normal[0]; normals[i1+1] += normal[1]; normals[i1+2] += normal[2];
        normals[i2] += normal[0]; normals[i2+1] += normal[1]; normals[i2+2] += normal[2];
    }
    
    // Normalize
    for (int i = 0; i < numVertices; i++) {
        float x = normals[i*3];
        float y = normals[i*3+1];
        float z = normals[i*3+2];
        float len = std::sqrt(x*x + y*y + z*z);
        if (len > 0.0001f) {
            normals[i*3] /= len;
            normals[i*3+1] /= len;
            normals[i*3+2] /= len;
        }
    }
    
    return normals;
}

// Compute bounding box
std::vector<float> computeBoundingBox(const std::vector<float>& vertices) {
    if (vertices.empty()) return {0,0,0,0,0,0};
    
    float minX = vertices[0], minY = vertices[1], minZ = vertices[2];
    float maxX = vertices[0], maxY = vertices[1], maxZ = vertices[2];
    
    for (size_t i = 0; i < vertices.size(); i += 3) {
        minX = std::min(minX, vertices[i]);
        minY = std::min(minY, vertices[i+1]);
        minZ = std::min(minZ, vertices[i+2]);
        maxX = std::max(maxX, vertices[i]);
        maxY = std::max(maxY, vertices[i+1]);
        maxZ = std::max(maxZ, vertices[i+2]);
    }
    
    return {minX, minY, minZ, maxX, maxY, maxZ};
}

EMSCRIPTEN_BINDINGS(geometry_processor) {
    register_vector<float>("VectorFloat");
    register_vector<int>("VectorInt");
    
    function("computeNormals", &computeNormals);
    function("computeBoundingBox", &computeBoundingBox);
}
EOF

emcc "$BUILD_DIR/geometry_processor.cpp" \
    -o "$OUTPUT_DIR/geometry_processor.js" \
    -O3 \
    -s WASM=1 \
    -s MODULARIZE=1 \
    -s EXPORT_ES6=1 \
    -s EXPORT_NAME="GeometryProcessor" \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s EXPORTED_RUNTIME_METHODS='["cwrap","ccall"]' \
    --bind

echo "✅ WebAssembly modules compiled successfully!"
echo "📦 Output: $OUTPUT_DIR/"
ls -lh "$OUTPUT_DIR"

echo ""
echo "🎉 Build complete! WASM modules are ready for use."
