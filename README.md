# ComfyUI-Meridian
Meridian - Temporal Batch Loader for timelapse

**A High-Performance, Seamless Sequence Manager for ComfyUI.**  
*Written by: Andrew F Burd*

---

## 🛠️ The Problem it Solves
Managing long animation sequences (like 1,000+ frames) in ComfyUI usually requires a messy
combination of **Meta Batch Managers**, **Number Counters**, and **Image Loaders**. Keeping
track of frame indices and ensuring temporal consistency between batches is a manual headache.

**Meridian** consolidates all of these into a single, intelligent node.

## 🚀 Key Features
*   **Consolidated Workflow**: Replaces three or more nodes with one central "Sequence Brain."
*   **Natural Numerical Sorting**: Say goodbye to renaming files with six leading zeros. Meridian understands that `frame_9.png` comes before `frame_10.png`.
*   **Temporal Bridge Logic**: Automatically handles overlapping frames (Striding) so Batch B always knows exactly how Batch A ended.
*   **Resumable Renders**: Use the `start_at_batch` slider to pick up exactly where you left off after a crash or pause.

## 📈 Node Map (Connections)
*   **batch_images**: Connect to **VAE Encode** or **KSampler**.
*   **reference_frames**: Connect to **IPAdapter** or **ControlNet-Tile** for temporal coherence.

This is still in BETA, working out the bugs as I type this...
