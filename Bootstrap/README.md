# Native macOS bootstrap

`GrowtopiaLauncher` is a universal Mach-O executable built for macOS 11.0 or newer, with Intel x86_64 and Apple Silicon arm64 slices.

Put it at `Growtopia Launcher.app/Contents/MacOS/GrowtopiaLauncher` with executable permission and set `CFBundleExecutable` to `GrowtopiaLauncher`.

The executable resolves its own location with `_NSGetExecutablePath` and `realpath`, then executes the built-in runtime with this argument vector:

```
/usr/bin/osascript -l JavaScript /absolute/bundle/Contents/Resources/ui.js /absolute/bundle/Contents/Resources
```

There is no shell evaluation, download, or updater logic in this bootstrap. Startup errors are appended to `~/Library/Logs/Growtopia Launcher UI.log`. The JXA UI receives its absolute Resources directory as `run(argv)`'s first argument.

Build using Zig 0.13.0 and Python 3:

```
python3 build.py /absolute/path/to/zig
```

The build script checks Mach-O architectures and load-command bounds, validates each arm64 ad-hoc signature's SHA-256 page hashes, and creates a correctly aligned universal container. Only the native executable is needed on the user's Mac. Zig and Python are build dependencies, not runtime dependencies.

The arm64 slice has a linker-generated ad-hoc signature. The Intel slice is unsigned. Neither slice has a Developer ID certificate or notarization, and this is not a signature over the complete application bundle. Native launch, Gatekeeper, and AppKit behavior still need testing on macOS.

Do not distribute the `toolchain` directory or intermediate `launcher-*` files as part of the user application. Source distribution needs only `launcher.c`, `build.py`, and this README.
