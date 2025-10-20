"""
Model Converter: PyTorch → TensorFlow.js
Converts trained PyTorch models for browser deployment
"""

import torch
import onnx
import tensorflowjs as tfjs
from pathlib import Path
import json
import numpy as np
from loguru import logger
import click

from backend.models.gnn_architecture import create_model


class ModelConverter:
    """
    Converts PyTorch models to TensorFlow.js format for browser deployment.
    Pipeline: PyTorch → ONNX → TensorFlow → TensorFlow.js
    """
    
    def __init__(
        self,
        model_path: str,
        output_dir: str = './frontend/public/models',
        model_type: str = 'gcn'
    ):
        """
        Initialize converter.
        
        Args:
            model_path: Path to PyTorch checkpoint
            output_dir: Output directory for TensorFlow.js model
            model_type: Type of model architecture
        """
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_type = model_type
        
        # Load model
        self.model = self.load_pytorch_model()
    
    def load_pytorch_model(self) -> torch.nn.Module:
        """Load PyTorch model from checkpoint"""
        logger.info(f"Loading PyTorch model from {self.model_path}...")
        
        # Create model architecture
        model = create_model(
            model_type=self.model_type,
            in_channels=6,
            hidden_channels=128,
            num_layers=4,
            dropout=0.2
        )
        
        # Load weights
        checkpoint = torch.load(self.model_path, map_location='cpu')
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
        
        model.eval()
        
        logger.success("PyTorch model loaded")
        return model
    
    def export_to_onnx(self, onnx_path: str = 'model.onnx') -> Path:
        """
        Export PyTorch model to ONNX format.
        
        Args:
            onnx_path: Output ONNX file path
            
        Returns:
            Path to ONNX file
        """
        onnx_file = self.output_dir / onnx_path
        
        logger.info(f"Exporting to ONNX: {onnx_file}...")
        
        # Create dummy input
        num_nodes = 100
        num_edges = 300
        
        dummy_x = torch.randn(num_nodes, 6)
        dummy_edge_index = torch.randint(0, num_nodes, (2, num_edges))
        dummy_batch = torch.zeros(num_nodes, dtype=torch.long)
        
        # Export to ONNX
        torch.onnx.export(
            self.model,
            (dummy_x, dummy_edge_index, dummy_batch),
            str(onnx_file),
            export_params=True,
            opset_version=13,
            do_constant_folding=True,
            input_names=['node_features', 'edge_index', 'batch'],
            output_names=['thickness', 'undercut', 'sharp_edge', 'overall_score'],
            dynamic_axes={
                'node_features': {0: 'num_nodes'},
                'edge_index': {1: 'num_edges'},
                'batch': {0: 'num_nodes'}
            }
        )
        
        # Verify ONNX model
        onnx_model = onnx.load(str(onnx_file))
        onnx.checker.check_model(onnx_model)
        
        logger.success(f"ONNX export complete: {onnx_file}")
        return onnx_file
    
    def export_to_tfjs(
        self,
        quantization: bool = True,
        weight_shard_size: int = 4 * 1024 * 1024  # 4MB
    ) -> Path:
        """
        Export model to TensorFlow.js format.
        
        Args:
            quantization: Apply quantization for smaller model size
            weight_shard_size: Maximum shard size in bytes
            
        Returns:
            Path to TensorFlow.js model directory
        """
        tfjs_dir = self.output_dir / 'tfjs'
        tfjs_dir.mkdir(exist_ok=True)
        
        logger.info(f"Exporting to TensorFlow.js: {tfjs_dir}...")
        
        # First, export to ONNX
        onnx_file = self.export_to_onnx()
        
        # Convert ONNX to TensorFlow
        # Note: This requires onnx-tf package
        try:
            import onnx_tf
            from onnx_tf.backend import prepare
            
            onnx_model = onnx.load(str(onnx_file))
            tf_rep = prepare(onnx_model)
            
            # Export as SavedModel
            saved_model_dir = self.output_dir / 'saved_model'
            tf_rep.export_graph(str(saved_model_dir))
            
            logger.info("Converted to TensorFlow SavedModel")
            
            # Convert SavedModel to TensorFlow.js
            if quantization:
                logger.info("Applying quantization (uint8)...")
                tfjs.converters.convert_tf_saved_model(
                    str(saved_model_dir),
                    str(tfjs_dir),
                    quantization_dtype_map={'uint8': '*'},
                    weight_shard_size_bytes=weight_shard_size
                )
            else:
                tfjs.converters.convert_tf_saved_model(
                    str(saved_model_dir),
                    str(tfjs_dir),
                    weight_shard_size_bytes=weight_shard_size
                )
            
            logger.success(f"TensorFlow.js export complete: {tfjs_dir}")
            
            # Get model size
            model_size = sum(f.stat().st_size for f in tfjs_dir.glob('**/*') if f.is_file())
            logger.info(f"Model size: {model_size / (1024 * 1024):.2f} MB")
            
            return tfjs_dir
            
        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            logger.error("Install required packages: pip install onnx-tf tensorflow tensorflowjs")
            raise
    
    def export_metadata(self, metadata: dict):
        """
        Export model metadata as JSON.
        
        Args:
            metadata: Dictionary of metadata
        """
        metadata_file = self.output_dir / 'metadata.json'
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved: {metadata_file}")
    
    def create_web_worker_wrapper(self):
        """
        Create Web Worker wrapper for async inference.
        """
        worker_code = """
// ManuScan AI - Inference Worker
importScripts('https://cdn.jsdelivr.net/npm/@tensorflow/tfjs');

let model = null;

// Load model
async function loadModel(modelPath) {
  model = await tf.loadGraphModel(modelPath);
  console.log('Model loaded in worker');
  return true;
}

// Run inference
async function predict(nodeFeatures, edgeIndex) {
  if (!model) {
    throw new Error('Model not loaded');
  }
  
  const nodeTensor = tf.tensor2d(nodeFeatures);
  const edgeTensor = tf.tensor2d(edgeIndex, undefined, 'int32');
  
  const outputs = await model.executeAsync({
    node_features: nodeTensor,
    edge_index: edgeTensor
  });
  
  const results = await Promise.all(outputs.map(t => t.data()));
  
  // Cleanup
  nodeTensor.dispose();
  edgeTensor.dispose();
  outputs.forEach(t => t.dispose());
  
  return results;
}

// Message handler
self.onmessage = async function(e) {
  const { type, data } = e.data;
  
  try {
    if (type === 'load') {
      await loadModel(data.modelPath);
      self.postMessage({ type: 'loaded' });
    } else if (type === 'predict') {
      const results = await predict(data.nodeFeatures, data.edgeIndex);
      self.postMessage({ type: 'prediction', results });
    }
  } catch (error) {
    self.postMessage({ type: 'error', error: error.message });
  }
};
"""
        
        worker_file = self.output_dir / 'inference.worker.js'
        with open(worker_file, 'w') as f:
            f.write(worker_code)
        
        logger.info(f"Web Worker created: {worker_file}")


