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
However, neither supports customized of backup location, (e.g. [Arch recommended
layout](https://wiki.archlinux.org/title/snapper#Suggested_filesystem_layout)).
Adhering to such layouts, and rolling back using them, sometime [involve
non-obvious
workarounds](https://wiki.archlinux.org/title/snapper#Restoring_/_to_its_previous_snapshot).
The motivation for `yabsnap` was to create a simpler, hackable and customizable
backup system.

|                     | yabsnap | timeshift          | snapper                |
| ------------------- | ------- | ------------------ | ---------------------- |
| Custom sources      | ✓       | Only root and home | ✓                      |
| Custom destinations | ✓       |                    |                        |
| Pacman hook         | ✓       |                    | With snap-pac          |
| File system         | btrfs   | btrfs, ext4        | btrfs                  |
| GUI                 |         | ✓                  | With snapper-gui       |
| Rollback            | ✓       | ✓                  | Only default subvolume |


# Configuring

* Run `yabsnap create-config CONFIGNAME`
* Then edit the file it creates.

# Usage

## Global flags

* `--dry-run` Disables all snapshot changes.
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

 The indicators `S`, `I`, `U` respectively indicate scheduled, installation, user backups.

### `yabsnap create`
 Creates an user backup.

 Optionally add comment with `--comment "COMMENT"`.

### `yabsnap delete`
Deletes a snapshot.

E.g.
`yabsnap delete /.snapshots/@home-20221006143047`
\
Or,
`yabsnap delete 20221006143047  # Deletes all backups with this timestamp.`

### `yabsnap rollback-gen`
Generates a script for rolling back.

E.g.
`yabsnap rollback-gen /.snapshots/@home-20221006143047`
\
Or,
`yabsnap rollback-gen 20221006143047`

Just running it will not carry out any changes, it will only display a script on
the console. \
The script must be stored and executed to perform the rollback.

# FAQ

* I deleted a snapshot manually. Will it confuse yabsnap?
  * No, you can also delete the corresponding metadata manually. It's in the
    same directory. If you used `yabsnap delete PATH_TO_SNAPSHOT`, it would take
    care of that for you.

* How do I delete multiple snaps?
  * The quickest way is to delete them manually. Remove the snaps, and
    corresponding `-meta.json` files.
