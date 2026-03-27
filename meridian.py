import os, re, math, torch, numpy as np, folder_paths
from PIL import Image, ImageOps
from server import PromptServer

# THE GLOBAL VAULT: Keeps your place in the folder across the queue
if "GLOBAL_MERIDIAN_VAULT" not in globals():
    GLOBAL_MERIDIAN_VAULT = {}

class Meridian:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "directory": ("STRING", {"default": "", "path": "True"}),
                "batch_size": ("INT", {"default": 30, "min": 1}),
                "overlap_frames": ("INT", {"default": 4, "min": 0}),
                "sort_mode": (["numerical", "alphabetical"],),
                "reset": ("BOOLEAN", {"default": False}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("IMAGE", "IMAGE")
    RETURN_NAMES = ("images", "references")
    FUNCTION = "load_batch"
    CATEGORY = "Custom_Animation"
    OUTPUT_NODE = True

    def load_batch(self, directory, batch_size, overlap_frames, sort_mode, reset, unique_id=None):
        path = os.path.abspath(os.path.expanduser(directory.strip().strip('"').strip("'").replace("\\", "/")))
        if not os.path.isabs(path): path = os.path.join(folder_paths.get_input_directory(), path)

        # 1. PERSISTENCE: Check if we are starting a new folder or resuming
        if unique_id not in GLOBAL_MERIDIAN_VAULT:
            GLOBAL_MERIDIAN_VAULT[unique_id] = {"idx": 0, "paths": [], "last_path": path, "memory": None}
        
        state = GLOBAL_MERIDIAN_VAULT[unique_id]

        # 2. AUTO-RESET: Only if you change folders or hit the reset button
        if state["last_path"] != path or reset:
            state.update({"idx": 0, "paths": [], "last_path": path, "memory": None})
            print(f"[Meridian] Initializing: {path}")

        # 3. FOLDER SCAN & NATURAL SORT
        if not state["paths"]:
            if not os.path.exists(path): return self._empty()
            files = [f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff'))]
            if sort_mode == "numerical":
                files.sort(key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s) if t])
            else: files.sort()
            state["paths"] = [os.path.join(path, f) for f in files]

        total = len(state["paths"])
        start = state["idx"]
        total_batches = math.ceil(total / batch_size)

        # 4. COMPLETION CHECK
        if start >= total:
            PromptServer.instance.send_sync("meridian.status", {"node_id": unique_id, "status": "Complete", "total_batches": total_batches})
            state["idx"] = 0
            return self._empty()

        # 5. THE CLEAN JUMP
        end = min(start + batch_size, total)
        batch_files = state["paths"][start:end]
        
        # 6. DASHBOARD HANDSHAKE
        PromptServer.instance.send_sync("meridian.status", {
            "node_id": unique_id, "status": "Running", "frame_start": start + 1, "frame_end": end, 
            "current_batch": (start // batch_size) + 1, "total_batches": total_batches
        })

        # 7. LOAD IMAGES
        imgs = [torch.from_numpy(np.array(ImageOps.exif_transpose(Image.open(f).convert("RGB"))).astype(np.float32) / 255.0)[None,] for f in batch_files]
        batch_tensor = torch.cat(imgs, dim=0)

        # 8. THE STYLE BRIDGE (Memory from previous batch)
        ref_out = state["memory"] if state["memory"] is not None else torch.zeros(1, 64, 64, 3)
        state["memory"] = batch_tensor[-min(overlap_frames, len(imgs)):] if overlap_frames > 0 else None

        # 9. ADVANCE THE COUNTER
        state["idx"] = start + batch_size
        return (batch_tensor, ref_out)

    def _empty(self):
        z = torch.zeros(1, 64, 64, 3)
        return (z, z.clone())

    @classmethod
    def IS_CHANGED(s, **kwargs):
        import random
        return random.random()

NODE_CLASS_MAPPINGS = {"TemporalBatchLoader": Meridian}
NODE_DISPLAY_NAME_MAPPINGS = {"TemporalBatchLoader": "Meridian (Temporal Batch Loader)"}
