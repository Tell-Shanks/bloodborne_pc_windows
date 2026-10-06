# DLSS 4 / DLAA

Windows launcher: choose **DLSS 4 / DLAA (NVIDIA RTX)** under image quality. Under detail settings choose **DLAA, Quality, Balanced, Performance, Custom**. Custom uses an even-pixel input size at 33–100% of output width and height. The selected NVIDIA DLL validates its actual supported size range; unsupported sizes produce a visible error. Restart after mode, ratio, output-size or DLL changes.

For native 4K use output 3840×2160 and DLAA. DLSS Quality uses 2560×1440 input. Performance uses 1924×1084 input at 4K: the existing game/UI recognition cannot safely distinguish scene and UI at exactly 1920×1080, while 1916×1078 is below DLSS Performance's allowed minimum. This small upward adjustment is intentional and appears in the launcher's actual input description.

## Replace the DLL

Close the game. Place your compatible `nvngx_dlss.dll` in a separate folder and select that folder in the launcher, or replace `dlss/nvngx_dlss.dll`. Leave the folder field empty to use the bundled location. No download or DLL replacement is performed silently. A restart is required. The bridge verifies the loaded module path and prints the loaded DLL file version. Incompatible DLLs produce NGX diagnostics in the log and overlay; success is reported only after evaluation succeeds.

Default: NVIDIA DLSS SDK tag v310.2.1, commit af199869c51cf2d71cc64d3db5064788ff38eb02. This integration provides Super Resolution and DLAA, not frame generation, Ray Reconstruction or DLSS 5. DLL file versions such as 310.2.1 are not the marketing generation number.

## Build

1. Run `python tools/fetch_dlss_sdk.py` using a Windows Python with working HTTPS. Downloads are pinned and SHA-256 verified; NVIDIA's SDK license is saved beside them.
2. Run `powershell -File tools/build_dlss_bridge.ps1` with MSVC Build Tools installed. The bridge uses the official MSVC static NGX library and exports a C ABI; the renderer remains MinGW.
3. Run `build_windows.ps1 -BuildDir out/windows-dlss -Test` using the normal MSYS2 UCRT64 dependencies. Deploy its `bin/bb-probe.exe` beside `dist/windows/bb-dlss-bridge.dll` and the existing runtime dependencies.

The bridge source is local integration code; NVIDIA headers and binaries remain subject to NVIDIA's license. SDK files and user-selected DLLs are not committed as game source. No borrowed NVIDIA application ID is used.

## Verification and limits

Verified on RTX 4070 Ti SUPER: native 4K DLAA in actual gameplay, plus standalone GPU execution for Quality, Balanced, Performance and Custom 75%. The startup DLL is 310.2.1.0. Native DLAA test scene was approximately 45–49 FPS; this is not a 4K120 guarantee. Other rendering passes remain significant GPU costs.

Original FSR settings are retained. DLSS failures show diagnostics; do not interpret output resolution alone as proof that the selected reconstruction method ran. Look for `DLSS: active input ...` and `DLSS loaded version:` in the log.
