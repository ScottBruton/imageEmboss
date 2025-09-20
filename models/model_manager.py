"""
Model Manager
Handles loading, managing, and processing with different segmentation models
"""

import torch
import torch.nn as nn
import segmentation_models_pytorch as smp
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import cv2
import numpy as np
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2


class ModelType(Enum):
    """Available model types"""
    UNET = "unet"
    FPN = "fpn"
    PSPNET = "pspnet"
    LINKNET = "linknet"
    PAN = "pan"
    MANET = "manet"
    DEEPLABV3 = "deeplabv3"
    DEEPLABV3PLUS = "deeplabv3plus"


class EncoderType(Enum):
    """Available encoder backbones"""
    RESNET18 = "resnet18"
    RESNET34 = "resnet34"
    RESNET50 = "resnet50"
    RESNET101 = "resnet101"
    RESNET152 = "resnet152"
    EFFICIENTNET_B0 = "efficientnet-b0"
    EFFICIENTNET_B1 = "efficientnet-b1"
    EFFICIENTNET_B2 = "efficientnet-b2"
    EFFICIENTNET_B3 = "efficientnet-b3"
    EFFICIENTNET_B4 = "efficientnet-b4"
    EFFICIENTNET_B5 = "efficientnet-b5"
    MOBILENET_V2 = "mobilenet_v2"
    DENSENET121 = "densenet121"
    DENSENET161 = "densenet161"
    DENSENET169 = "densenet169"
    DENSENET201 = "densenet201"


class ModelConfig:
    """Configuration for a model"""
    
    def __init__(self, 
                 model_type: ModelType,
                 encoder_name: EncoderType,
                 encoder_weights: str = "imagenet",
                 in_channels: int = 3,
                 classes: int = 1,
                 activation: Optional[str] = None,
                 model_name: str = ""):
        self.model_type = model_type
        self.encoder_name = encoder_name
        self.encoder_weights = encoder_weights
        self.in_channels = in_channels
        self.classes = classes
        self.activation = activation
        self.model_name = model_name or f"{model_type.value}_{encoder_name.value}"


