# Contributing to ManuScan AI

Thank you for your interest in contributing to ManuScan AI! This document provides guidelines and instructions for contributing.

## Getting Started

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/yourusername/manuscan-ai.git
   cd manuscan-ai
   ```
3. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd frontend && npm install
   ```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring

### 2. Make Your Changes

Follow the coding standards:

**Python Code**
- Follow PEP 8 style guide
- Use type hints
- Add docstrings for all functions
- Run `black` for formatting
- Run `flake8` for linting

**TypeScript Code**
- Follow ESLint rules
- Use TypeScript types
- Add JSDoc comments
- Run `prettier` for formatting

### 3. Test Your Changes

```bash
# Backend tests
pytest backend/tests/

# Frontend tests
cd frontend
npm test

# Run benchmarks
python scripts/benchmark.py
```

### 4. Commit Your Changes

Use conventional commits:
```bash
git commit -m "feat: add support for IGES files"
git commit -m "fix: resolve mesh decimation bug"
git commit -m "docs: update API documentation"
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python

```python
def analyze_mesh(
    mesh: o3d.geometry.TriangleMesh,
    threshold: float = 2.0
) -> ManufacturabilityReport:
    """
    Analyze mesh for manufacturability issues.
    
    Args:
        mesh: Input triangle mesh
        threshold: Minimum wall thickness in mm
        
    Returns:
        Complete manufacturability report
    """
    # Implementation
    pass
```

### TypeScript

```typescript
/**
 * Load and analyze 3D model
 * @param file - STL file to analyze
 * @returns Analysis results
 */
async function analyzeModel(file: File): Promise<AnalysisResult> {
  // Implementation
}
```

## Testing Guidelines

### Unit Tests

- Test individual functions
- Mock external dependencies
- Aim for >80% coverage

### Integration Tests

- Test complete workflows
- Use real data samples
- Verify performance targets

### Example Test

```python
def test_thickness_analysis():
    """Test wall thickness detection"""
    mesh = create_test_mesh()
    detector = FeatureDetector()
    result = detector.analyze_wall_thickness(mesh)
    
    assert result.min_thickness > 0
    assert len(result.thin_regions) >= 0
```

## Documentation

- Update README if adding features
- Add docstrings to new functions
- Update architecture docs if changing structure
- Include code examples

## Performance Requirements

Ensure your changes maintain performance targets:

- Mesh loading: <2s for 500k vertices
- Preprocessing: <50ms (GPU)
- Inference: <100ms
- Total pipeline: <200ms

## Areas for Contribution

### High Priority

- [ ] STEP file parsing (WebAssembly)
- [ ] Additional GNN architectures
- [ ] Real-world training dataset
- [ ] Mobile optimization
- [ ] PDF report generation

### Medium Priority

- [ ] Assembly analysis
- [ ] Cost estimation
- [ ] Tool path generation
- [ ] Multi-language support
- [ ] Annotation system improvements

### Documentation

- [ ] Tutorial videos
- [ ] More code examples
- [ ] API documentation
- [ ] Performance optimization guide

## Questions?

- Open an issue for discussion
- Join our Discord community
- Email: contact@manuscan.ai

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on improving the project
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to ManuScan AI! 🚀**
