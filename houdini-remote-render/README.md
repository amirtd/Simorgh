# Houdini 22 Remote Render: Windows → Ubuntu

A deployable shelf tool, USD packager, SSH/SFTP client, and serial persistent render queue. No HQueue, web service, cloud service, or paid API. Windows cooks a selected Solaris LOP stage at each requested frame, packages flattened USD and dependencies, and sends the bundle over SSH. Ubuntu runs one `husk` process per frame. The panel polls JSON status and automatically downloads completed jobs while open.

**Readiness:** implemented and tested at the software/component level. Real Houdini rendering and Windows-to-Linux end-to-end operation are **not verified**. The inspected server has Ubuntu 24.04.5, RTX 5060 Ti (16311 MiB), RTX 3060, NVIDIA 580.178.04, and Tailscale installed. No Houdini installation was found in the searched locations; SSH was inactive with no port 22 listener. No Windows machine or Phoenix scene was available. No drivers, Houdini installations, SSH settings, or services were changed during development.

## Supported workflow and limits

- Houdini **22**, Python 3, Qt 6/PySide6. Choose one Solaris LOP stage containing exactly one USD Render Settings prim, one render product, and a camera relationship. Select Karma CPU or XPU, integer frames/step, resolution, EXR/PNG, and destination.
- This is a Solaris/USD workflow. OBJ-only, Mantra, Redshift, arbitrary ROP networks, and live DOP simulations require scene preparation in Solaris first. The server deliberately does not open `.hip` files. This avoids assuming a universal Houdini render command.
- Cooked geometry, USD layers/references, USD asset-valued textures, VDBs/caches, UDIM tiles, and MaterialX filename/include resources are packaged. Dependency checks run after export and checksums run before queueing and again before rendering. Relative bundle paths make Windows drives irrelevant on Linux.
- `$HIP`, `$JOB`, `$F`, backticks, resolver URIs, `op:`/`opdef:`, and other unresolved expressions must be resolved by cooking/export or are rejected. Image sequences should appear as concrete per-frame filenames in the cooked stage. UDIM sets must have existing tiles. Custom resolver plugins, assets hidden inside opaque binaries, USDZ packages, dynamic filenames in shader code, custom plugins/HDAs, and procedural geometry are not supported automatically. Bake these to portable USD geometry and explicit file assets; do not assume a successful export proves compatibility of custom shader code.
- MaterialX XML is parsed for `file`, `href`, and `type="filename"` values; nested files are copied recursively. Files with arbitrary non-asset string dependencies need conversion to explicit asset-valued data.
- Motion blur samples already on the cooked stage are retained. Test caches and simulations at the requested frame order; exporting large scenes is synchronous in Houdini and may take time and disk space.
- XPU selects one configured GPU and disables the Embree CPU device, so GPU failures are visible. CPU rendering uses Karma CPU. GPU statistics cover all GPUs and update about once per second; frame progress and ETA update after each completed frame.
- Commercial and Indie installations must have valid, compatible Houdini/Karma entitlements on both hosts as required by SideFX. Licensing is checked by native tools; this project does not install licenses or bypass restrictions. Apprentice / `.hipnc` is rejected. Verify Indie export, format, resolution, and license compatibility with the actual Houdini build before production. Native export/render errors remain errors.

## 1. Inspect and prepare Ubuntu

Run from this directory:

```bash
python3 linux/diagnose.py
nvidia-smi --query-gpu=index,uuid,name,driver_version,memory.total --format=csv
```

The diagnostic is read-only. `husk --help` discovers tools; it is **not** a license checkout or proof of XPU availability. `hython` tests license availability separately. A successful real XPU frame is still required.

