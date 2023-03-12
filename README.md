Yet Another Btrfs Snapshotter

NOTE This is currently only tested and meant for Arch Linux.

# Installing

## Arch with AUR (Recommended)

```bash
# Use your favorite AUR manager. E.g. -
yay -S yabsnap
# OR,
pamac install yabsnap
```

## Command-line Install
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

# Quick Start

- Create a config:
`yabsnap create-config CONFIGNAME`
  - This will create a file `/etc/configs/yabsnap/CONFIGNAME.conf`
- Edit the config to change the `source` field, to point to a btrfs mounted directory. E.g. `source = /`, or `source = /home`.

Also, ensure that the service is enabled,
```sh
sudo systemctl enable --now yabsnap.timer
```

You should now have automated backups running.

# Config File

The example config file shows options that you can change to configura the
behavior of backup and cleanups.

```ini
[DEFAULT]
# Source, must be a btrfs mount.
source = /home

# Destination directory and prefix. Timestamp will be added to this prefix.
dest_prefix =

# How much time must pass after a snap before creating another one.
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

# How much time must have bassed from last installation to trigger a snap.
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
* `--source` Restricts to the config which has the specified source.

## Commands
### `yabsnap create-config NAME`
Creates a new config by `NAME`. \
Immediately after that, the `source` and `dest_prefix` fields must be filled
out.

### `yabsnap list`
Lists existing snaps. Example -
```
Config: source=/home
S    2022-10-06 14:30:47  /.snapshots/@home-20221006143047
S    2022-10-06 15:30:07  /.snapshots/@home-20221006153007
S    2022-10-06 16:30:19  /.snapshots/@home-20221006163019
 I   2022-10-06 16:46:59  /.snapshots/@home-20221006164659  pacman -S perl-rename

Config: source=/
  U  2022-10-06 12:23:12  /.snapshots/@root-20221006122312  test_comment
 I   2022-10-06 16:46:59  /.snapshots/@root-20221006164659  pacman -S perl-rename
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

* I deleted a snapshot manually. Will it confuse yabsnap?
  * No, you can also delete the corresponding metadata manually. It's in the
    same directory. If you used `yabsnap delete PATH_TO_SNAPSHOT`, it would take
    care of that for you.

* How do I delete multiple snaps?
  * The quickest way is to delete them manually. Remove the snaps, and
    corresponding `-meta.json` files.
