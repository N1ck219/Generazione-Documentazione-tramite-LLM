# TinyXML-2 Memory and Utility Module (`TinyXML-2_memory_utils`)

## Introduction

The **TinyXML-2 Memory and Utility Module** provides foundational low-level services, memory management abstractions, dynamic data structures, string management wrappers, and XML utility functions essential for the entire TinyXML-2 library. 

This module underpins the DOM classes defined in [TinyXML-2_dom](TinyXML-2_dom.md) and the visitor/serialization features in [TinyXML-2_visitor](TinyXML-2_visitor.md) by eliminating expensive standard heap allocations for small, frequent node creations and providing robust text normalization, entity encoding/decoding, and numeric conversion routines.

---

## Core Components

The module comprises several key helper classes, templates, and structs:

1. **`MemPool`** (Abstract Base Class)
   - Defines the virtual interface for fast object allocation and deallocation (`Alloc()`, `Free()`, `ItemSize()`, `SetTracked()`).
2. **`MemPoolT<ITEM_SIZE>`** (Template Class)
   - Implements block-based memory pooling for fixed-size objects (such as `XMLElement`, `XMLAttribute`, `XMLText`, and `XMLComment`). Pre-allocates blocks containing multiple items to significantly reduce fragmentation and overhead.
3. **`DynArray<T, INITIAL_SIZE>`** (Template Class)
   - A lightweight dynamic array of Plain Old Data (POD) types with a small initial stack-allocated memory pool (`_pool`) to prevent dynamic allocation during low-capacity usage.
4. **`Block`** (Internal Structure)
   - Represents a contiguous memory chunk managed by `MemPoolT`, holding a fixed number of allocation items.
5. **`StrPair`** (Class)
   - Wraps and manages string pointers (often pointing directly into the source XML file itself) while supporting lazy evaluation of newline normalization, whitespace collapsing, and XML entity processing.
6. **`XMLUtil`** (Utility Class)
   - Provides static helper methods for whitespace handling, character reference resolution, UTF-8/UTF-32 conversions, and safe string-to-primitive/primitive-to-string conversions.
7. **`Entity`** (Internal Struct)
   - Represents standard XML entity mapping pairs (e.g., `&quot;`, `&amp;`, `&apos;`, `&lt;`, `&gt;`).

---

## Architecture and Component Relationships

The memory management and utility components support the higher-level DOM and visitor modules as illustrated below:

```mermaid
graph TD
    subgraph TinyXML-2_memory_utils
        MemPool --> MemPoolT
        MemPoolT --> Block
        DynArray --> MemPoolT
        DynArray --> XMLPrinter
        StrPair --> XMLNode
        StrPair --> XMLAttribute
        XMLUtil --> StrPair
        XMLUtil --> XMLAttribute
        XMLUtil --> XMLElement
    end

    subgraph TinyXML-2_dom
        XMLDocument -->|Uses memory pools| MemPoolT
        XMLNode -->|Uses| StrPair
        XMLAttribute -->|Uses| StrPair
        XMLElement -->|Uses| MemPool
    end

    subgraph TinyXML-2_visitor
        XMLPrinter -->|Uses buffer| DynArray
    end
{class: "dark"}
```

---

## Component Details

### 1. Memory Pools (`MemPool` & `MemPoolT`)
TinyXML-2 avoids calling global `new` and `delete` for every individual node or attribute. Instead, `XMLDocument` instantiates specialized `MemPoolT` pools tailored to the exact sizes of `XMLElement`, `XMLAttribute`, `XMLText`, and `XMLComment`.

* **Block Allocation**: Each block pre-allocates space for multiple items (`ITEMS_PER_BLOCK = 4096 / ITEM_SIZE`).
* **Free List**: Unused items form a singly-linked list via a union overlay (`Item`), allowing $O(1)$ allocation and deallocation.

```mermaid
sequenceDiagram
    participant Doc as XMLDocument
    participant Pool as MemPoolT<sizeof(XMLElement)>
    participant Block as Block

    Doc->>Pool: Alloc()
    alt _root is null
        Pool->>Block: new Block
        Note over Pool,Block: Link items into free list (_root)
    end
    Pool->>Doc: Return _root item (casted to XMLElement*)
    Note over Doc: Node used in DOM

    Doc->>Pool: Free(node)
    Note over Pool: Prepend node back to _root free list
{class: "dark"}
```

### 2. Dynamic Array (`DynArray`)
`DynArray<T, INITIAL_SIZE>` provides a fast vector-like container for POD types. 
* It uses an internal fixed-size array `_pool[INITIAL_SIZE]` to avoid heap allocations when size remains small (e.g., tracking child nodes, printing stacks, or unlinked node lists).
* Automatically scales by doubling capacity when limits are exceeded.

### 3. String Pair (`StrPair`)
`StrPair` optimizes string storage by pointing directly into the raw loaded XML character buffer (`_start` and `_end`), avoiding string duplication during parsing. When requested via `GetStr()`, it lazily processes:
* **Newline Normalization**: Converts `CR`, `CR-LF`, or `LF-CR` sequences to standard `LF` (`\n`).
* **Entity Decoding**: Resolves standard entity references (`&amp;`, `&lt;`, `&gt;`, `&apos;`, `&quot;`) and numeric character references (`&#20013;`, `&#x4e2d;`).
* **Whitespace Collapsing**: Trims leading/trailing whitespace and compresses internal whitespace runs when requested.

---

## Data Flow & Parsing Utilities (`XMLUtil`)

During parsing and serialization, `XMLUtil` provides robust transformation and checking routines:

```mermaid
flowchart LR
    Raw[Raw XML Buffer] --> Skip[XMLUtil::SkipWhiteSpace]
    Skip --> CheckBOM[XMLUtil::ReadBOM]
    CheckBOM --> Ident[XMLDocument::Identify]
    Ident --> ParseNode[ParseDeep / StrPair]
    ParseNode --> Conv[XMLUtil::ToInt / ToDouble / ToStr]
{class: "dark"}
```

---

## Dependencies on Other Modules

- **Consumed by**: 
  - [TinyXML-2_dom](TinyXML-2_dom.md) relies heavily on `MemPoolT` for node/attribute allocation, `StrPair` for node naming/values, and `XMLUtil` for parsing attributes and text.
  - [TinyXML-2_visitor](TinyXML-2_visitor.md) uses `DynArray` for tracking output nesting depth and buffering serialized output in memory mode.
