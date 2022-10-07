Yet Another Btrfs Snapshotter

NOTE This is currently only tested and meant for Arch Linux.

# Installing

```bash
sudo ./install.sh
```

## To uninstall
```bash
sudo ./uninstall.sh
```

# Configuring

* Run `yabsnap create-config CONFIGNAME`
* Then edit the file it creates.

# Commands

## `yabsnap create-config NAME`
Creates a new config by `NAME`. \
Immediately after that, the `source` and `dest_prefix` fields must be filled
out.

## `yabsnap list`
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

 ## `yabsnap create`
 Creates an user backup.

 Optionally add comment with `--comment "COMMENT"`.

## `yabsnap delete`
Deletes a snapshot.

## Global flags

* `--dry-run` Disables all snapshot changes.
* `--source` Restricts to the config which has the specified source.

E.g.
`yabsnap delete /.snapshots/@home-20221006143047`.


# FAQ

* I deleted a snapshot manually. Will it mess it up?
  * No, you can also delete the corresponding metadata manually. It's in the
    same directory. If you used `yabsnap delete PATH_TO_SNAPSHOT`, it would take
    care of that for you.
