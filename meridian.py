# ==============================================================================
# PROJECT: Meridian (Temporal Batch Loader)
# WRITTEN BY: Andrew F Burd
# LICENSE: MIT License
# DESCRIPTION: A high-performance sequence manager for ComfyUI.
# ==============================================================================

import os
import torch
import re
import folder_paths
import numpy as np
from PIL import Image, ImageOps

class Meridian:
    def __init__(self):
        self.node_states = {}

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "directory": ("STRING", {"default": "", "path": "True"}), 
                "batch_size": ("INT", {"default": 30, "min": 1, "max": 10000}),
                "overlap_frames": ("INT", {"default": 4, "min": 0, "max": 64}),
                "start_at_batch": ("INT", {"default": 0, "min": 0, "max": 10000}),
                "sort_mode": (["numerical", "alphabetical", "modified_date"], {"default": "numerical"}),
                "reset": ("BOOLEAN", {"default": False}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "IMAGE") 
    RETURN_NAMES = ("batch_images", "reference_frames")
    FUNCTION = "load_batch"
    CATEGORY = "Custom_Animation"

    def load_batch(self, directory, batch_size, overlap_frames, start_at_batch, sort_mode, reset, unique_id):
        directory = directory.strip().strip('"').strip("'")
        if not os.path.isabs(directory):
            directory = os.path.join(folder_paths.get_input_directory(), directory)
        path = os.path.abspath(os.path.expanduser(directory.replace("\\", "/")))
        
        stride = max(1, batch_size - overlap_frames)
        
        if unique_id not in self.node_states or reset:
            self.node_states[unique_id] = {"current_index": start_at_batch * stride, "image_paths": []}
        
        state = self.node_states[unique_id]

        if not state["image_paths"] or reset:
            if not os.path.exists(path):
                return (torch.zeros(1, 64, 64, 3), torch.zeros(1, 64, 64, 3))
            
            valid_exts = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')
            files = [os.path.join(path, f) for f in os.listdir(path) if f.lower().endswith(valid_exts)]
            
            if sort_mode == "numerical":
                def natural_keys(text):
                    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text)) if c]
                state["image_paths"] = sorted(files, key=natural_keys)
            else:
                state["image_paths"] = sorted(files)

        total_frames = len(state["image_paths"])
        start_idx = state["current_index"]
        
        if start_idx >= total_frames:
            return (torch.zeros(1, 64, 64, 3), torch.zeros(1, 64, 64, 3))

        end_idx = min(start_idx + batch_size, total_frames)
        batch_files = state["image_paths"][start_idx:end_idx]
        
        images = []
        master_size = None

        for i, f in enumerate(batch_files):
            img = Image.open(f).convert("RGB")
            img = ImageOps.exif_transpose(img) 
            
            if master_size is None:
                master_size = img.size
            
            if img.size != master_size:
                img = img.resize(master_size, Image.Resampling.LANCZOS)
                
            img_np = np.array(img).astype(np.float32) / 255.0
            images.append(torch.from_numpy(img_np)[None,])
            
        batch_tensor = torch.cat(images, dim=0)
        ref_count = min(overlap_frames, len(images))
        reference_tensor = batch_tensor[-ref_count:] if ref_count > 0 else torch.zeros(1, 64, 64, 3)

        state["current_index"] += stride

        state["current_index"] += stride
        
        if state["current_index"] >= self.total_frames:
            return {
                "ui": {"is_complete": [True]}, 
                "result": (batch_tensor, reference_tensor)
            }

        return (batch_tensor, reference_tensor)
    @classmethod
    def IS_CHANGED(s, **kwargs):
        import random
        return random.random()

NODE_CLASS_MAPPINGS = {"TemporalBatchLoader": Meridian}
NODE_DISPLAY_NAME_MAPPINGS = {"TemporalBatchLoader": "Meridian (Temporal Batch Loader)"}
