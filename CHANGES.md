# Changes Documentation

## Reference: llama.cpp commit 4d5ae24c0ac79c4e360773bac58dd2c2a46b7f67

### Summary
Fix for `common_params_parse` not accepting negated arguments.

### Changes Applied
This commit addresses an issue where negated command-line arguments (e.g., `--no-mmap`) were not properly recognized by the argument parser.

### Key Modifications

1. **Function Renaming** (`common/arg.cpp` and `common/arg.h`):
   - Renamed `common_params_parse` to `common_params_to_map` for the map-returning overload
   - This clarifies the function's purpose of converting parameters to a map

2. **Negated Arguments Support** (`common/arg.cpp`):
   - Added support for `args_neg` in the argument-to-options mapping
   - Now iterates over both `opt.args` and `opt.args_neg` when building the argument map
   
   ```cpp
   for (const auto & arg : opt.args_neg) {
       arg_to_options[arg] = &opt;
   }
   ```

3. **Test Coverage** (`tests/test-arg-parser.cpp`):
   - Added test case for negated arguments
   - Tests that `--no-mmap` is properly parsed with `LLAMA_EXAMPLE_COMMON`

4. **Usage Update** (`tools/server/server-models.cpp`):
   - Updated function call from `common_params_parse` to `common_params_to_map`

### Impact
This fix ensures that command-line tools properly recognize and handle negated boolean flags, improving the robustness of the argument parsing system.

### Related Issue
PR #17991 in ggml-org/llama.cpp repository.

---

**Note**: This documentation is maintained in this `.github` repository for reference purposes. The actual implementation exists in the llama.cpp project.
