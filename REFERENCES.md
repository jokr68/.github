# Technical References

This document tracks important technical references and commits from related projects.

## llama.cpp - SOLVE_TRI Extension

**Commit:** [53ecd4fdb923dcb53d311ed42798cae7198aa742](https://github.com/ggml-org/llama.cpp/commit/53ecd4fdb923dcb53d311ed42798cae7198aa742)

**Summary:** Extended SOLVE_TRI operation to support more dimensions

### Key Changes

1. **Extended Matrix Size Support**
   - Previous implementation was limited to n ≤ 64, k ≤ 32 (where n is the triangular matrix dimension and k is the number of right-hand side vectors)
   - New implementation supports arbitrary dimensions using cuBLAS

2. **Dual Implementation Strategy**
   - Fast kernel path: For small matrices (n ≤ 64, k ≤ 32) using warp-based parallel reduction
   - cuBLAS path: For larger matrices using `cublasStrsmBatched`

3. **Multi-Vendor Support**
   - Added HIP (AMD) support with appropriate macro definitions
   - Added MUSA support with corresponding definitions
   - Maintains compatibility across CUDA, HIP, and MUSA platforms

4. **Testing**
   - Added extensive test cases covering various matrix sizes
   - Tests include edge cases and larger dimensions (up to 256×256)
   - Comprehensive batch testing with different configurations

### Technical Details

The implementation uses:
- `cublasStrsmBatched` for solving triangular systems in batches
- Math mode switching between `CUBLAS_DEFAULT_MATH` and `CUBLAS_TF32_TENSOR_OP_MATH` to ensure numerical accuracy while maintaining performance
- Proper handling of strides and batching across multiple dimensions (ne02, ne03) for efficient memory access patterns

### Files Modified
- `ggml/src/ggml-cuda/ggml-cuda.cu`
- `ggml/src/ggml-cuda/solve_tri.cu`
- `ggml/src/ggml-cuda/vendors/hip.h`
- `ggml/src/ggml-cuda/vendors/musa.h`
- `tests/test-backend-ops.cpp`

### Significance

This change enables llama.cpp to handle larger attention mechanisms and more complex linear algebra operations efficiently, which is crucial for scaling transformer models and handling larger chunk sizes in models like Qwen3Next.
