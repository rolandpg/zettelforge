# DGX Spark / ASUS Ascent GX10 - Hardware Specs
**Date captured:** 2026-04-04
**Source:** https://www.asus.com/us/networking-iot-servers/desktop-ai-supercomputer/ultra-small-ai-supercomputers/asus-ascent-gx10/techspec/

## Compute
- **GPU:** NVIDIA Blackwell GPU (GB10, integrated)
- **CPU:** ARM v9.2-A CPU (GB10)
- **Chipset:** Integrated (SoC design)

## Memory
- **System Memory:** 128 GB LPDDR5x unified system memory
- **Unified Memory Architecture:** CPU and GPU share the 128GB pool

## Storage
- **Primary:** 4TB M.2 NVMe PCIe 5.0 SSD
- **Secondary:** 1TB M.2 NVMe PCIe 4.0 SSD
- **Tertiary:** 2TB M.2 NVMe PCIe 4.0 SSD
- **Total:** 7TB NVMe SSD storage

## Networking
- **Wi-Fi:** Wi-Fi 7 (802.11be, Gig+)
- **Bluetooth:** 5.4
- **Ethernet:** 10G Gigabit Ethernet
- **SmartNIC:** NVIDIA ConnectX-7

## I/O
- **USB-C:** 3x USB 3.2 Gen 2x2 Type-C (20Gbps, DisplayPort 2.1 alt mode)
- **USB-C PD:** 1x USB 3.2 Gen 2x2 Type-C with PD in (180W EPR PD3.1)
- **Video:** 1x HDMI 2.1
- **Security:** Kensington Lock

## Physical
- **Dimensions:** 150 x 150 x 51 mm (5.91 x 5.91 x 2.01 inch)
- **Weight:** 1.48kg
- **Power:** 240W adapter with EPR PD3.1
- **OS:** Ubuntu Linux

## Key Implications for AI/LLM Work
- **Unified Memory:** 128GB shared between CPU/GPU means no PCIe bandwidth bottlenecks
- **Blackwell Architecture:** 5th-gen Tensor Cores, FP4/FP6/FP8 support for inference
- **Storage Speed:** PCIe 5.0 primary SSD means fast model loading
- **Network:** 10G + ConnectX-7 enables fast data pulls and cluster connectivity

## Fine-Tuning Capability Estimate
- **Full fine-tuning:** Up to 13B parameter models (128GB accommodates model + optimizer states + gradients)
- **QLoRA fine-tuning:** Up to 70B parameter models with aggressive quantization
- **Inference:** 70B+ models feasible depending on quantization level
