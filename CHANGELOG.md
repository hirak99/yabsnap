# Release Summaries

Note: The summaries below are curated using a language model on git log. Summaries for
versions before v2.2.11 are not included.

## v2.3.3 (Nov 08, 2025)

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

## v2.3.2 (Nov 04, 2025)

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

## v2.3.1 also v2.2.12 (Nov 03, 2025)

Rollback to address bugs #69 and #70. The base is v2.2.11.

### **Chore**

1. **Snapshot Handling Enhancements**

   * Ignore unknown snapshot fields to facilitate rollback of version 2.3.0 without snapshot loading errors (commits: [d747523](https://github.com/hirak99/yabsnap/commit/d747523)).

## v2.3.0 (Nov 01, 2025)

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

## v2.2.11 (Oct 30, 2025)

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