# Deploy detectron2 Demo on Ascend NPU

Deploy and test Facebook AI Research's detectron2 on Huawei Ascend NPU (ModelArts), with COCO val2017 and OGNet oil/gas refinery inference demos.

## Parameters

- `$SSH_KEY`: Path to SSH private key (default: find KeyPair-1708.pem in working directory)
- `$SSH_HOST`: Remote host (default: ma-user@dev-modelarts-apsoutheast1.huaweicloud.com)
- `$SSH_PORT`: SSH port (default: 32098)
- `$WORK_DIR`: Persistent work directory on remote (default: /home/ma-user/work)
- `$MAX_IMAGES`: Number of images per model (default: 20)
- `$SCORE_THRESH`: Detection score threshold (default: 0.5)

## Instructions

You are deploying a detectron2 inference demo on a Huawei Ascend NPU server for Petrobras AI department. Follow ALL phases in order. Each phase must complete before starting the next.

### Phase 1: SSH Connection Setup

1. Locate the SSH key file. Try `$SSH_KEY` first, then search the working directory for `KeyPair-1708.pem`.
2. Copy the key to `/tmp/` and `chmod 600` it (Windows filesystem doesn't support Unix permissions).
3. Test the SSH connection:
   ```
   ssh -i /tmp/KeyPair-1708.pem -p $SSH_PORT $SSH_HOST "echo OK; hostname; whoami"
   ```
4. Define a shell helper for subsequent SSH commands:
   ```
   SSH="ssh -i /tmp/KeyPair-1708.pem -p $SSH_PORT $SSH_HOST"
   ```

### Phase 2: Environment Check

Run these checks via SSH and record the results:

1. **OS & Arch**: `cat /etc/os-release | head -3; uname -m`
2. **Python**: `python3 --version`
3. **PyTorch + torch_npu**: `python3 -c "import torch; print('torch:', torch.__version__); import torch_npu; print('torch_npu:', torch_npu.__version__); print('NPU available:', torch.npu.is_available()); print('NPU count:', torch.npu.device_count())"`
4. **NPU Hardware**: `npu-smi info`
5. **CANN**: `cat /usr/local/Ascend/ascend-toolkit/latest/*/ascend_toolkit_install.info 2>/dev/null | grep version`
6. **GCC**: `gcc --version | head -1`
7. **Persistent disk**: `df -h $WORK_DIR`
8. **Existing detectron2**: `pip3 show detectron2 2>/dev/null || echo "not installed"`

If NPU is not available, STOP and report the error.

### Phase 3: Install detectron2 (if not present)

If detectron2 is not installed or not on persistent storage:

1. Install dependencies: `pip3 install fvcore iopath ninja`
2. Clone detectron2 to persistent storage:
   ```
   cd $WORK_DIR && git clone https://github.com/facebookresearch/detectron2.git
   ```
3. Build and install: `cd $WORK_DIR/detectron2 && pip3 install -e .`
4. Verify: `python3 -c "import detectron2; print(detectron2.__version__, detectron2.__file__)"`
   - Must show path under `$WORK_DIR/detectron2/`

If detectron2 already exists at `$WORK_DIR/detectron2/`, skip this phase.

### Phase 4: Create NPU Compatibility Patches

Create `$WORK_DIR/npu_patch.py` on the remote server with these contents:

```python
"""Runtime patches for detectron2 on Ascend NPU."""
import os
import torch
import torch_npu

def apply_patches():
    """Apply all NPU compatibility patches for detectron2 inference."""
    # 1. Set persistent model weights cache
    cache_dir = os.path.join(os.environ.get("WORK_DIR", "/home/ma-user/work"), ".torch", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    os.environ.setdefault("FVCORE_CACHE", cache_dir)

    # 2. Patch comm.synchronize() to avoid torch.cuda.current_device()
    try:
        from detectron2.utils import comm
        def _npu_synchronize():
            if not torch.distributed.is_available():
                return
            if not torch.distributed.is_initialized():
                return
            if torch.distributed.get_world_size() == 1:
                return
            torch.distributed.barrier()
        comm.synchronize = _npu_synchronize
    except Exception:
        pass

    # 3. Patch NMS: try detectron2 custom op, fallback to torchvision
    try:
        from detectron2.layers import nms as nms_module
        test_boxes = torch.tensor([[0,0,10,10]], dtype=torch.float32).npu()
        test_scores = torch.tensor([0.9], dtype=torch.float32).npu()
        nms_module.nms(test_boxes, test_scores, 0.5)
    except Exception:
        import torchvision.ops
        import detectron2.layers.nms as nms_mod
        nms_mod.nms = torchvision.ops.nms

    print("[npu_patch] Ascend NPU patches applied")
```

### Phase 5: Download Datasets

#### 5a: COCO val2017 (required)

1. Create directory: `mkdir -p $WORK_DIR/data/coco`
2. Download if not present:
   ```
   cd $WORK_DIR/data/coco
   wget http://images.cocodataset.org/zips/val2017.zip
   wget http://images.cocodataset.org/annotations/annotations_trainval2017.zip
   unzip val2017.zip && unzip annotations_trainval2017.zip
   rm val2017.zip annotations_trainval2017.zip
   ```
3. Verify: `ls $WORK_DIR/data/coco/val2017/ | wc -l` should be ~5000
4. Verify annotations: `ls $WORK_DIR/data/coco/annotations/instances_val2017.json`

#### 5b: OGNet Oil Refinery Dataset (required)

1. Create directory: `mkdir -p $WORK_DIR/data/ognet`
2. Download if not present:
   ```
   cd $WORK_DIR/data/ognet
   wget --timeout=120 http://download.cs.stanford.edu/deep/ognet/OGNetDevelopmentData.zip
   unzip OGNetDevelopmentData.zip && rm OGNetDevelopmentData.zip
   ```
3. If Stanford server is unavailable, report the failure but continue with COCO.
4. Verify: `ls $WORK_DIR/data/ognet/OGNetDevelopmentData/images/ | wc -l` should be ~7053

### Phase 6: Create Demo Scripts

#### 6a: COCO Demo Script (`$WORK_DIR/demo_coco.py`)

Create a script that:
- Imports torch, torch_npu, applies npu_patch
- Registers COCO val2017 dataset via `register_coco_instances`
- Creates DefaultPredictor with `MODEL.DEVICE = "npu"` and configurable score threshold
- Runs Faster R-CNN and Mask R-CNN on evenly sampled COCO val2017 images
- Saves annotated output images with bounding boxes and masks
- Prints per-image detection counts and per-class breakdown for the first image
- Prints summary statistics (total detections, avg dets/image, avg latency)

Key config settings:
- `cfg.MODEL.DEVICE = "npu"`
- `cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = $SCORE_THRESH`
- `cfg.INPUT.MIN_SIZE_TEST = 800`
- `cfg.INPUT.MAX_SIZE_TEST = 1333`
- `cfg.TEST.DETECTIONS_PER_IMAGE = 100`

#### 6b: OGNet Demo Script (`$WORK_DIR/demo_ognet.py`)

Create a script that:
- Imports torch, torch_npu, applies npu_patch
- Reads OGNet train.csv and val.csv to find positive (Target=1) refinery images
- Creates DefaultPredictor with `MODEL.DEVICE = "npu"` and score threshold 0.3 (lower for aerial imagery)
- Runs Faster R-CNN and Mask R-CNN on refinery images
- Saves annotated output images
- Prints per-image detection counts and summary statistics

### Phase 7: Run COCO Demo

1. Execute:
   ```
   cd $WORK_DIR && python3 demo_coco.py --max-images $MAX_IMAGES --score-thresh $SCORE_THRESH --models faster_rcnn mask_rcnn
   ```
2. Record all output: detection counts, latencies, per-class breakdowns.
3. Verify output images exist: `ls $WORK_DIR/output_coco/faster_rcnn/ | wc -l`

### Phase 8: Run OGNet Demo

1. Execute:
   ```
   cd $WORK_DIR && python3 demo_ognet.py --max-images $MAX_IMAGES --models faster_rcnn mask_rcnn
   ```
2. Record all output.
3. Verify output images exist: `ls $WORK_DIR/output_ognet/faster_rcnn/ | wc -l`

### Phase 9: Package Results

1. Pack COCO results on remote:
   ```
   cd $WORK_DIR/output_coco && tar czf /tmp/detectron2_coco_results.tar.gz faster_rcnn/ mask_rcnn/
   ```
2. Pack OGNet results on remote:
   ```
   cd $WORK_DIR/output_ognet && tar czf /tmp/detectron2_ognet_results.tar.gz faster_rcnn/ mask_rcnn/
   ```
3. Download both packages to local `/tmp/`:
   ```
   scp -i /tmp/KeyPair-1708.pem -P $SSH_PORT $SSH_HOST:/tmp/detectron2_coco_results.tar.gz /tmp/
   scp -i /tmp/KeyPair-1708.pem -P $SSH_PORT $SSH_HOST:/tmp/detectron2_ognet_results.tar.gz /tmp/
   ```

### Phase 10: Generate Test Report

Write a professional English test report to `/tmp/detectron2_npu_test_report.md` containing:

1. **Executive Summary** — key results for both COCO and OGNet
2. **Test Environment** — full hardware/software stack
3. **Datasets** — COCO val2017 and OGNet details
4. **Models & Configuration** — model configs, inference settings
5. **NPU Compatibility Patches** — what was patched and why
6. **COCO val2017 Results** — per-model tables with detections, latency, per-class breakdown
7. **OGNet Results** — per-model tables with detections, latency
8. **Performance Comparison** — COCO vs OGNet, Faster R-CNN vs Mask R-CNN
9. **Quality Improvement Recommendations** — TTA, larger backbone, ensemble, SAHI, fine-tuning, quantization
10. **Storage Layout** — persistent directory tree
11. **Known Issues** — CPU fallbacks, domain gap, first-image latency
12. **Reproduction Steps** — exact commands to reproduce
13. **Appendix** — software stack, output packages, COCO categories

The report must reference both output packages:
- `/tmp/detectron2_coco_results.tar.gz` — COCO val2017 annotated images
- `/tmp/detectron2_ognet_results.tar.gz` — OGNet refinery annotated images

### Final Output

After all phases complete, report to the user:
1. Both result package paths on local machine
2. Test report path
3. Key metrics summary (COCO: dets/image, latency; OGNet: dets/image, latency)
4. Any warnings or issues encountered