Install Houdini 22 using the SideFX installer and license it through License Administrator. This project never installs or modifies Houdini or GPU drivers. Check the exact build requirements at [SideFX system requirements](https://www.sidefx.com/Support/system-requirements/). At development time SideFX lists NVIDIA 580 production/studio or 595 recommended; the installed driver meets that documented branch baseline, but runtime compatibility remains untested.

Source the existing installation and deploy the service:

```bash
cd /opt/hfs22.0.BUILD
source ./houdini_setup
cd /path/to/houdini-remote-render
bash linux/install.sh --hfs /opt/hfs22.0.BUILD --gpu 0 --start
```

Prefer a stable GPU UUID from `nvidia-smi` instead of `0` if device order changes. Installer verifies the selected GPU, driver baseline, executables, Houdini version, and `hython` license category. It stops without deployment when Houdini is absent. Existing deployment files require an interactive replacement confirmation; jobs and outputs are retained. Root is fixed at `~/houdini-render` for SSH clients.

Layout:

```text
~/houdini-render/
  jobs/<id>/status.json     # progress, timing, GPU measurements and errors
  scenes/<id>/             # immutable-by-convention checksummed input bundle
  assets/                  # reserved for future shared asset cache
  outputs/<id>/            # numbered results plus checksum manifest
  logs/<id>.<frame>.log     # husk stdout/stderr
  scripts/                 # deployed Linux and shared modules
  server.json              # Linux-only HFS and GPU configuration
  queue.sqlite             # persistent queue, WAL mode
```

```bash
systemctl --user status houdini-render.service
journalctl --user -u houdini-render.service -n 100
sudo loginctl enable-linger "$USER"
```

Linger makes the user service available after boot without an interactive login. The installer prints this command but does not run it. One worker is enforced with an OS lock. Queued jobs survive restart. Jobs interrupted during a worker crash/reboot are marked failed on restart; submit again after inspecting their logs. Completed frames and inputs remain on the server. Only per-job renderer scratch is automatically removed after completion/failure/cancellation. No age-based output deletion occurs.

## 2. Configure SSH privately

Use LAN or Tailscale connectivity. There is no render listening port; access is the existing SSH service only. Keep SSH reachable only through the private network/firewall; do not forward it on a public router. The installer preserves existing sshd and firewall policies.

If OpenSSH is absent, the installer can explicitly install/enable it with `--enable-ssh` (requires sudo). Review network binding/firewall settings first, particularly if this computer has a public interface. Without this option, no SSH service changes are made.

On Windows PowerShell:

```powershell
ssh-keygen -t ed25519
ssh your-linux-user@100.x.y.z
```

Verify the server's host-key fingerprint through a trusted channel before accepting it. Obtain the fingerprint locally on Ubuntu with `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`. Add **only the public key** from Windows to Ubuntu `~/.ssh/authorized_keys` (directory mode 700, file mode 600); do not replace existing keys. Test key-only access:

```powershell
ssh -o BatchMode=yes your-linux-user@100.x.y.z python3 --version
```

If using a passphrase, load your key into the Windows OpenSSH agent. Paramiko uses the agent or standard local key files and rejects unknown/changed host keys. It never asks for or stores a password. Do not place private keys, passwords, or connection files in the project. The SSH account owns the renderer and should be dedicated to trusted rendering work if feasible.

## 3. Install the Windows shelf tool

Copy this whole directory to a new folder, for example `C:/Tools/houdini-remote-render`; do not overwrite an existing deployment without backing it up. Linux and Windows do not need shared drives.

In Houdini 22's **Command Line Tools** terminal, install the only extra runtime dependency for the Windows client:

```text
hython -m pip install --user -r C:/Tools/houdini-remote-render/requirements-windows.txt
```

Use the Python environment that Houdini 22 actually runs. If user package installs are disabled, install into a separate user-owned dependency folder and add it to `sys.path`; do not alter Houdini's bundled files.

Create a shelf tool named **Remote Render**, set its language to Python, and paste:

```python
import sys
base = 'C:/Tools/houdini-remote-render'
for path in (base, base + '/windows'):
    if path not in sys.path:
        sys.path.insert(0, path)
import remote_render_panel
remote_render_panel.show()
```

Connection settings and pending job destinations are saved to `%USERPROFILE%/.houdini-remote-render/connection.json`. You may copy `windows/config.example.json` there **only if no settings file already exists**, or enter host/username/output in the panel. Port defaults to 22 and can be changed in that local JSON. Private keys remain in the SSH agent or your normal `.ssh` directory.

## 4. Submit Phoenix

1. Open Phoenix on Windows. Save current edits. Prepare its Solaris stage with camera, a single render product, and a single Render Settings prim. Choose its output LOP path, such as `/stage/OUT`.
2. Click **Remote Render**. Enter the Ubuntu LAN/Tailscale hostname and SSH user. The scene field defaults to the open `.hip`/`.hiplc`. To load another scene, save your current changes first and enter that file path.
3. Select engine, range/step, width/height, EXR/PNG, and a Windows destination. Use a separate destination per shot/job to avoid filename collisions.
4. Acknowledge that you trust the scene and assets, then **Submit Render**. Loading/cooking scenes can execute code on Windows. The current scene is saved before export.
5. Keep the panel open for automatic monitoring and result retrieval. Closing the panel/Houdini does not cancel server jobs; reopen it to resume polling persisted pending jobs. **Render Status**, **Cancel Render**, and **Download Results** apply to the Job ID field. The tool monitors all its pending jobs in round-robin order.

Results use `frame.0001.exr` or `frame.0001.png`. Download first writes `.part`, resumes from its current byte count, verifies size and SHA-256, and renames the file. Identical existing frames are skipped; different existing frames trigger an error instead of being overwritten. Linux originals remain. There is deliberately no automatic remote cleanup command; delete inputs/outputs explicitly only after confirming your backups.

Failed exports/transfers can leave a bundle under the Windows temporary directory `hrr-<uuid>`. Successful submissions remove local staging. Inspect or remove abandoned bundles explicitly. Remote partially uploaded bundles are not queued until all checksum validation passes. A transfer may be retried using the CLI below; uploads restart individual files, downloads resume byte offsets.

## 5. Verify actual rendering before production

First test Linux locally in a sourced Houdini 22 shell, using a fresh output directory:

```bash
hython tests/verify_local_render.py --engine xpu --gpu 0 --output /tmp/hrr-xpu-check-001
```

The included `tests/glass.usda` contains a camera, moving sphere, dome/distant lights, MaterialX standard-surface glass, and render settings. The verifier renders frames 1–3, checks outputs, saves logs/timing/license information, and requires GPU device evidence in XPU logs. Inspect those logs for the RTX 5060 Ti/OptiX device and errors. File existence alone is not proof of a correctly shaded image: open the rendered frames and confirm glass, lighting, framing, and motion.

Generate a small test HIP in a **fresh** process, with a destination that does not exist (use `.hiplc` for Indie):

```text
hython tests/create_test_hip.py C:/Users/YOU/Documents/hrr-glass.hip
```

Open that file on Windows and submit `/stage/OUT`, frames 1–3 at 128×128 XPU. Confirm all server statuses complete, downloaded frames match server SHA-256, and the images look correct. Repeat with a single frame and with cancellation of a longer job. Only then try Phoenix. This is the acceptance test still outstanding on the inspected machines.

## Tests and CLI

```bash
python3 -m unittest discover -s tests -v
```

Development validation on 2026-10-22: **17 tests passed, 1 live test skipped**, using an isolated Python environment with OpenUSD (`usd-core`) and Paramiko. Python compilation and installer shell syntax checks passed. The installer was exercised on this machine and correctly stopped at missing Houdini before deployment. Houdini export-contract tests mock `hou` while using real OpenUSD; they do not validate the Houdini 22 UI or license runtime.

Core tests use a deliberately fake `husk` executable to test process/output handling without a Houdini license. USD packaging tests run under Houdini's Python or an optional isolated `usd-core` environment. Neither kind proves Karma support. The live SSH/render test is skipped unless explicitly configured.

On Windows with client dependencies available:

```text
hython windows/submit_render.py ping
hython windows/submit_render.py status --job JOB_ID
hython windows/submit_render.py cancel --job JOB_ID
hython windows/submit_render.py download --job JOB_ID --output D:/Phoenix/renders/test
hython windows/submit_render.py submit --bundle C:/path/to/exported-bundle
```

CLI also accepts `--config C:/path/to/connection.json`. To run the live automated end-to-end test, set `HRR_LIVE_CONFIG` to that configuration and `HRR_LIVE_BUNDLE` to a fresh **trusted**, real Houdini-exported bundle, then run the tests. The test queues the bundle, waits up to ten minutes, and verifies downloads. A previously submitted ID cannot be submitted twice; export a fresh bundle for each test.

## Security model

SSH key authentication and strict host keys secure transport. Job IDs, paths, enums, integer bounds, manifests, and checksums are validated. Client data is sent as JSON on stdin to a fixed remote command, never interpolated into a shell command. Render processes use argument arrays and isolated process groups. Cancellation only targets the active frame's group; the service also owns that group's descendants. Assets and outputs are restricted to configured bundle/output directories, including resolving traversal/symlink checks on server input files.

This is a **trusted-user renderer**, not a hostile-scene sandbox. USD, MaterialX, Houdini plugins, and native renderers have code/data execution surfaces. Only submit scenes/assets you trust; the panel requires explicit acknowledgment. Server never loads a HIP, and husk procedurals are disabled; unsupported procedural geometry must be baked. The SSH account can execute commands by design. Do not give untrusted people its key or use this as a public render service.

## References

- [SideFX Houdini 22 requirements](https://www.sidefx.com/Support/system-requirements/)
- [husk flags, engine selection, frame/output overrides, licensing](https://www.sidefx.com/docs/houdini/ref/utils/husk.html)
- [Karma XPU devices and environment variables](https://www.sidefx.com/docs/houdini/solaris/karma_xpu.html)
- [SideFX licensing](https://www.sidefx.com/Support/licensing/)
- [How husk uses licenses](https://www.sidefx.com/faq/question/how-are-licenses-used-when-issuing-the-husk-command/)
