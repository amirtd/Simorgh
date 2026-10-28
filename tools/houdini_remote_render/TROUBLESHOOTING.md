# Troubleshooting

## Houdini not found / installer stops

Use the actual existing HFS directory, not its `bin` directory. Source `houdini_setup`, confirm `hython` and `husk`, and rerun with `--hfs /opt/hfs22.0.BUILD`. This project does not install Houdini. The inspected machine currently has no detected installation, so deployment and real rendering remain blocked.

## Licensing errors / Apprentice / Indie

Run `hython -c 'import hou; print(hou.applicationVersionString(), hou.licenseCategory())'` in the sourced environment. Review `sesictrl print-license` locally and use SideFX License Administrator to resolve entitlements. Do not post license inventories publicly. Success in `husk --help` does not prove licensing. Apprentice/non-commercial HIP workflows are refused. For Indie, retain the appropriate scene extension and use compatible native Houdini/Karma licensing; do not rename restricted files or convert license categories to bypass a restriction. Try the supplied small scene before a production shot.

## SSH refused / timeout / host key rejected

On Ubuntu, inspect `systemctl status ssh` and `ss -ltn '( sport = :22 )'`. On Windows, test `ssh -o BatchMode=yes user@private-host python3 --version`. Check Tailscale on both computers and confirm the intended private address. Install OpenSSH only if needed using the installer's explicit `--enable-ssh` option or your normal administration process. Check private-interface firewall rules; do not make a public router port forward.

Verify the host fingerprint before first connection. A changed key can indicate a rebuilt host or the wrong machine; verify it locally before updating `known_hosts`. The client deliberately refuses unknown keys. It does not fall back to passwords. For encrypted keys, unlock your SSH agent before using the shelf tool.

## Paramiko / PySide6 import errors

Install Paramiko using the exact Houdini 22 Python environment. Running `pip` from an unrelated Windows Python installation does not make it available to Houdini. PySide6 is expected from Houdini's Qt6 environment; it is not an extra application dependency. Test `import paramiko` in Houdini's Python shell.

## No worker / queue stays queued

Inspect `systemctl --user status houdini-render.service` and `journalctl --user -u houdini-render.service -n 100`. Use `systemctl --user daemon-reload` after installing without `--start`, then enable/start the service. Use `sudo loginctl enable-linger YOUR_USER` if it must run after reboot without login. The service sources Houdini's environment before starting the worker. A second worker fails its lock instead of competing for the same GPU.

Jobs running at a crash/restart become failed with an interruption message. Queued jobs remain queued. Resubmit interrupted work with a new ID after checking partial frames. Automatic frame-render resumption is not implemented; byte-resumable **download** is.

## Missing assets / unsupported paths

Use the explicit asset path in the error to locate missing textures, VDBs, geometry caches, USD layers, or MaterialX includes. A USD render sees the cooked Solaris stage, not every unused reference in the HIP. Bake SOP/OBJ content into Solaris first. Windows drives are remapped into hashed relative bundle directories; never try to mount `C:` as a Linux path.

Unresolved `$F`, `$HIP`, backticks, `opdef:`, URI resolvers, USDZ-internal paths, and other unsupported expressions are errors. Resolve expressions in the cooked stage, bake procedurals, and use file-based assets. Custom assets hidden in shader code or opaque binary formats require explicit scene preparation; the packager cannot infer them.

Very large frame ranges cook/export on the UI thread because Houdini APIs are not thread safe. Start with one small frame, then expand. Temporary export bundles can consume substantial local disk space.

## Wrong GPU / out of memory / XPU initialization failure

Inspect `nvidia-smi`, the selected GPU in `~/houdini-render/server.json`, and `~/houdini-render/logs/JOB.FRAME.log`. A stable UUID avoids GPU index reorder. The inspected machine has both a 5060 Ti and a 3060, and Isaac Sim was using approximately 2 GiB of the 5060 Ti during initial inspection. This tool does not stop unrelated GPU processes. Close them yourself if you want more VRAM.

XPU runs with `CUDA_VISIBLE_DEVICES` and `KARMA_XPU_DISABLE_EMBREE_DEVICE=1` to select the configured GPU and avoid silent CPU fallback. Check OptiX/NVIDIA device logs in the real verification run. Driver branch detection is only a baseline check, not a substitute for a successful render. Reduce texture/geometry/resolution memory or use the explicitly selected CPU renderer if appropriate. Driver changes require your own review; the installer never makes them.

## Black image / wrong glass / output not found

Open the USD in Solaris and confirm the camera, one render product, MaterialX surface binding, lights, and render settings. The selected LOP must contain the whole render stage. The tool overrides render resolution and output filename through husk. It disables render-time procedurals; bake their geometry. Custom shaders may need matching resources/plugins on both hosts and are outside automatic deployment support.

A nonzero exit or missing/empty expected frame marks the job failed. `status.json` contains the last log excerpt and each frame has its full log. A present image is not proof of visual correctness: inspect the fixture and production result in an image viewer.

## Cancel requested but status still running

The worker notices cancellation on its next poll (about a second, plus GPU query time), sends SIGTERM to its own active render group, waits up to ten seconds, then sends SIGKILL if required. It never kills every `husk` or NVIDIA process. A queued cancellation is handled when the worker reaches that queue entry. If a job already completed before cancellation arrives, its completed result is retained.

## Download interrupted / checksum mismatch / existing output

Reopen the panel or select the Job ID and click Download Results. Downloads append to `.part`, verify size and SHA-256, then rename. Matching destination frames are skipped. Different existing destination files are retained and reported as a conflict; select a new directory or explicitly back up/remove the conflicting files.

A corrupted `.part` file cannot be repaired by appending. Remove only that partial file and retry. If the checksum still differs, inspect the Linux output; it may have changed after the manifest was generated. The software never deletes Linux original frames automatically.

## Panel closed / lost status / multiple jobs

Server jobs continue while Houdini or the panel is closed. Local connection settings persist pending job IDs and per-job host/output destinations. Reopen the shelf tool to resume automatic polling/download. Network errors remain visible and may be retried on subsequent polls. If a failed download conflicts with an existing frame, use a clean output directory through the CLI; automatic downloads keep the original per-job destination.

## Updating a deployment

Stop the user service before replacing scripts. The installer asks before replacing an existing deployment; queue data and outputs are retained. Back up the old scripts/config first if you need rollback. On Windows deploy into a new directory and update the shelf path. Restart Houdini to clear previously imported Python modules. Connection settings are per user and separate from the deployed code.
