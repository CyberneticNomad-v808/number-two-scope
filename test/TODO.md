# SpiderFoot test/run Script - TODO

## Plan (Approved 2025-10-26)

### Problem
Current test/run script is incomplete - missing most of the BLKC framework (340 lines missing). Logging functions incomplete, missing config system features, and has improper shellcheck disables.

### Solution
Properly implement using the universal-script-template.sh as the base, following demo-script.sh as the example.

### Steps
1. **Replace current broken implementation** with proper template copy
2. **Customize for SpiderFoot test runner:**
   - Update header/description/usage
   - Add PROJECT_ROOT variable (points to SpiderFoot root)
   - Set BLKC_COMPONENT="spiderfoot-test-runner"
   - Add validate_working_directory() and validate_dependencies() functions
   - Replace start/stop/status functions with:
     - run_standard_tests() - excludes module tests
     - run_all_tests() - includes everything
     - run_module_tests() - only module tests
   - Remove embedded file extraction functions (not needed)
   - Update help text and command dispatcher
3. **Validate with shellcheck** (should pass cleanly - color variable warnings are acceptable framework variables)
4. **Initialize BLKC config system:**
   - Run setup-blkc-config.sh
   - Create ~/.blkc/run.config with test-specific settings

This follows the exact pattern from demo-script.sh which is 535 lines and properly implements the full BLKC framework.

---

## Completed
- [x] Read demo-script.sh to understand proper BLKC implementation
- [x] Copy universal-script-template.sh to /stuff/spiderfoot/test/run
- [x] Customize header for SpiderFoot test runner (lines 1-40)
- [x] Add PROJECT_ROOT variable after SCRIPT_VERSION
- [x] Set BLKC_COMPONENT to 'spiderfoot-test-runner'
- [x] Add validation functions: validate_working_directory, validate_dependencies
- [x] Replace service functions with test functions: run_standard_tests, run_all_tests, run_module_tests
- [x] Remove embedded file extraction functions
- [x] Update show_help with test runner commands and examples
- [x] Update dispatch_command with test/all/modules commands
- [x] Update main() to call validate_working_directory and validate_dependencies
- [x] Fix shellcheck SC2155 warning for PROJECT_ROOT
- [x] Run shellcheck to validate the script

## Pending
- [ ] Make script executable
- [ ] Run setup-blkc-config.sh to initialize config system
- [ ] Create ~/.blkc/run.config with script-specific settings
- [ ] Test script execution
