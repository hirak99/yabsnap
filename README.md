## Yet Another Btrfs(*) Snapshotter

(*) Along with btrfs, we now fully support rsync snapshots.

Currently this is tested on Arch and Fedora, and should work in most other
distributions.


# Installing

## Arch Linux: Install from AUR

Use your preferred AUR handler -

```bash
yay -S yabsnap
# OR
paru -S yabsnap
```

Or install manually from AUR -
```sh
mkdir yabsnap_tmp && cd yabsnap_tmp
curl 'https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=yabsnap' -o PKGBUILD
mkpkg -si
```

## Other Distributions: Install from git
```bash
git clone https://github.com/hirak99/yabsnap
cd yabsnap

# To install -
sudo scripts/install.sh

# To uninstall -
sudo scripts/uninstall.sh
```


# What does it do?

Yabsnap easily and flexibly orchestrates btrfs snapshots.

* Supports system snapshots/boot environments/system restore points,
  snapshots of user data, as well as general-purpose snapshots.
* Allows configuration of different snapshotting schedules and
  snapshot retention policies for different data sets.
* Supports multiple source filesystems by using drop-in config files.
  Different drives necessarily have different snapshot targets, and
  Yabsnap is currently (Jun 2025) the only btrfs snapshot manager that
  can achieve this.
* Provides a wizard that generates each of these config files.
* Optionally annotates snapshots with a description.
* Supports pre-installation snaps with auto-generated comments.
  TODO: What is a "pre-installation snap"?
* Does not modify source subvolumes when making snapshots.
* TODO: Say something about pruning.
* Facilitates rollbacks by heuristically generating a shell script of
  suggested commands (requires the use of the btrfs backend).

## Alternatives

