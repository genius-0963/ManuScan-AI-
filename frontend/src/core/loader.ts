/**
 * STL/STEP File Loader
 * Handles loading and parsing of 3D CAD files
 */

import * as THREE from 'three';
import { STLLoader as ThreeSTLLoader } from 'three/examples/jsm/loaders/STLLoader';

export class STLLoader {
  private loader: ThreeSTLLoader;

  constructor() {
    this.loader = new ThreeSTLLoader();
  }

  /**
   * Load STL file from File object
   */
  async loadFromFile(file: File): Promise<THREE.BufferGeometry> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (event) => {
        const arrayBuffer = event.target?.result as ArrayBuffer;
        try {
          const geometry = this.loader.parse(arrayBuffer);
          console.log(`✓ Loaded ${file.name}`);
          resolve(geometry);
        } catch (error) {
          reject(new Error(`Failed to parse STL file: ${error}`));
        }
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsArrayBuffer(file);
    });
  }

  /**
   * Load STL file from URL
   */
  async loadFromUrl(url: string): Promise<THREE.BufferGeometry> {
    return new Promise((resolve, reject) => {
      this.loader.load(
        url,
        (geometry) => {
          console.log(`✓ Loaded ${url}`);
          resolve(geometry);
        },
        (progress) => {
          console.log(`Loading: ${((progress.loaded / progress.total) * 100).toFixed(0)}%`);
        },
        (error) => {
          reject(new Error(`Failed to load STL file: ${error}`));
        }
      );
    });
  }

  /**
   * Validate geometry
   */
  validateGeometry(geometry: THREE.BufferGeometry): boolean {
    if (!geometry.attributes.position) {
      console.error('Geometry has no position attribute');
      return false;
    }

    const vertexCount = geometry.attributes.position.count;
    if (vertexCount === 0) {
      console.error('Geometry has no vertices');
      return false;
    }

    return true;
  }
}

export class STEPLoader {
  /**
   * Load STEP file (requires WebAssembly OCCT bindings)
   * Placeholder for future implementation
   */
  async loadFromFile(file: File): Promise<THREE.BufferGeometry> {
    // TODO: Implement STEP loading via WebAssembly Open CASCADE
    throw new Error('STEP file loading not yet implemented');
  }
}
