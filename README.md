Yet Another Btrfs Snapshotter

Note: Currently this is tested on Arch and Fedora, but should work in most other
distributions.

# Installing

## Arch Linux: Install from AUR

```bash
# Use your favorite AUR manager. E.g. -
yay -S yabsnap
# OR,
pamac install yabsnap
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

Allows managing scheduled btrfs snapshots.

* Supports multiple sources, and customizing destination directory. Use `yabsnap
  create-config` to configure what gets snapped, and when.
* Supports pre-installation snaps with auto-generated comments.
* Supports rollback - by generating a short shell script.

## Alternatives

Some good alternatives are timeshift, snapper; both very good in what they do.
However, neither supports customized of snapshot location, (e.g. [Arch recommended
layout](https://wiki.archlinux.org/title/snapper#Suggested_filesystem_layout)).
Adhering to such layouts, and rolling back using them, sometime [involve
non-obvious
workarounds](https://wiki.archlinux.org/title/snapper#Restoring_/_to_its_previous_snapshot).
The motivation for `yabsnap` was to create a simpler, hackable and customizable
snapshot system.

|                     | yabsnap | timeshift                  | snapper                |
| ------------------- | ------- | -------------------------- | ---------------------- |
| Custom sources      | ✓       | Only root and home (1)     | ✓                      |
| Custom destinations | ✓       |                            |                        |
| Pacman hook         | ✓       | Via timeshift-autosnap (2) | Via snap-pac           |
| File system         | btrfs   | btrfs, ext4                | btrfs                  |
| GUI                 |         | ✓                          | With snapper-gui       |
| Rollback            | ✓       | ✓                          | Only default subvolume |

(1) timeshift does not allow separate schedules or triggers for root and home.

(2) At the time of writing, `timeshift-autosnap` does not tag the snapshot with
pacman command used.

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

| Subvolumes | Mount Point | Mount Options |
|---|---|---|
| @ | `/` | `subvol=@` |
| @home (optional) | `/home` | `subvol=@home` |
| @.snapshots | `/.snapshots` | `subvol=@.snapshots` |

NOTE: The names can be different; you do not need to rename your existing subvolumes.

Tips -
- Mount by `subvol=NAME`, instead of `subvolid=NUMERIC_ID`. This is necessary to allow rollbacks without touching the fstab.
- Create a top level subvolume for all snapshots.

To set this up in shell, mount the top volume and create a @.snapshot subvolume -
```sh
# Mount the top level subvolume (id 5) into a temporary mount dir.
TOP=/run/mount/btrfs_top  # Temporary path to mount subvol.
mkdir $TOP
mount /dev/sdX $TOP -t btrfs -o subvolid=5
# Assuming @ (or root) and optionally @home already exists,
# all you need is a new subvolume for snapshots.
btrfs subvolume create $TOP/.snapshot
```

And then add a line to your `fstab` to mount the @.snapshots subvolume on every boot.

## Config File

Once you create a config, automated snapshots should start running.

You can further configure the behavior of snapshots by editing the config. Below
is how a config file looks like.

```ini
# All configurations must be under the [DEFAULT] section.
[DEFAULT]

# Source, must be a btrfs mount.
# For example, `source = /` or `source = /home`.
source =

# Destination including directory and prefix where the snapshots will be stored.
# For example, `dest_prefix = /.snapshots/@root-` will result in snapshots like
# "/.snapshots/@root-20230315120000".
# Time in the format YYYYMMDDhhmmss will be added to the prefix while creating snaps.
dest_prefix =

# Only one snap can be made within this interval.
# The intervals are counted from 1970 Jan 1, 12:00 AM UTC.
trigger_interval = 1 hour

# How much minimum time must pass before a snap can be cleaned up.
min_keep_secs = 1800

# How many user-created snaps to keep.
# User created snaps can are made with 'create' command.
keep_user = 1

# How many pre-installation snaps to keep.
# Any value more than 0 will enable pacman hook, and store snap on before pacman operation.
# Will also work for AUR managers such as yay, since AUR managers also use pacman.
keep_preinstall = 1

# How much time must have passed from last installation to trigger a snap.
# This prevents snaps multiple installations from a script to each trigger snap in short succession.
preinstall_interval = 5 minutes

# How many scheduled snaps to keep.
# If all are 0, scheduled snap will be disabled.
keep_hourly = 0
keep_daily = 5
keep_weekly = 0
keep_monthly = 0
keep_yearly = 0
```

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

 The indicators `S`, `I`, `U` respectively indicate scheduled, installation, user snapshots.

### `yabsnap create`
 Creates an user snapshot.

 Optionally add comment with `--comment "COMMENT"`.

### `yabsnap delete PATH|TIMESTAMP`
Deletes a snapshot.

E.g.
`yabsnap delete /.snapshots/@home-20221006143047`
\
Or,
`yabsnap delete 20221006143047  # Deletes all snapshots with this timestamp.`

### `yabsnap rollback-gen PATH|TIMESTAMP`
Generates a script for rolling back.

E.g.
`yabsnap rollback-gen /.snapshots/@home-20221006143047`
\
Or,
`yabsnap rollback-gen 20221006143047`

Just running it will not carry out any changes, it will only display a script on
the console. \
The script must be stored and executed to perform the rollback operation.

# FAQ

- Does it work on other distros than Arch?
  - It _should_ work if installed with `sudo scripts/install.sh`, although
    - Installation hook will not work.
    - And rest of the features should be tested.
  - If you'd want full support on a distro, I'm happy to know so that I can
    evaluate and find a way to prioritize it. Please open an issue.

- I deleted a snapshot manually. Will it confuse yabsnap?
  - No. You should also delete the corresponding metadata `-meta.json` manually
    (it's in the same directory). If you used `yabsnap delete PATH_TO_SNAPSHOT`,
    it would take care of that for you.

- How do I delete multiple snaps?
  - The quickest way is to delete them manually. Remove the snaps with `btrfs
    subvolume snapshot del YOUR_SNAP`, and corresponding `-meta.json` files.
