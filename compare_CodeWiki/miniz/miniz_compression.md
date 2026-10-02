# miniz_compression Module Documentation

## Introduction

The `miniz_compression` module provides zlib-compatible compression APIs (`deflate`) for the `miniz` library. It bridges standard zlib stream management and buffer operations with underlying low-level compression primitives (`tdefl`), enabling memory-efficient block and stream compression.

---

## Architecture and Components

The module revolves around zlib-compatible stream structures and state management functions defined in `miniz.c`.

### Core Components

- **`mz_internal_state` / `tdefl_compressor`**: Internal representation of the compression state.
- **Initialization APIs**:
  - `mz_deflateInit`: Initializes a compression stream using default parameters.
  - `mz_deflateInit2`: Initializes a compression stream with custom level, method, window bits, memory level, and strategy.
- **Execution & Control APIs**:
  - `mz_deflate`: Compresses input data from the stream buffer with a specified flush type.
  - `mz_deflateReset`: Resets an active stream state for reuse without re-allocation.
  - `mz_deflateEnd`: Frees stream state resources and cleans up memory.
- **Helper & Utility APIs**:
  - `mz_deflateBound`: Estimates the upper bound of compressed data size for a given source length.
  - `mz_compress` / `mz_compress2`: Convenience wrappers for one-shot buffer compression.
  - `mz_compressBound`: Wrapper around `mz_deflateBound` for buffer sizing.

---

## System Integration & Data Flow

`miniz_compression` interacts directly with memory utilities (see [miniz_utilities](miniz_utilities.md)) and acts as the counterpart to the [miniz_decompression](miniz_decompression.md) module.

### Component Interaction Diagram

```mermaid
graph TD
    UserApp[Application / Caller] -->|Calls mz_deflateInit / mz_deflateInit2| DeflateInit[mz_deflateInit2]
    DeflateInit -->|Allocates via zalloc| State[mz_internal_state / tdefl_compressor]
    
    UserApp -->|Supplies input buffers| Deflate[mz_deflate]
    Deflate -->|Compresses chunks via tdefl| State
    Deflate -->|Updates adler32 & totals| Stream[mz_stream]
    
    UserApp -->|Calls mz_deflateEnd| DeflateEnd[mz_deflateEnd]
    DeflateEnd -->|Frees via zfree| State
    
    subgraph Utilities & Decompression
        DeflateInit -.->|Uses memory allocators| Utils[miniz_utilities]
        UserApp -.->|Counterpart module| Decomp[miniz_decompression]
    end
```

### Compression Process Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Stream as mz_stream
    participant Comp as miniz_compression (mz_deflate)
    participant Core as tdefl engine

    App->>Stream: Initialize (mz_deflateInit / mz_deflateInit2)
    Stream->>Comp: Allocate & init tdefl_compressor state
    Comp-->>App: MZ_OK
    
    loop While data remains or flush requested
        App->>Stream: Set next_in, avail_in, next_out, avail_out
        App->>Comp: mz_deflate(stream, flush)
        Comp->>Core: tdefl_compress(...)
        Core-->>Comp: Status & byte counts
        Comp->>Stream: Update total_in, total_out, adler, avail_*
        Comp-->>App: MZ_OK / MZ_STREAM_END / MZ_BUF_ERROR
    end
    
    App->>Comp: mz_deflateEnd(stream)
    Comp->>Stream: Free state memory via zfree
    Comp-->>App: MZ_OK
```

---

## See Also

- [miniz_decompression](miniz_decompression.md)
- [miniz_utilities](miniz_utilities.md)
