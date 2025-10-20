"""
Training Pipeline for GNN Models
Multi-task learning for manufacturability prediction
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch_geometric.loader import DataLoader
from torch.utils.tensorboard import SummaryWriter
from pathlib import Path
import numpy as np
from tqdm import tqdm
from loguru import logger
import json
from typing import Dict, List, Optional
import time

from backend.models.gnn_architecture import create_model, MultiTaskLoss, count_parameters
from backend.geometry.graph_converter import MeshToGraphConverter


class Trainer:
    """
    Training pipeline for manufacturability prediction models.
    """
    
    def __init__(
        self,
        model_type: str = 'gcn',
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5,
        batch_size: int = 8,
        num_epochs: int = 100,
        checkpoint_dir: str = './checkpoints',
        log_dir: str = './logs'
    ):
        """
        Initialize trainer.
        
        Args:
            model_type: Type of model ('gcn', 'sage', 'gat')
            device: Device to train on
            learning_rate: Learning rate
            weight_decay: L2 regularization
            batch_size: Batch size
            num_epochs: Number of training epochs
            checkpoint_dir: Directory to save checkpoints
            log_dir: Directory for TensorBoard logs
        """
        self.device = torch.device(device)
        self.batch_size = batch_size
        self.num_epochs = num_epochs
        
        # Create directories
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize model
        logger.info(f"Creating {model_type.upper()} model...")
        self.model = create_model(
            model_type=model_type,
            in_channels=6,
            hidden_channels=128,
            num_layers=4,
            dropout=0.2
        ).to(self.device)
        
        logger.info(f"Model parameters: {count_parameters(self.model):,}")
        
        # Loss function
        self.criterion = MultiTaskLoss(num_tasks=3).to(self.device)
        
        # Optimizer
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=10,
            verbose=True
        )
        
        # TensorBoard writer
        self.writer = SummaryWriter(log_dir=str(self.log_dir))
        
        # Training stats
        self.train_losses = []
        self.val_losses = []
        self.best_val_loss = float('inf')
        self.epoch = 0
        
        logger.success("Trainer initialized")
    
    def train_epoch(self, train_loader: DataLoader) -> Dict[str, float]:
        """
        Train for one epoch.
        
        Args:
            train_loader: Training data loader
            
        Returns:
            Dictionary of training metrics
        """
        self.model.train()
        total_loss = 0
        loss_components = {'thickness': 0, 'undercut': 0, 'sharp_edge': 0}
        
        pbar = tqdm(train_loader, desc=f"Epoch {self.epoch + 1}/{self.num_epochs}")
        
        for batch_idx, data in enumerate(pbar):
            data = data.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            output = self.model(data.x, data.edge_index, data.batch)
            
            # Compute loss
            loss, loss_dict = self.criterion(
                thickness_pred=output['thickness'],
                thickness_target=data.y_thickness,
                undercut_pred=output['undercut'],
                undercut_target=data.y_undercut,
                sharp_edge_pred=output['sharp_edge'],
                sharp_edge_target=data.y_sharp_edge
            )
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            # Accumulate losses
            total_loss += loss.item()
            for key in loss_components:
                loss_components[key] += loss_dict[key]
            
            # Update progress bar
            pbar.set_postfix({'loss': loss.item()})
        
        # Average losses
        num_batches = len(train_loader)
        avg_loss = total_loss / num_batches
        for key in loss_components:
            loss_components[key] /= num_batches
        
        return {
            'total': avg_loss,
            **loss_components
        }
    
    def validate(self, val_loader: DataLoader) -> Dict[str, float]:
        """
        Validate model on validation set.
        
        Args:
            val_loader: Validation data loader
            
        Returns:
            Dictionary of validation metrics
        """
        self.model.eval()
        total_loss = 0
        loss_components = {'thickness': 0, 'undercut': 0, 'sharp_edge': 0}
        
        with torch.no_grad():
            for data in val_loader:
                data = data.to(self.device)
                
                # Forward pass
                output = self.model(data.x, data.edge_index, data.batch)
                
                # Compute loss
                loss, loss_dict = self.criterion(
                    thickness_pred=output['thickness'],
                    thickness_target=data.y_thickness,
                    undercut_pred=output['undercut'],
                    undercut_target=data.y_undercut,
                    sharp_edge_pred=output['sharp_edge'],
                    sharp_edge_target=data.y_sharp_edge
                )
                
                total_loss += loss.item()
                for key in loss_components:
                    loss_components[key] += loss_dict[key]
        
        # Average losses
        num_batches = len(val_loader)
        avg_loss = total_loss / num_batches
        for key in loss_components:
            loss_components[key] /= num_batches
        
        return {
            'total': avg_loss,
            **loss_components
        }
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None
    ):
        """
        Full training loop.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader (optional)
        """
        logger.info(f"Starting training for {self.num_epochs} epochs...")
        start_time = time.time()
        
        for epoch in range(self.num_epochs):
            self.epoch = epoch
            
            # Train
            train_metrics = self.train_epoch(train_loader)
            self.train_losses.append(train_metrics['total'])
            
            # Log training metrics
            self.writer.add_scalar('Loss/train', train_metrics['total'], epoch)
            self.writer.add_scalar('Loss/train_thickness', train_metrics['thickness'], epoch)
            self.writer.add_scalar('Loss/train_undercut', train_metrics['undercut'], epoch)
            self.writer.add_scalar('Loss/train_sharp_edge', train_metrics['sharp_edge'], epoch)
            
            logger.info(
                f"Epoch {epoch + 1}/{self.num_epochs} - "
                f"Train Loss: {train_metrics['total']:.4f}"
            )
            
            # Validate
            if val_loader is not None:
                val_metrics = self.validate(val_loader)
                self.val_losses.append(val_metrics['total'])
                
                # Log validation metrics
                self.writer.add_scalar('Loss/val', val_metrics['total'], epoch)
                self.writer.add_scalar('Loss/val_thickness', val_metrics['thickness'], epoch)
                self.writer.add_scalar('Loss/val_undercut', val_metrics['undercut'], epoch)
                self.writer.add_scalar('Loss/val_sharp_edge', val_metrics['sharp_edge'], epoch)
                
                logger.info(f"Val Loss: {val_metrics['total']:.4f}")
                
                # Update learning rate
                self.scheduler.step(val_metrics['total'])
                
                # Save best model
                if val_metrics['total'] < self.best_val_loss:
                    self.best_val_loss = val_metrics['total']
                    self.save_checkpoint('best_model.pth', is_best=True)
                    logger.success(f"New best model saved! (loss: {self.best_val_loss:.4f})")
            
            # Save regular checkpoint
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(f'checkpoint_epoch_{epoch + 1}.pth')
        
        elapsed = time.time() - start_time
        logger.success(f"Training completed in {elapsed / 60:.2f} minutes")
        
        # Close writer
        self.writer.close()
    
    def save_checkpoint(self, filename: str, is_best: bool = False):
        """
        Save model checkpoint.
        
        Args:
            filename: Checkpoint filename
            is_best: Whether this is the best model
        """
        checkpoint = {
            'epoch': self.epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'best_val_loss': self.best_val_loss,
        }
        
        path = self.checkpoint_dir / filename
        torch.save(checkpoint, path)
        
        if is_best:
            logger.info(f"Best checkpoint saved: {path}")
        else:
            logger.info(f"Checkpoint saved: {path}")
    
    def load_checkpoint(self, filename: str):
        """
        Load model checkpoint.
        
        Args:
            filename: Checkpoint filename
        """
        path = self.checkpoint_dir / filename
        
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}")
        
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.epoch = checkpoint['epoch']
        self.train_losses = checkpoint['train_losses']
        self.val_losses = checkpoint['val_losses']
        self.best_val_loss = checkpoint['best_val_loss']
        
        logger.success(f"Checkpoint loaded: {path}")


def create_synthetic_dataset(num_samples: int = 100) -> List:
    """
    Create synthetic dataset for testing.
    In production, replace with real data.
    """
    from backend.geometry.mesh_processor import MeshProcessor
    import open3d as o3d
    
    processor = MeshProcessor()
    converter = MeshToGraphConverter()
    
    graphs = []
    
    logger.info(f"Generating {num_samples} synthetic samples...")
    
    for i in tqdm(range(num_samples)):
        # Create random mesh (sphere with random resolution)
        resolution = np.random.randint(10, 30)
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=resolution)
        mesh.compute_vertex_normals()
        
        # Create synthetic labels
        num_vertices = len(mesh.vertices)
        thickness = np.random.uniform(1.0, 10.0, num_vertices)
        undercuts = np.random.randint(0, 2, num_vertices).astype(np.float32)
        sharp_edges = np.random.randint(0, 2, num_vertices).astype(np.float32)
        
        # Convert to graph
        graph = converter.convert(mesh, thickness, undercuts)
        graph.y_sharp_edge = torch.from_numpy(sharp_edges).float().unsqueeze(-1)
        
        graphs.append(graph)
    
    return graphs


def main():
    """
    Main training script
    """
    # Configuration
    config = {
        'model_type': 'gcn',
        'batch_size': 8,
        'num_epochs': 50,
        'learning_rate': 0.001,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu'
    }
    
    logger.info("ManuScan AI - Training Pipeline")
    logger.info(f"Configuration: {json.dumps(config, indent=2)}")
    
    # Create synthetic dataset (replace with real data)
    logger.info("Creating dataset...")
    dataset = create_synthetic_dataset(num_samples=100)
    
    # Split dataset
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config['batch_size'], shuffle=False)
    
    logger.info(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    # Initialize trainer
    trainer = Trainer(
        model_type=config['model_type'],
        device=config['device'],
        learning_rate=config['learning_rate'],
        batch_size=config['batch_size'],
        num_epochs=config['num_epochs']
    )
    
    # Train
    trainer.train(train_loader, val_loader)
    
    logger.success("Training complete!")


if __name__ == "__main__":
    main()