class ModelManager:
    """Manages segmentation models and their processing"""
    
    def __init__(self, device: str = "auto"):
        self.device = self._get_device(device)
        self.current_model: Optional[nn.Module] = None
        self.current_config: Optional[ModelConfig] = None
        self.preprocessing_fn = None
        
        # Available model configurations
        self.available_models = self._get_available_models()
    
    def _get_device(self, device: str) -> str:
        """Determine the best device to use"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon
            else:
                return "cpu"
        return device
    
    def _get_available_models(self) -> Dict[str, ModelConfig]:
        """Get list of available model configurations"""
        models = {}
        
        # Popular combinations with descriptions
        popular_combinations = [
            (ModelType.UNET, EncoderType.RESNET34, "U-Net ResNet34"),
            (ModelType.UNET, EncoderType.EFFICIENTNET_B0, "U-Net EfficientNet-B0"),
            (ModelType.FPN, EncoderType.RESNET50, "FPN ResNet50"),
            (ModelType.PSPNET, EncoderType.RESNET101, "PSPNet ResNet101"),
            (ModelType.DEEPLABV3PLUS, EncoderType.RESNET50, "DeepLabV3+ ResNet50"),
            (ModelType.LINKNET, EncoderType.RESNET18, "LinkNet ResNet18"),
            (ModelType.PAN, EncoderType.EFFICIENTNET_B2, "PAN EfficientNet-B2"),
        ]
        
        for model_type, encoder, name in popular_combinations:
            config = ModelConfig(
                model_type=model_type,
                encoder_name=encoder,
                model_name=name
            )
            models[name] = config
        
        return models
    
    def get_model_description(self, model_name: str) -> Dict[str, str]:
        """Get detailed description and use case information for a model"""
        descriptions = {
            "U-Net ResNet34": {
                "description": "U-Net is a classic encoder-decoder architecture with skip connections. ResNet34 provides a good balance between performance and speed.",
                "use_cases": "• Medical image segmentation\n• General object segmentation\n• Binary and multi-class segmentation\n• When you need good accuracy with moderate speed",
                "image_examples": "• X-ray images (bone, lung segmentation)\n• MRI scans (tumor, organ detection)\n• Satellite imagery (building, road detection)\n• Microscopy images (cell segmentation)\n• CT scans (organ, lesion detection)",
                "pros": "• Excellent for small objects\n• Good boundary preservation\n• Well-established architecture\n• Moderate computational requirements",
                "cons": "• May struggle with very large objects\n• Limited context understanding\n• Can be memory intensive for high-res images",
                "best_for": "Medical imaging, satellite imagery, general segmentation tasks"
            },
            "U-Net EfficientNet-B0": {
                "description": "U-Net with EfficientNet-B0 backbone. EfficientNet uses compound scaling for optimal efficiency.",
                "use_cases": "• Mobile and edge deployment\n• Real-time applications\n• Resource-constrained environments\n• When speed is critical",
                "image_examples": "• Live camera feeds (real-time segmentation)\n• Mobile app images (quick processing)\n• Surveillance footage (object detection)\n• Drone imagery (fast aerial analysis)\n• Webcam streams (interactive applications)",
                "pros": "• Very fast inference\n• Low memory usage\n• Good for mobile devices\n• Efficient architecture",
                "cons": "• Lower accuracy than larger models\n• May miss fine details\n• Limited for complex scenes",
                "best_for": "Real-time applications, mobile apps, edge computing"
            },
            "FPN ResNet50": {
                "description": "Feature Pyramid Network with ResNet50. Uses multi-scale feature fusion for better object detection at different scales.",
                "use_cases": "• Multi-scale object detection\n• Instance segmentation\n• When objects vary greatly in size\n• Complex scenes with multiple objects",
                "image_examples": "• Street scenes (cars, pedestrians, buildings)\n• Aerial photography (vehicles, structures)\n• Crowded images (people, objects)\n• Industrial images (machinery, products)\n• Sports footage (players, equipment)",
                "pros": "• Excellent multi-scale performance\n• Good for varying object sizes\n• Strong feature representation\n• Good balance of speed/accuracy",
                "cons": "• More complex than U-Net\n• Higher memory usage\n• May be overkill for simple tasks",
                "best_for": "Instance segmentation, object detection, complex scenes"
            },
            "PSPNet ResNet101": {
                "description": "Pyramid Scene Parsing Network with ResNet101. Uses spatial pyramid pooling to capture global context.",
                "use_cases": "• Scene parsing and understanding\n• Semantic segmentation\n• When global context is important\n• High-resolution images",
                "image_examples": "• Cityscapes (roads, buildings, sky)\n• Landscape photos (trees, water, mountains)\n• Interior scenes (furniture, walls, floors)\n• High-res satellite imagery (urban areas)\n• Panoramic images (wide scenes)",
                "pros": "• Excellent global context understanding\n• Good for scene parsing\n• Handles large objects well\n• Strong semantic understanding",
                "cons": "• High computational requirements\n• Slower inference\n• Memory intensive\n• May be overkill for simple tasks",
                "best_for": "Scene parsing, semantic segmentation, high-resolution images"
            },
            "DeepLabV3+ ResNet50": {
                "description": "DeepLabV3+ with ResNet50. Uses atrous convolutions and spatial pyramid pooling for precise segmentation.",
                "use_cases": "• Precise boundary segmentation\n• High-quality segmentation\n• When accuracy is critical\n• Professional applications",
                "image_examples": "• Portrait photos (hair, face boundaries)\n• Product images (precise object edges)\n• Medical scans (organ boundaries)\n• Architectural photos (building edges)\n• Quality control images (defect detection)",
                "pros": "• Excellent boundary precision\n• Good multi-scale features\n• Strong performance\n• Well-optimized architecture",
                "cons": "• Higher computational cost\n• More complex than basic U-Net\n• Requires more memory",
                "best_for": "Professional segmentation, high-accuracy requirements, boundary-sensitive tasks"
            },
            "LinkNet ResNet18": {
                "description": "LinkNet with ResNet18. Lightweight architecture with direct skip connections for fast inference.",
                "use_cases": "• Real-time applications\n• Mobile deployment\n• When speed is more important than accuracy\n• Simple segmentation tasks",
                "image_examples": "• Simple object photos (single items)\n• Basic shapes and patterns\n• Low-resolution images\n• Quick preview images\n• Simple background removal",
                "pros": "• Very fast inference\n• Low memory footprint\n• Simple architecture\n• Good for real-time use",
                "cons": "• Lower accuracy than larger models\n• Limited for complex scenes\n• May miss fine details",
                "best_for": "Real-time processing, mobile applications, simple segmentation"
            },
            "PAN EfficientNet-B2": {
                "description": "Path Aggregation Network with EfficientNet-B2. Combines bottom-up and top-down paths for rich feature representation.",
                "use_cases": "• Instance segmentation\n• When you need both speed and accuracy\n• Multi-object scenes\n• Balanced performance requirements",
                "image_examples": "• Group photos (multiple people)\n• Retail images (multiple products)\n• Nature scenes (multiple animals/plants)\n• Urban scenes (multiple vehicles)\n• Manufacturing (multiple parts)",
                "pros": "• Good balance of speed and accuracy\n• Excellent for instance segmentation\n• Efficient architecture\n• Good multi-object handling",
                "cons": "• More complex than basic models\n• Moderate computational requirements\n• May be overkill for simple tasks",
                "best_for": "Instance segmentation, balanced performance needs, multi-object scenes"
            }
        }
        
        return descriptions.get(model_name, {
            "description": "Custom model configuration",
            "use_cases": "• Custom segmentation tasks\n• Experimental applications\n• Specific domain requirements",
            "image_examples": "• Custom domain images\n• Experimental datasets\n• Specialized applications\n• Research images\n• Domain-specific content",
            "pros": "• Customizable parameters\n• Tailored for specific needs\n• Flexible configuration",
            "cons": "• Requires tuning\n• May need validation\n• Less tested than standard models",
            "best_for": "Custom applications, research, specific domain tasks"
        })
    
    def load_model(self, config: ModelConfig) -> bool:
        """Load a model with the given configuration"""
        try:
            # Create the model
            model = self._create_model(config)
            
            # Move to device
            model = model.to(self.device)
            
            # Set to evaluation mode
            model.eval()
            
            # Store the model and config
            self.current_model = model
            self.current_config = config
            
            # Get preprocessing function
            self.preprocessing_fn = smp.encoders.get_preprocessing_fn(
                config.encoder_name.value, 
                config.encoder_weights
            )
            
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def _create_model(self, config: ModelConfig) -> nn.Module:
        """Create a model based on configuration"""
        model_type = config.model_type.value
        encoder_name = config.encoder_name.value
        
        if model_type == "unet":
            return smp.Unet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "fpn":
            return smp.FPN(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "pspnet":
            return smp.PSPNet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "linknet":
            return smp.Linknet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "pan":
            return smp.PAN(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "manet":
            return smp.MAnet(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "deeplabv3":
            return smp.DeepLabV3(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        elif model_type == "deeplabv3plus":
            return smp.DeepLabV3Plus(
                encoder_name=encoder_name,
                encoder_weights=config.encoder_weights,
                in_channels=config.in_channels,
                classes=config.classes,
                activation=config.activation,
            )
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    def unload_model(self):
        """Unload the current model"""
        if self.current_model is not None:
            del self.current_model
            self.current_model = None
            self.current_config = None
            self.preprocessing_fn = None
            
            # Clear GPU cache if using CUDA
            if self.device == "cuda":
                torch.cuda.empty_cache()
    
    def preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess an image for the current model"""
        if self.preprocessing_fn is None:
            raise ValueError("No model loaded")
        
        # Apply preprocessing
        image = self.preprocessing_fn(image)
        
        # Convert to tensor and add batch dimension
        image_tensor = torch.from_numpy(image).float()
        image_tensor = image_tensor.unsqueeze(0)  # Add batch dimension
        
        return image_tensor.to(self.device)
    
    def predict(self, image: np.ndarray) -> np.ndarray:
        """Run inference on an image"""
        if self.current_model is None:
            raise ValueError("No model loaded")
        
        with torch.no_grad():
            # Preprocess the image
            input_tensor = self.preprocess_image(image)
            
            # Run inference
            prediction = self.current_model(input_tensor)
            
            # Convert to numpy
            if isinstance(prediction, (list, tuple)):
                prediction = prediction[0]
            
            prediction = prediction.squeeze().cpu().numpy()
            
            # Apply activation if specified
            if self.current_config.activation == "sigmoid":
                prediction = 1 / (1 + np.exp(-prediction))
            elif self.current_config.activation == "softmax":
                prediction = np.exp(prediction) / np.sum(np.exp(prediction), axis=0)
            
            return prediction
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        if self.current_model is None:
            return {"loaded": False}
        
        info = {
            "loaded": True,
            "model_name": self.current_config.model_name,
            "model_type": self.current_config.model_type.value,
            "encoder": self.current_config.encoder_name.value,
            "encoder_weights": self.current_config.encoder_weights,
            "in_channels": self.current_config.in_channels,
            "classes": self.current_config.classes,
            "device": self.device,
            "parameters": sum(p.numel() for p in self.current_model.parameters()),
        }
        
        if self.device == "cuda":
            info["gpu_memory"] = torch.cuda.memory_allocated() / 1024**3  # GB
        
        return info
    
    def get_available_models(self) -> Dict[str, ModelConfig]:
        """Get list of available model configurations"""
        return self.available_models.copy()
    
    @property
    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded"""
        return self.current_model is not None
    
    @property
    def current_model_name(self) -> str:
        """Get the name of the currently loaded model"""
        if self.current_config:
            return self.current_config.model_name
        return "No model loaded"
