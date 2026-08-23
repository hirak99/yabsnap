# Release Summaries

Note: Summaries for versions before v2.2.11 are not included.

## v2.4.2 (2026-08-17)

### **Fixes**

1. **Rollback and TUI Stability**

   * Report failed rollback instead of success (commit: [9dca24c](https://github.com/hirak99/yabsnap/commit/9dca24c)).
   * Fix TUI freeze on failed rollback; show the error detail (commit: [ffe7d70](https://github.com/hirak99/yabsnap/commit/ffe7d70)).

2. **Snapshot Creation**

   * Prevent same-name snapshot collision between concurrent creates (commit: [f9deaa8](https://github.com/hirak99/yabsnap/commit/f9deaa8)).
   * Run post-transaction hooks for TUI create (commit: [f75ff39](https://github.com/hirak99/yabsnap/commit/f75ff39)).

### **Enhancements**

1. **Lock Handling**

   * Cleanup lock files (commit: [d74a0a7](https://github.com/hirak99/yabsnap/commit/d74a0a7)).
   * Skip per-second lock for read-only list commands (commit: [d5362ed](https://github.com/hirak99/yabsnap/commit/d5362ed)).

### **Chore**

1. **Tooling**

   * Migrated formatting/linting from black, isort, and mypy to ruff (commits: [99297d1](https://github.com/hirak99/yabsnap/commit/99297d1), [c5a2f6e](https://github.com/hirak99/yabsnap/commit/c5a2f6e), and related).

## v2.4.1 (2026-06-15)

### **Fixes**

1. **Packaging**

   * Prevent runtime bytecode generation to avoid package conflicts (commit: [637b157](https://github.com/hirak99/yabsnap/commit/637b157)).

## v2.4.0 (2026-06-13)

### **Enhancements**

1. **TUI Polish**

   * Drop the window title bar, bind escape to close modal dialogs, and format timestamps (commits: [cfdb457](https://github.com/hirak99/yabsnap/commit/cfdb457), [ebabe74](https://github.com/hirak99/yabsnap/commit/ebabe74), [c86aef3](https://github.com/hirak99/yabsnap/commit/c86aef3)).
   * Change key for viewing metadata to m (commit: [15e53c7](https://github.com/hirak99/yabsnap/commit/15e53c7)).

### **Documentation**

1. **Minor Updates**

   * Minor docs update (commit: [072c42d](https://github.com/hirak99/yabsnap/commit/072c42d)).

## v2.3.5 (2026-06-08)

### **Enhancements**

1. **TUI (New)**

   * Introduced the TUI (commit: [f891e57](https://github.com/hirak99/yabsnap/commit/f891e57)); delete and rollback flows started as work-in-progress (commit: [e8473e5](https://github.com/hirak99/yabsnap/commit/e8473e5)).
   * Press t to open a terminal in the TUI (commit: [d3ac1db](https://github.com/hirak99/yabsnap/commit/d3ac1db)).
   * View snapshot metadata in the TUI (commit: [47c0015](https://github.com/hirak99/yabsnap/commit/47c0015)).
   * Optional key overlay for demo; debounced and supports multiple keys within a second (commits: [70c2259](https://github.com/hirak99/yabsnap/commit/70c2259), [b75942b](https://github.com/hirak99/yabsnap/commit/b75942b), [f6d829b](https://github.com/hirak99/yabsnap/commit/f6d829b), [0790ff0](https://github.com/hirak99/yabsnap/commit/0790ff0)).

2. **TUI as Optional Dependency**

   * Made TUI optional; textual added as a workflow dependency (commits: [2a2a0f4](https://github.com/hirak99/yabsnap/commit/2a2a0f4), [08bbc1c](https://github.com/hirak99/yabsnap/commit/08bbc1c)).

### **Refactoring**

1. **Code Hygiene**

   * Rename app.py to tui_app.py (commit: [759b2f3](https://github.com/hirak99/yabsnap/commit/759b2f3)).
   * Replace os.system() with subprocess.run() (commit: [522adc3](https://github.com/hirak99/yabsnap/commit/522adc3)).
   * Add isort to workflow and tests; reformat for isort and updated black checks (commits: [82812f0](https://github.com/hirak99/yabsnap/commit/82812f0), [4e401ea](https://github.com/hirak99/yabsnap/commit/4e401ea), [0fd098b](https://github.com/hirak99/yabsnap/commit/0fd098b), [47df72e](https://github.com/hirak99/yabsnap/commit/47df72e), [763115e](https://github.com/hirak99/yabsnap/commit/763115e)).

### **Documentation**

1. **README**

   * Added TUI updates and demo; fixed alert sections; small readability fixes (commits: [d3e3e8c](https://github.com/hirak99/yabsnap/commit/d3e3e8c), [391622c](https://github.com/hirak99/yabsnap/commit/391622c), [ead3d0a](https://github.com/hirak99/yabsnap/commit/ead3d0a), [ec1add6](https://github.com/hirak99/yabsnap/commit/ec1add6)).

### **External Contributions**

* **ShalokShalom** contributed to fixing typos and improving readability in README.md (commits: [ec1add6](https://github.com/hirak99/yabsnap/commit/ec1add6), [42580cd](https://github.com/hirak99/yabsnap/commit/42580cd)).

## v2.3.4 (2025-11-10)

### **Fixes**

1. **mtab Parsing**

   * Switch to findmnt --mtab -J (commit: [8acf988](https://github.com/hirak99/yabsnap/commit/8acf988)).

### **Chore**

1. **Performance**

   * Added caching in mtab parser (commit: [5f48454](https://github.com/hirak99/yabsnap/commit/5f48454)).

## v2.3.3 (2025-11-08)

### **Enhancements**

1. **Implemented Shell Completions**

   * Added zsh completions (commits: [94ecb0c](https://github.com/hirak99/yabsnap/commit/94ecb0c), [5541489](https://github.com/hirak99/yabsnap/commit/5541489), [650a9e1](https://github.com/hirak99/yabsnap/commit/650a9e1), [6c925b9](https://github.com/hirak99/yabsnap/commit/6c925b9), [5541489](https://github.com/hirak99/yabsnap/commit/5541489), [1b7c2a4](https://github.com/hirak99/yabsnap/commit/1b7c2a4)).
   * Integrated richer completions for zsh (commits: [ba850cc](https://github.com/hirak99/yabsnap/commit/ba850cc), [5541489](https://github.com/hirak99/yabsnap/commit/5541489)).
   * Introduced bash autocompletion (commits: [ad82003](https://github.com/hirak99/yabsnap/commit/ad82003), [94ecb0c](https://github.com/hirak99/yabsnap/commit/94ecb0c)).
   * Added ability to offer completions for target_suffix (commit: [c5f0792](https://github.com/hirak99/yabsnap/commit/c5f0792)).
   * Improved completion logic by moving to Python for better abstraction from shell-dependent implementations (commits: [5f50dda](https://github.com/hirak99/yabsnap/commit/5f50dda), [86c5104](https://github.com/hirak99/yabsnap/commit/86c5104)).

### **Documentation**

1. **Help Text and Clarity**

   * Reworded help text for many args to improve clarity (commit: [c3515b5](https://github.com/hirak99/yabsnap/commit/c3515b5)).

### **Refactoring**

1. **General Refactoring and Cleanup**

   * Refactored completion logic for better readability and functionality (commits: [ea6b3e9](https://github.com/hirak99/yabsnap/commit/ea6b3e9), [dab1ded](https://github.com/hirak99/yabsnap/commit/dab1ded), [96819ba](https://github.com/hirak99/yabsnap/commit/96819ba), [3f7c751](https://github.com/hirak99/yabsnap/commit/3f7c751)).
   * Removed dependency of `batch_deleter` from `arg_parser` (commit: [a3ea6bd](https://github.com/hirak99/yabsnap/commit/a3ea6bd)).
   * Split `arg_parser` into separate components for better maintainability (commit: [5a224a2](https://github.com/hirak99/yabsnap/commit/5a224a2)).
   * Completions are no longer a class, simplifying the structure (commit: [1b7c2a4](https://github.com/hirak99/yabsnap/commit/1b7c2a4)).
   * Refactored batch deleter to simplify parsing of snapshot timestamps (commit: [c96f588](https://github.com/hirak99/yabsnap/commit/c96f588)).

### **Chore**

1. **Minor Edits and Bug Fixes**

   * Various minor changes to install scripts and completion handling (commits: [e81e0c9](https://github.com/hirak99/yabsnap/commit/e81e0c9), [3ada32f](https://github.com/hirak99/yabsnap/commit/3ada32f), [95f8727](https://github.com/hirak99/yabsnap/commit/95f8727), [32d3b3b](https://github.com/hirak99/yabsnap/commit/32d3b3b)).
   * Updated direct install and uninstall scripts (commit: [3ada32f](https://github.com/hirak99/yabsnap/commit/3ada32f)).
   * Fixed issues with unittest discovery and circular reference in tests (commits: [c9ba0c1](https://github.com/hirak99/yabsnap/commit/c9ba0c1), [82689de](https://github.com/hirak99/yabsnap/commit/82689de)).

2. **Improvement to Completion Logic**

   * Improved handling after positional arguments (commits: [3295d96](https://github.com/hirak99/yabsnap/commit/3295d96), [55c3730](https://github.com/hirak99/yabsnap/commit/55c3730)).
   * Added environment flag for debugging shell completions (commit: [7575bcf](https://github.com/hirak99/yabsnap/commit/7575bcf)).
   * Dropped `-h` option from completion as `--help` exists (commit: [dd7ab56](https://github.com/hirak99/yabsnap/commit/dd7ab56)).

### **Fixes**

1. **Bug Fixes and Test Improvements**

   * Fixed issues in completions related to using `cd` and `pushd` in zsh (commit: [e3f4a4d](https://github.com/hirak99/yabsnap/commit/e3f4a4d)).
   * Fixed test issues related to shell completion logic (commit: [82689de](https://github.com/hirak99/yabsnap/commit/82689de)).

### **External Contributions**

* **thR CIrcU5** contributed to fixing type issues and updating unit tests for batch deleter (commits: [1e9b3eb](https://github.com/hirak99/yabsnap/commit/1e9b3eb), [8786623](https://github.com/hirak99/yabsnap/commit/8786623), [c96f588](https://github.com/hirak99/yabsnap/commit/c96f588)).
   * Completed batch deleter todo (commit: [0d242f0](https://github.com/hirak99/yabsnap/commit/0d242f0)).
   * Updated unit tests for batch deleter (commit: [8786623](https://github.com/hirak99/yabsnap/commit/8786623)).

## v2.3.2 (2025-11-04)

### **Fixes and Enhancements**

1. **Rollback and Nested Subvolumes**

   * Fix for best effort rollback of nested subvolume snapshots (commits: [d5aaf12](https://github.com/hirak99/yabsnap/commit/d5aaf12)).
   * Fix for handling nested subvolumes correctly in `mtab` (commits: [e7357aa](https://github.com/hirak99/yabsnap/commit/e7357aa)).

2. **Logging and Error Handling**

   * Logs and warnings now show code and line number (commits: [07353bb](https://github.com/hirak99/yabsnap/commit/07353bb)).
   * Added a message to `mtab` ValueError for better debugging (commits: [75daaa5](https://github.com/hirak99/yabsnap/commit/75daaa5)).

3. **Device UUID and Locale**

   * Fix for taking locale changes into account in device UUID, addressing issue #70 (commits: [a1b940f](https://github.com/hirak99/yabsnap/commit/a1b940f)).

4. **Miscellaneous Fixes and Refactoring**

   * Chore: Ignore unknown fields in configuration (commits: [0513be2](https://github.com/hirak99/yabsnap/commit/0513be2)).
   * Documentation update to specify that `list-json` outputs in JSONL format (commits: [aaf3be6](https://github.com/hirak99/yabsnap/commit/aaf3be6)).

## v2.3.1 also v2.2.12 (2025-11-03)

Rollback to address bugs #69 and #70. The base is v2.2.11.

### **Chore**

1. **Snapshot Handling Enhancements**

   * Ignore unknown snapshot fields to facilitate rollback of version 2.3.0 without snapshot loading errors (commits: [d747523](https://github.com/hirak99/yabsnap/commit/d747523)).

## v2.3.0 (2025-11-01)

### **Enhancements**

1. **Rollback Enhancements**

   * Automatic offline rollback introduced (commit: [c3caec1](https://github.com/hirak99/yabsnap/commit/c3caec1)).
   * Warning added if UUID does not match during rollback (commit: [d749202](https://github.com/hirak99/yabsnap/commit/d749202)).
   * Reworked nested subvolume detection (commit: [e14b267](https://github.com/hirak99/yabsnap/commit/e14b267)).
   * Added BTRFS subvolume to snapshot metadata (commit: [7e34bd3](https://github.com/hirak99/yabsnap/commit/7e34bd3)).
   * Refined handling of rollback pass list (commits: [96307cf](https://github.com/hirak99/yabsnap/commit/96307cf), [d7ddf50](https://github.com/hirak99/yabsnap/commit/d7ddf50)).

2. **Snap Metadata Updates**

   * Added `version` field to snapshot metadata (commit: [0925be1](https://github.com/hirak99/yabsnap/commit/0925be1)).
   * Introduced `source_uuid` to be checked during rollback (commit: [2b6e9ab](https://github.com/hirak99/yabsnap/commit/2b6e9ab)).

3. **General Improvements**

   * Introduced `dataclass_loader`, a lightweight replacement for Pydantic (commit: [cc9a3fc](https://github.com/hirak99/yabsnap/commit/cc9a3fc)).
   * Updated error handling and improved warning messages (commits: [67b9a33](https://github.com/hirak99/yabsnap/commit/67b9a33), [eb236c2](https://github.com/hirak99/yabsnap/commit/eb236c2)).
   * Enhanced FAQ section and updated documentation (commits: [9527374](https://github.com/hirak99/yabsnap/commit/9527374), [8c8a8dd](https://github.com/hirak99/yabsnap/commit/8c8a8dd)).

### **Refactoring**

1. **Code Refactor for Clarity and Performance**

   * Split function `runsh_or_error()` and `runsh()` for better error handling (commit: [3830d74](https://github.com/hirak99/yabsnap/commit/3830d74)).
   * Moved `SnapType` enum to a separate module to avoid circular dependencies (commit: [ea486f1](https://github.com/hirak99/yabsnap/commit/ea486f1)).
   * Reorganized snapshot-related logic into one directory (commit: [52a36e7](https://github.com/hirak99/yabsnap/commit/52a36e7)).
   * Consolidated utility functions into a single directory (commit: [c8bb6bd](https://github.com/hirak99/yabsnap/commit/c8bb6bd)).

2. **Miscellaneous Code Refinements**

   * Renamed `common_fs_utils` to `mtab_parser` for clarity (commit: [798f27d](https://github.com/hirak99/yabsnap/commit/798f27d)).
   * Refined `dataclass_loader` implementation (commit: [c4b6d39](https://github.com/hirak99/yabsnap/commit/c4b6d39)).
   * Removed stray comments and improved function names for readability (commits: [b9be207](https://github.com/hirak99/yabsnap/commit/b9be207), [84b7c5c](https://github.com/hirak99/yabsnap/commit/84b7c5c)).

### **Chores**

1. **Metadata and Snap Management**

   * Improved handling of snapshot metadata and error messages (commits: [b30302b](https://github.com/hirak99/yabsnap/commit/b30302b), [31c19ed](https://github.com/hirak99/yabsnap/commit/31c19ed)).
   * Updated license and FAQ section (commit: [6e00929](https://github.com/hirak99/yabsnap/commit/6e00929)).

### **Documentation**

1. **Updated Documentation**

   * Revised and expanded FAQ section (commits: [9527374](https://github.com/hirak99/yabsnap/commit/9527374), [8c8a8dd](https://github.com/hirak99/yabsnap/commit/8c8a8dd)).
   * Updated README and manpage for `subvol-map` (commit: [b30302b](https://github.com/hirak99/yabsnap/commit/b30302b)).

## v2.2.11 (2025-10-30)

### **Enhancements**

1. **Rollback Feature Improvements**

   * Added `--live-subvol-map` option to the rollback-gen and rollback commands (commits: [d3260fc](https://github.com/hirak99/yabsnap/commit/d3260fc), [0a0ded2](https://github.com/hirak99/yabsnap/commit/0a0ded2), [79f0ca8](https://github.com/hirak99/yabsnap/commit/79f0ca8)).
   * Refactored subvolume map implementation and merged rollback-gen-offline into `rollback-gen` (commit: [79f0ca8](https://github.com/hirak99/yabsnap/commit/79f0ca8)).
   * Improved documentation for the `--live-subvol-map` option, including new rewording and examples (commits: [d60adda](https://github.com/hirak99/yabsnap/commit/d60adda), [8d4bc27](https://github.com/hirak99/yabsnap/commit/8d4bc27)).

2. **Grub-Btrfs Support**

   * Added compatibility with grub-btrfs (commit: [df27928](https://github.com/hirak99/yabsnap/commit/df27928)).

### **Documentation**

1. **README Updates**

   * Fixed typos and updated example commands (commits: [e85b4be](https://github.com/hirak99/yabsnap/commit/e85b4be), [19e6791](https://github.com/hirak99/yabsnap/commit/19e6791)).
2. **Rollback Documentation**

   * Improved documentation for the `--live-subvol-map` option (commit: [d60adda](https://github.com/hirak99/yabsnap/commit/d60adda)).