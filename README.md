# Simorgh

Houdini 22.0.429 (Apprentice) animation project.

Set the Houdini project (`$JOB`) to the repository root:

```text
E:/Wirling Worlds/Simorgh
```

## Layout

```text
assets/
  characters/
    abstract_fish/       current fish asset and After Effects work
    phoenix/             Houdini rig, After Effects rig, and source artwork
  effects/
    ink_drop/            Houdini and After Effects ink-drop projects
shots/
  seq01/shot010/         production shot files, references, and reviews
tools/
  houdini_remote_render/ remote-render utilities
archive/
  abstract_fish_versions/ superseded fish versions
  duplicates/             preserved duplicate project copies
  packages/               historical delivery archives
  tests/                  obsolete test scenes
_output/                   local generated output; ignored by Git
```

Use `$HIP`-relative paths inside Houdini scenes whenever possible. Scene versions,
scripts, documentation, source textures, and selected review media belong in Git.
Renders, caches, auto-saves, logs, and application-generated backups do not.

Large binary assets are managed by Git LFS according to `.gitattributes`.
