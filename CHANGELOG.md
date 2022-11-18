Unreleased
  * [[18.1]](https://github.com/hirak99/yabsnap/commit/eb0208e9ad994183a1edacd1f68987193c841611) Added `preinstall_interval` config
  * [[18.2]](https://github.com/hirak99/yabsnap/commit/193c7050a5cb9d45fc04c38c8958544096b1e4d3) Prevent skipped snapshots to run immediately on boot
  * [[18.3]](https://github.com/hirak99/yabsnap/commit/ae5539099e6dbcbd93829f7c11f55b4e264aa233) Added changelog

v1.07.1
  * [[17.1]](https://github.com/hirak99/yabsnap/commit/0bc1067dfd554ff3fb0f476755246f18e6b84c8f) All information and prompts now go to sys.stderr

v1.07
  * [[16.1]](https://github.com/hirak99/yabsnap/commit/9601dff935f39882232ed8ba7cf51df42dc9b3fd) Replace dict with tuple for internal deletion rules structure
  * [[16.2]](https://github.com/hirak99/yabsnap/commit/adfe22cbbba3d11d58a874ae508c4a29bb39cc61) Moved the duration buffer to configs
  * [[16.3]](https://github.com/hirak99/yabsnap/commit/deb4d2ef9332511470ae3e4ba430e76431fe15ce) Minor change to pacman hook's message

v1.06.5
  * [[15.1]](https://github.com/hirak99/yabsnap/commit/ff2b4deac9ede73a629deac649c0e9d6439a9a79) Refrained from showing duration like "1 year 5s"
  * [[15.2]](https://github.com/hirak99/yabsnap/commit/1bfbd519ceda83b28ed42a4592ccc365efbb1cfc) Reordered yabsnap list to show location before when

v1.06.4
  * [[14.1]](https://github.com/hirak99/yabsnap/commit/7d91f6e9b594c657fd3f9b9978c7519eb1d4e26f) list now displays how long ago snap was made

v1.06.3
  * [[13.1]](https://github.com/hirak99/yabsnap/commit/2eab809dcc7a315d67ff22c5c1843d1ae9be2ad5) Enforced flake8 and mypy linting
  * [[13.2]](https://github.com/hirak99/yabsnap/commit/71f28f21c6f6524ece58f7ab127b5b09aaf4de65) Separate tests requiring dependencies (flake8 and mypy)
  * [[13.3]](https://github.com/hirak99/yabsnap/commit/9fe5d72e6f4518d0cd66d888cbda478b5c242976) Create python-app.yml
  * [[13.4]](https://github.com/hirak99/yabsnap/commit/be5782be6227647009c5dfbd01ef3c42a7732e0a) Update README.md
  * [[13.5]](https://github.com/hirak99/yabsnap/commit/aee5f27e467bfee6994c147bb5ebf68ad44498f3) Added a test for rollbacker
  * [[13.6]](https://github.com/hirak99/yabsnap/commit/4415b7ad94396aee420189679de9a9dc7f39f3eb) Rollbacker makes more obvious if no snapshot matched
  * [[13.7]](https://github.com/hirak99/yabsnap/commit/99bd77a1ee492ebfdac71a0c79ffa6904b8d4b8e) Improved rollbacker test - covers multiple snaps
  * [[13.8]](https://github.com/hirak99/yabsnap/commit/de45f293c6c89fd3d6aa8e48842d1f873221fa28) Reorganized rollbacker_test mocks
  * [[13.9]](https://github.com/hirak99/yabsnap/commit/3724bdadd59547d80afb68270dfb09c557adaaaa) Keeps suffix same on scheduled run with multiple configs
  * [[13.10]](https://github.com/hirak99/yabsnap/commit/d3c60aa55c5afef7d0c5dba36184a8653ea830d4) Sync only once for one mount path
  * [[13.11]](https://github.com/hirak99/yabsnap/commit/4b4614601a8e139706918c65d97eb2a15dda5699) Moved global flags to a struct
  * [[13.12]](https://github.com/hirak99/yabsnap/commit/2af1f95f725b249dc3cd30b7fa38a07c4c023b47) Simplified main() function

v1.06.2
  * [[12.1]](https://github.com/hirak99/yabsnap/commit/78bf3e5690dd54f32417cc21fc5f94456c4ece1d) Look for pacman before continuing.

v1.06.1
  * [[11.1]](https://github.com/hirak99/yabsnap/commit/f46ddea516f8e06b223b94bc1c4f50c1ccde3983) Small changes - corrected rollbacker to include # in echo

v1.06
  * [[10.1]](https://github.com/hirak99/yabsnap/commit/22d489254c86da9aab7a5f497a478657d16742f4) Fixed program name for --help

v1.05.5
  * [[9.1]](https://github.com/hirak99/yabsnap/commit/b1cfeba1681ff448c205219e86eced2cee5f5b58) Move services to /usr/lib/systemd/system
  * [[9.2]](https://github.com/hirak99/yabsnap/commit/8043bac7b0d0964d65a76cfbaf02bb75e86e9a90) Use lsb-release to determine distro

v1.05.4
  * [[8.1]](https://github.com/hirak99/yabsnap/commit/cf2ee0bff37a3d500c169692f06599a765d2a933) Minor README change
  * [[8.2]](https://github.com/hirak99/yabsnap/commit/68837f664984f23b0aff035669fd1656391e0fbf) Added and clarified some features in alternatives
  * [[8.3]](https://github.com/hirak99/yabsnap/commit/ff8031804a5090207224da42fb978de198ae2640) Honors the --source global argument for create-config

v1.05.3
  * [[7.1]](https://github.com/hirak99/yabsnap/commit/262bceb9d72c984bf150b03e780aabd33367bcc2) Added Google License

v1.05.2
  * [[6.1]](https://github.com/hirak99/yabsnap/commit/6e1235f983e7b21eb14446d6e028764e5f92f342) Minor edits
  * [[6.2]](https://github.com/hirak99/yabsnap/commit/9d46263c21bc8b8aff97cea9ae983e9e97c3cdad) Config file now automatically sets dest_prefix

v1.05.1
  * [[5.1]](https://github.com/hirak99/yabsnap/commit/9676eaba865db4954ef945f8bd33a2b611c230f6) Added manpage
  * [[5.2]](https://github.com/hirak99/yabsnap/commit/199840cd287e56e911425737dbd1de11833a0aae) Made timer persistent; shows friendly error on bad config

v1.05
  * [[4.1]](https://github.com/hirak99/yabsnap/commit/04474229e7babef30c39a77d7d290a28a7a8d0e7) Added AUR installation to README.md
  * [[4.2]](https://github.com/hirak99/yabsnap/commit/fdcc12f21a4f257224452e30c9e8ecfa46d7196d) Added motivation in README.md
  * [[4.3]](https://github.com/hirak99/yabsnap/commit/fb0efc2aa655add6d6fed6ffc26f7748e64478dd) Correct yabsnap link for AUR

v1.03
  * [[3.1]](https://github.com/hirak99/yabsnap/commit/3bf9e5ecb59c2e6efce10438c5d13e5921b7de88) Some more changes -

v1.01
  * [[2.1]](https://github.com/hirak99/yabsnap/commit/286d4185a1b6d39bbfb29f3e67690baa17095de7) Preparing for AUR

v1.0
  * [[1.1]](https://github.com/hirak99/yabsnap/commit/ef0bff1f1983f73d628b29ce2a9930e48c4c98ef) Split off and renamed
  * [[1.2]](https://github.com/hirak99/yabsnap/commit/fbff635223f91b46f643ed53d1013150a1f207aa) Added install script
  * [[1.3]](https://github.com/hirak99/yabsnap/commit/64f257824ffc9ed988b2c0f12d7b7e4d1cd34e9c) Added README.md
  * [[1.4]](https://github.com/hirak99/yabsnap/commit/f800b36346368c8bc01430b3ba09a0cdd56dfedb) Added an argument to make sure it's not started inadvertently
  * [[1.5]](https://github.com/hirak99/yabsnap/commit/11687b30bfe18ea503bb2875403727863f1e8b7c) Separated main
  * [[1.6]](https://github.com/hirak99/yabsnap/commit/b9acf062491bf63c02a04c00f637342e53c322cf) Moved the services to a directory
  * [[1.7]](https://github.com/hirak99/yabsnap/commit/c8fc2a2ca306033b12c6db1c131da03bcf5d7a4b) Added pacman hook
  * [[1.8]](https://github.com/hirak99/yabsnap/commit/a96489a2a722bd3478fef96d6177d7ab1f7aebc4) Implemented minimum time to keep
  * [[1.9]](https://github.com/hirak99/yabsnap/commit/988d9a8d39aa7ba9894fe735829272a95fcab1fb) Changed minimum time preserved to mid hour to avoid boundary issues
  * [[1.10]](https://github.com/hirak99/yabsnap/commit/061645dbdbb2ff1c6f235cf670108929953a25f6) Encapsulates snapshots in its own class
  * [[1.11]](https://github.com/hirak99/yabsnap/commit/1cea0240f8d108665542a69ac7f98b5bc4cf8268) install.sh to exclude test and other files
  * [[1.12]](https://github.com/hirak99/yabsnap/commit/67ff78197dec9a44723db14bf91b2ac9301c12f4) Moved handling of snap time to snap_holder.Snapshot
  * [[1.13]](https://github.com/hirak99/yabsnap/commit/5055c737cf99c1302d33ce484627614edfee91a3) Use one TIME_FORMAT
  * [[1.14]](https://github.com/hirak99/yabsnap/commit/9c190859e6d95107ee72c504c9cb5b3243e87500) Store and handle metadata
  * [[1.15]](https://github.com/hirak99/yabsnap/commit/06173966ef527b7861227d8c54f9bb91c0c8c664) Added 'list' command
  * [[1.16]](https://github.com/hirak99/yabsnap/commit/5fd0165afbfa4ab94dd46da3f6126552cff24875) Do not proceed with install.sh if not Arch based distro
  * [[1.17]](https://github.com/hirak99/yabsnap/commit/12861f38eaba86e6f611b7f160fdd3e8532a22f5) Changed 'P' to 'I' as installation trigger
  * [[1.18]](https://github.com/hirak99/yabsnap/commit/e69f53778b09daf030da5fb3245acebf1011334c) Only consider scheduled snaps for expiry
  * [[1.19]](https://github.com/hirak99/yabsnap/commit/a040723ec07c0c499744bf463ecf025e0634b69e) Added the 'create' command, and cleanup for create and pacman
  * [[1.20]](https://github.com/hirak99/yabsnap/commit/4a3f74f1137af534ea18f33d70c8facf656c9954) Slightly better list
  * [[1.21]](https://github.com/hirak99/yabsnap/commit/7a098a864c4b9a92dbe356690c17dfcf41c49216) Added command 'delete'
  * [[1.22]](https://github.com/hirak99/yabsnap/commit/f83f0858c8a4ab14bbb76b3a741e30a59737792d) Added --source to be able to restrict to a config
  * [[1.23]](https://github.com/hirak99/yabsnap/commit/17fd60a6eadba9b42d473cf02d25a2d1122af978) Can add --comment for create
  * [[1.24]](https://github.com/hirak99/yabsnap/commit/856a794adac3eae2930c627db52339144163fe59) Prints 'Syncing...' (only if sync is needed)
  * [[1.25]](https://github.com/hirak99/yabsnap/commit/adfd82ff8bf6d5f0c693bc98964b2d538aef6088) Do not --delete-exclude on install.sh (preserves pycache)
  * [[1.26]](https://github.com/hirak99/yabsnap/commit/5b0ed19841f7f13d93fe018b484b29bc16ec12f5) Added code to parse config from configuration files
  * [[1.27]](https://github.com/hirak99/yabsnap/commit/bd63d79f22f7fe4ccd68aa599e2b4547a6f7d4bc) Moved the configs from hardcoded to /etc/yabsnap/configs
  * [[1.28]](https://github.com/hirak99/yabsnap/commit/7fb132b9852bdfc631c72a9850f138a2522a3105) Implemented --dry-run
  * [[1.29]](https://github.com/hirak99/yabsnap/commit/39fee09d4b7ae4618281f0a74bfb386f051368b7) Pre-installation backups append pacman command
  * [[1.30]](https://github.com/hirak99/yabsnap/commit/d81ce3fcf113a288e77662bd3d60bdb798f67f7c) Updated README.md
  * [[1.31]](https://github.com/hirak99/yabsnap/commit/3875184f360780b34c4a72c373630c63611712d2) Create LICENSE
  * [[1.32]](https://github.com/hirak99/yabsnap/commit/fb288795c8e978718c3354bbe33844fafa5c62fd) Hilight that this is for Arch only
  * [[1.33]](https://github.com/hirak99/yabsnap/commit/440b2856c52dc51687d76771141c075374a6b59d) Force sync on delete, since dirty flag is not updated
  * [[1.34]](https://github.com/hirak99/yabsnap/commit/2356984cb7768d27dc9920058bd9409421f7d29c) yabsnap list shows config file names
  * [[1.35]](https://github.com/hirak99/yabsnap/commit/79ee67fe9da6d4e762ac063701f07d9223d1cfa1) Enabled deleting correlated snaps across configs
  * [[1.36]](https://github.com/hirak99/yabsnap/commit/750ca030690c5b13b0c9fb009b1224a208f64844) Renamed utils to os_utils
  * [[1.37]](https://github.com/hirak99/yabsnap/commit/0679211eeea45a4c2bc9f80b86497589fb18ed5d) Added rollback command - it produces a script
  * [[1.38]](https://github.com/hirak99/yabsnap/commit/cccd57be6bcecd607c75cb564bbab35f1f37d73c) Changed option name from rollback to rollback-gen
  * [[1.39]](https://github.com/hirak99/yabsnap/commit/872fcfd0fe9c670fae8e92030e926a022653f799) Minor changes to the rollback script
  * [[1.40]](https://github.com/hirak99/yabsnap/commit/456ba4aa05b0978843c797eec472e4ea3ed82cb0) Updated the README.md with rollback-gen
  * [[1.41]](https://github.com/hirak99/yabsnap/commit/4466aa20b5a37062ce32db7b022d78eee5345535) Small fixes to create-config
  * [[1.42]](https://github.com/hirak99/yabsnap/commit/a8eccd1924ffb6646c98e923fc96c05c760a2f56) Minor logging message change