@click.command()
@click.option('--input', '-i', required=True, help='Input PyTorch checkpoint path')
@click.option('--output', '-o', default='./frontend/public/models', help='Output directory')
@click.option('--model-type', '-m', default='gcn', help='Model architecture type')
@click.option('--quantize', is_flag=True, help='Apply quantization')
def main(input: str, output: str, model_type: str, quantize: bool):
    """
    Convert PyTorch model to TensorFlow.js format.
    
    Example:
        python model_converter.py -i checkpoints/best_model.pth -o frontend/public/models --quantize
    """
    logger.info("ManuScan AI - Model Converter")
    logger.info(f"Input: {input}")
    logger.info(f"Output: {output}")
    logger.info(f"Model type: {model_type}")
    logger.info(f"Quantization: {quantize}")
    
    # Convert model
    converter = ModelConverter(
        model_path=input,
        output_dir=output,
        model_type=model_type
    )
    
    # Export to TensorFlow.js
    tfjs_dir = converter.export_to_tfjs(quantization=quantize)
    
    # Export metadata
    metadata = {
        'model_type': model_type,
        'input_features': 6,
        'hidden_channels': 128,
        'num_layers': 4,
        'quantized': quantize,
        'input_names': ['node_features', 'edge_index'],
        'output_names': ['thickness', 'undercut', 'sharp_edge', 'overall_score']
    }
    converter.export_metadata(metadata)
    
    # Create Web Worker
    converter.create_web_worker_wrapper()
    
    logger.success("✅ Conversion complete!")
    logger.info(f"Model ready for browser deployment: {tfjs_dir}")


if __name__ == "__main__":
    main()
