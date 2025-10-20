/**
 * Three.js 3D Viewer
 * Renders models with analysis overlays
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import type { ViewerConfig, MeshData, HeatmapConfig, VisualizationMode } from '../types';

export class ModelViewer {
  private container: HTMLElement;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private mesh: THREE.Mesh | null = null;
  private originalColors: Float32Array | null = null;
  private animationFrameId: number = 0;

  constructor(config: ViewerConfig) {
    this.container = config.container;

    const width = config.width || this.container.clientWidth;
    const height = config.height || this.container.clientHeight;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(config.backgroundColor || 0xf0f0f0);

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    this.camera.position.set(0, 0, 50);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.container.appendChild(this.renderer.domElement);

    // Controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;

    // Lighting
    this.setupLighting();

    // Grid
    if (config.enableGrid) {
      const grid = new THREE.GridHelper(100, 100);
      this.scene.add(grid);
    }

    // Handle resize
    window.addEventListener('resize', this.handleResize.bind(this));

    // Start animation loop
    this.animate();

    console.log('✓ 3D Viewer initialized');
  }

  /**
   * Setup scene lighting
   */
  private setupLighting(): void {
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    // Directional lights
    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight1.position.set(1, 1, 1);
    this.scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.4);
    dirLight2.position.set(-1, -1, -1);
    this.scene.add(dirLight2);

    // Hemisphere light for better ambient
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.3);
    this.scene.add(hemiLight);
  }

  /**
   * Load and display mesh
   */
  loadMesh(meshData: MeshData): void {
    // Remove existing mesh
    if (this.mesh) {
      this.scene.remove(this.mesh);
      this.mesh.geometry.dispose();
      if (Array.isArray(this.mesh.material)) {
        this.mesh.material.forEach((m) => m.dispose());
      } else {
        this.mesh.material.dispose();
      }
    }

    // Create mesh
    const geometry = meshData.geometry;
    const material = new THREE.MeshStandardMaterial({
      color: 0x808080,
      metalness: 0.3,
      roughness: 0.7,
      flatShading: false,
      side: THREE.DoubleSide,
      vertexColors: true,
    });

    this.mesh = new THREE.Mesh(geometry, material);

    // Store original colors (gray)
    const vertexCount = geometry.attributes.position.count;
    this.originalColors = new Float32Array(vertexCount * 3);
    for (let i = 0; i < vertexCount; i++) {
      this.originalColors[i * 3] = 0.5; // R
      this.originalColors[i * 3 + 1] = 0.5; // G
      this.originalColors[i * 3 + 2] = 0.5; // B
    }

    // Set initial colors
    geometry.setAttribute('color', new THREE.BufferAttribute(this.originalColors, 3));

    this.scene.add(this.mesh);

    // Center and scale mesh
    this.fitCameraToMesh();

    console.log('✓ Mesh loaded into viewer');
  }

  /**
   * Apply heatmap coloring
   */
  applyHeatmap(values: Float32Array, config: HeatmapConfig): void {
    if (!this.mesh) return;

    const geometry = this.mesh.geometry;
    const vertexCount = geometry.attributes.position.count;

    if (values.length !== vertexCount) {
      console.error(`Value count (${values.length}) doesn't match vertex count (${vertexCount})`);
      return;
    }

    const colors = new Float32Array(vertexCount * 3);

    for (let i = 0; i < vertexCount; i++) {
      const normalized = (values[i] - config.min) / (config.max - config.min);
      const color = this.valueToColor(normalized, config.colormap);

      colors[i * 3] = color[0];
      colors[i * 3 + 1] = color[1];
      colors[i * 3 + 2] = color[2];
    }

    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.attributes.color.needsUpdate = true;

    console.log(`✓ Heatmap applied (${config.colormap})`);
  }

  /**
   * Highlight specific regions
   */
  highlightRegions(indices: number[], color: THREE.Color = new THREE.Color(0xff0000)): void {
    if (!this.mesh) return;

    const geometry = this.mesh.geometry;
    const colors = geometry.attributes.color.array as Float32Array;

    for (const idx of indices) {
      if (idx >= 0 && idx < colors.length / 3) {
        colors[idx * 3] = color.r;
        colors[idx * 3 + 1] = color.g;
        colors[idx * 3 + 2] = color.b;
      }
    }

    geometry.attributes.color.needsUpdate = true;
  }

  /**
   * Reset to original colors
   */
  resetColors(): void {
    if (!this.mesh || !this.originalColors) return;

    const geometry = this.mesh.geometry;
    geometry.setAttribute('color', new THREE.BufferAttribute(this.originalColors.slice(), 3));
    geometry.attributes.color.needsUpdate = true;
  }

  /**
   * Convert normalized value to color
   */
  private valueToColor(value: number, colormap: string): [number, number, number] {
    value = Math.max(0, Math.min(1, value));

    if (colormap === 'redyellowgreen') {
      // Red -> Yellow -> Green
      if (value < 0.5) {
        return [1, value * 2, 0];
      } else {
        return [1 - (value - 0.5) * 2, 1, 0];
      }
    } else if (colormap === 'jet') {
      // Jet colormap approximation
      const r = Math.max(0, Math.min(1, 1.5 - Math.abs(value * 4 - 3)));
      const g = Math.max(0, Math.min(1, 1.5 - Math.abs(value * 4 - 2)));
      const b = Math.max(0, Math.min(1, 1.5 - Math.abs(value * 4 - 1)));
      return [r, g, b];
    } else {
      // Default: grayscale
      return [value, value, value];
    }
  }

  /**
   * Fit camera to view entire mesh
   */
  private fitCameraToMesh(): void {
    if (!this.mesh) return;

    const box = new THREE.Box3().setFromObject(this.mesh);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = this.camera.fov * (Math.PI / 180);
    const cameraDistance = maxDim / (2 * Math.tan(fov / 2));

    this.camera.position.copy(center);
    this.camera.position.z += cameraDistance * 1.5;
    this.camera.lookAt(center);

    this.controls.target.copy(center);
    this.controls.update();

    console.log(`✓ Camera fitted to mesh (size: ${maxDim.toFixed(2)})`);
  }

  /**
   * Take screenshot
   */
  screenshot(width?: number, height?: number): string {
    if (width && height) {
      const originalSize = this.renderer.getSize(new THREE.Vector2());
      this.renderer.setSize(width, height);
      this.renderer.render(this.scene, this.camera);
      const dataURL = this.renderer.domElement.toDataURL('image/png');
      this.renderer.setSize(originalSize.x, originalSize.y);
      return dataURL;
    } else {
      this.renderer.render(this.scene, this.camera);
      return this.renderer.domElement.toDataURL('image/png');
    }
  }

  /**
   * Handle window resize
   */
  private handleResize(): void {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height);
  }

  /**
   * Animation loop
   */
  private animate(): void {
    this.animationFrameId = requestAnimationFrame(this.animate.bind(this));

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * Cleanup resources
   */
  dispose(): void {
    cancelAnimationFrame(this.animationFrameId);

    if (this.mesh) {
      this.mesh.geometry.dispose();
      if (Array.isArray(this.mesh.material)) {
        this.mesh.material.forEach((m) => m.dispose());
      } else {
        this.mesh.material.dispose();
      }
    }

    this.renderer.dispose();
    this.controls.dispose();

    window.removeEventListener('resize', this.handleResize.bind(this));

    console.log('✓ Viewer disposed');
  }
}

export default ModelViewer;
