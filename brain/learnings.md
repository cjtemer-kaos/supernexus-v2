## Lección: Modelos de difusión en RTX 3060 12GB (Windows)
- **Kolors (T2I)**: Funciona perfectamente. ~2.5 min/imagen a 1024x1024, FP16, peak VRAM 11.8 GB.
- **Video models (Wan2.1, CogVideoX)**: No viables en Windows RTX 3060. Todos los modelos de video testeados (Wan2.1-T2V-1.3B, CogVideoX-2B) son extremadamente lentos (~100-145s/step) por falta de Triton en Windows. La atención 3D cae a implementación PyTorch naive sin optimización CUDA.
- Soluciones: WSL2 (Triton funciona), o APIs externas. ComfyUI + onediff/nexfort podría acelerar en Windows.
- Frame saving fix: (frame * 255).astype(np.uint8) antes de Image.fromarray().