Some good alternatives are timeshift, snapper; both very good in what they do.
However, neither supports customized of snapshot location, (e.g. [Arch recommended
layout](https://wiki.archlinux.org/title/snapper#Suggested_filesystem_layout)).
Adhering to such layouts, and rolling back using them, sometime [involve
non-obviousworkarounds](https://wiki.archlinux.org/title/snapper#Restoring_/_to_its_previous_snapshot).
The motivation for `yabsnap` was to create a simpler, hackable and customizable
snapshot system.

|                     | yabsnap      | timeshift                  | snapper                |
| ------------------- | ------------ | -------------------------- | ---------------------- |
| Custom sources      | ✓            | Only root and home (1)     | ✓                      |
| Custom destinations | ✓            |                            |                        |
| Pacman hook         | ✓            | Via timeshift-autosnap (2) | Via snap-pac           |
| Snapshot Mechanisms | btrfs, rsync | btrfs, rsync               | btrfs                  |
| GUI                 |              | ✓                          | With snapper-gui       |
| Rollback            | ✓ (3)        | ✓                          | Only default subvolume |

(1) timeshift does not allow separate schedules or triggers for root and home.

(2) At the time of writing, `timeshift-autosnap` does not tag the snapshot with
pacman command used.

(3) Automatic rollback is only implemented for btrfs snapshots (as of 202511).


# Usage

## Quick Start

- Create a config:
`yabsnap create-config CONFIGNAME`
  - This will create a file `/etc/yabsnap/configs/CONFIGNAME.conf`
- Edit the config to change the `source` field, to point to a btrfs mounted directory. E.g. `source = /`, or `source = /home`.

Also, ensure that the service is enabled,
```sh
sudo systemctl enable --now yabsnap.timer
```

You should now have automated backups running.

## Recommended Subvolume Layout

Below is an example layout.

| Subvolumes       | Mount Point   | Mount Options        |
| ---------------- | ------------- | -------------------- |
| @                | `/`           | `subvol=@`           |
| @home (optional) | `/home`       | `subvol=@home`       |
| @.snapshots      | `/.snapshots` | `subvol=@.snapshots` |

You can also refer to [suggested filesystem layout in Arch Wiki here](https://wiki.archlinux.org/title/Snapper#Suggested_filesystem_layout).

Tips -
- **Do not use the root subvolume (subvolid=5) for root directly for root.** Instead use a named subvolume e.g. `@`, and mount that for your root filesystem.
  - If you don't have a separate subvolume for root yet, you can create one by taking a snapshot of your existing root, then deleting other directories and adjusting your `fstab` to add `subvol=@` (and regenerate the GRUB config with `grub-mkconfig` if you are using grub).
- **Mount by** `subvol=NAME`, instead of `subvolid=NUMERIC_ID`. This is necessary to allow rollbacks without touching the fstab.
- Create a top level subvolume, e.g. `@.snapshots`, to contain all snapshots.

### Example Shell commands to set up

Assuming you already have root mounted from a subvolume (e.g. `@`), below are some shell commands to create `@.snapshot` -

```sh
# Mount the top level subvolume (id 5) into a temporary mount dir.
TOP=/run/mount/btrfs_top  # Temporary path to mount subvol.
mount --mkdir /dev/sdX $TOP -t btrfs -o subvolid=5
# Assuming @ (or root) and optionally @home already exists,
# all you need is a new subvolume for snapshots.
btrfs subvolume create $TOP/@.snapshots
# Also need directory to mount @.snapshots into -
mkdir /.snapshots
```

### fstab
And then add a line to your `fstab` to mount the @.snapshots subvolume on every boot.

Example lines for fstab -
```fstab
# fstab: Example for root. Notably, use subvol=/@, do not use subvolid.
UUID=BTRFS_VOL_UUID  /  btrfs  rw,noatime,ssd,space_cache=v2,subvol=/@,compress=zstd  0  1

# fstab: Example for /.snapshots.
UUID=BTRFS_VOL_UUID  /.snapshots  btrfs  rw,noatime,ssd,space_cache=v2,subvolid=260,subvol=/@.snapshots  0  2
```

Replace `BTRFS_VOL_UUID` with the uuid from `lsblk
-f`, for the partition where the subvolumes reside.

## Config File

You can create a config with `yabsnap create-config NAME`.

This will create a config /etc/yabsnap/NAME.conf. You will need to edit it and
fill in `source` and `dest_prefix` (e.g. `source = /` and `dest_prefix =
/.snapshots/@root-`). You can also configure other aspects of snapshots by
editing the config.

Once you have set up a config, automated snapshots should start running.

You can see how the default config looks like here: [Default config](./src/code/example_config.conf)


# Command Line Interface

## Global flags

* `--dry-run` Disables all snapshot changes. Shows what it would do instead.
* `--config-file CONFIG-FILE` Specify which config file to operate on.
* `--source SOURCE` Restricts to the config which has the specified source, for example `--source /home`. The source must be specified in one of the config files. Alternatively, a config-file directly may also be specified with `--config-file CONFIG-FILE`.

## Commands
### `yabsnap create-config NAME`
Creates a new config by `NAME`. \
Immediately after that, the `source` and `dest_prefix` fields must be filled
out.

### `yabsnap list`
Lists existing snaps. Example -
```
Config: /etc/yabsnap/configs/home.conf (source=/home)
Snaps at: /.snapshots/@home-...
  20221006143047  S    2022-10-06 14:30:47
  20221006153007  S    2022-10-06 15:30:07
  20221006163019  S    2022-10-06 16:30:19
  20221006164659   I   2022-10-06 16:46:59  pacman -S perl-rename

Config: /etc/yabsnap/configs/root.conf (source=/)
Snaps at: /.snapshots/@root-...
  20221006122312    U  2022-10-06 12:23:12   test_comment
  20221006164659   I   2022-10-06 16:46:59   pacman -S perl-rename
 ```

 The indicators `S`, `I`, `U` respectively indicate scheduled, installation, user(TODO: sysadmin-initiated, or unprivileged user?) snapshots.

### `yabsnap list-json`

Similar to list, but as machine readable **JSONL** (JSON Lines).

This is useful for programmatically building commands.

You can pipe the output through tools like [jq](https://jqlang.org/) to filter or
manipulate data. For example, you can use `jq` to filter:

```sh
# Filter all snaps created during installation.
yabsnap list-json | jq -c 'select(.trigger=="I")'

# Filter all snaps created during installation, and using home.conf.
yabsnap list-json | jq -c 'select(.trigger=="I" and (.config_file | endswith("/home.conf")))'
```

You can also restructure the output:
```sh
# Show only the timestamps.
yabsnap list-json | jq '.file.timestamp'
```

In [nushell](https://www.nushell.sh/), you process the JSONL output natively:

```nushell
yabsnap list-json | from json --objects
```

### `yabsnap create`
 Creates an user snapshot.

 Optionally add comment with `--comment "COMMENT"`.

### `yabsnap set-ttl PATH|TIMESTAMP --ttl TTL`

Sets a TTL or Time-To-Live for a snapshot.

E.g.
`yabsnap set-ttl /.snapshots/@home-20221006143047 --ttl '1 day'`

If a snapshot has a TTL, it will be deleted soon after the TTL expires.
Snapshots with TTL will not be part of any other automated deletion operation.
Of course, they can still be deleted manually, with the `delete` or `batch-delete`
commands.

> [!TIP] To prevent a scheduled snapshot from automatic deletion you can set a long TTL for it, e.g. '999 years'.

### `yabsnap delete PATH|TIMESTAMP`
Deletes a snapshot.

E.g.
`yabsnap delete /.snapshots/@home-20221006143047`
\
Or,
`yabsnap delete 20221006143047  # Deletes all snapshots with this timestamp.`

### `yabsnap batch-delete [--start TIMESTAMP] [--end TIMESTAMP] [--indicator S|I|U]`
Batch delete snapshots.

```sh
# Note: For these examples, assume there is a snapshot as shown in the above `yabsnap list` command.

# Delete all snapshots under all configuration files.
yabsnap batch-delete

# Delete all snapshots including and after 2022-09-25_17:21.
yabsnap batch-delete --start 20220925172100
# Or,
yabsnap batch-delete --start 2022-09-25_17:21

# Delete snapshots before 2022-10-06_15:30 (excluding that snapshot) where the indicator is S.
# Only root.conf's `20221006143047` will be deleted.
yabsnap batch-delete --indicator S --end 2022-10-06_15:30  # :00 is understood
```

### `yabsnap rollback-gen PATH|TIMESTAMP [--subvol-map SUBVOL_MAP]`
Generates a script for rolling back.

E.g.
`yabsnap rollback-gen /.snapshots/@home-20221006143047`
\
Or,
`yabsnap rollback-gen 20221006143047`

Just running it will not carry out any changes, it will only display a script on
the console. \
The script must be stored and executed to perform the rollback operation.

**`... --subvol-map SUBVOL_MAP`**

An advanced feature used to override automatic identification of subvolumes at the time
of rollback.

The `SUBVOL_MAP` should be of the format `"MOUNT_DIR:SUBVOL_NAME ..."`.
For example, `--subvol-map "/:@ /home:@home"`.

When `--subvol-map` is used, the generated script will include a comment confirming the
override.

Context: This option is particularly relevant for rolling back snapshots taken before
version `v2.3.0`. Earlier versions did not store subvolume names with snapshots, and
instead detected them based on mount points of directories like `"/"` or `"/home"`.
While this worked for online rollbacks (where the subvolumes were mounted consistently
with the snapshot), it failed in offline environments where subvolumes could be mounted
differently (e.g., mounting`/@.snapshots/@root-20250921193009` as root, when the actual
subvolume to roll back is `@`).

For snapshots taken **after** `v2.3.0`, this option is no longer necessary, as the
subvolume names are now stored with the snapshots.

### `yabsnap rollback PATH|TIMESTAMP [--subvol-map SUBVOL_MAP] [--noconfirm]`

Shows a rollback script, interactively confirms, and executes it.

If you are a person who likes taking heavy risks, you can skip the confirmation
with `... --noconfirm`.

The optional arg `--subvol-map` works similarly as rollback-gen.

# FAQ

## General

- Why Python?
  - Python, when written with high code quality, serves as an excellent
    orchestrator. This is precisely what we needed for Yabsnap, with a focus on
    (1) expressiveness, (2) ease of maintenance, and (3) accessibility for
    contributors. While low-level speed or efficiency is not a primary concern
    for us, modern Python supports static type checking, making it a robust
    choice for our needs. To ensure code health and maintainability, we
    emphasize strict adherence to code style and readability standards.

- Does it work on other distros than Arch?
  - It _should_ work if installed with `sudo scripts/install.sh`, although
    - Installation hook will not work.
    - And rest of the features should be tested.
  - If you'd want full support on a distro, I'm happy to know so that I can
    evaluate and find a way to prioritize it. Please open an issue.

- Why is Google in the copyright?
  - I began this project while I was at Google. To release it as open source, I
    followed Google's open-sourcing process, which required including Google in
    the copyright notice. That said, I'm grateful to Google and my team for
    supporting and encouraging me in my goal to share the project with the
    community.

## Operational

- I deleted a snapshot manually. Will this confuse yabsnap?
  - No. You should also delete the corresponding metadata `-meta.json` manually
    (it's in the same directory). If you used `yabsnap delete PATH_TO_SNAPSHOT`,
    it would take care of that for you.

- How do I delete multiple snaps?
  - You can use `yabsnap batch-delete ...`
  - You can also delete them manually. Remove the snaps with `btrfs subvolume snapshot
    del YOUR_SNAP`, and corresponding `-meta.json` files.

## Rollback Related

- Can I roll back rsync or bcachefs snapshots?
  - Not currently. Rollback is supported only for btrfs snapshots.

- Does `yabsnap` support _online_ rollback?
  - Yes. The `rollback-gen` command to generate a rollback script, or `rollback` command
    to apply the script. It can be run and executed even when the subvolume is mounted.

    The generated script is designed to let you continue working in the live environment
    and switch over to the rolled-back state on the next reboot.

    > [!NOTE]
    > It is **strongly recommended** that you read and understand the script
    > before committing to a rollback. Doing so will help you see exactly what
    > it does and how to reverse it if needed. The generated script is
    intentionally kept small and readable for this reason.

- Does `yabsnap` support _offline_ rollback?
  - Yes! Starting from `v2.3.0`, `yabsnap` stores the necessary information to perform
    offline rollbacks in snapshots.
  - **For snapshots taken prior to `v2.3.0`, an additional argument is required.** For
    these snapshots, `yabsnap` relies on the currently mounted subvolume to determine
    the subvolume to rollback. While this works well for online rollbacks, it's not
    suitable for offline environments. For example, `grub-btrfs` might mount the
    subvolume `/@.snapshots/@root-20250921193009` as root, allowing you to log into it.
    However, to roll back, `yabsnap` needs to know that root subvolume is `@` under
    normal operations. To specify this, you can use the `--subvol-map "/:@"`
    argument.

    > [!NOTE] NOTE: As with live rollback, it’s strongly recommended that you review the
    > generated script before running it, to ensure you understand what it will do and
    > how to undo it if necessary.

- How is rollback handled for nested subvolumes?
  - Rolling back nested subvolumes is supported. However, due to the way BTRFS handles
    subvolumes, additional steps are required to move them over after you log in to the
    rolled-back snapshot following a reboot.

    The rollback script will automatically generate the necessary instructions for you to follow.

  - For more context, refer to the discussion in [Issue
    #52](https://github.com/hirak99/yabsnap/issues/52), especially [this
    comment](https://github.com/hirak99/yabsnap/issues/52#issuecomment-2746173900).
