# cJSON Core Types Module Documentation

## Introduction

The `cJSON_core_types` module forms the foundational data structures and core utility mechanisms for the `cJSON` library. It defines the primary `cJSON` struct (representing JSON objects, arrays, strings, numbers, booleans, and null values), memory allocation hooks (`internal_hooks`), parsing buffers (`parse_buffer`), error tracking structures (`error`), and fundamental helper functions for managing object lifecycles, versioning, and basic type checks.

---

## Architecture & Core Components

The module encompasses the core definitions used across all other sub-modules (`cJSON_parsing`, `cJSON_printing`, and `cJSON_manipulation`). Below is the architectural relationship and data flow between these core structures:

```mermaid
graph TD
    subgraph cJSON_core_types
        direction TB
        cJSON["cJSON Struct<br/><i>JSON Value Node</i>"] --> internal_hooks["internal_hooks<br/><i>Memory Management Hooks</i>"]
        parse_buffer["parse_buffer<br/><i>Parsing State & Buffer</i>"] --> internal_hooks
        error["error<br/><i>Global Error Tracking</i>"]
    end

    subgraph Related Modules
        cJSON_parsing["cJSON_parsing<br/><i>[cJSON_parsing.md]</i>"] -->|Uses| cJSON
        cJSON_parsing -->|Uses| parse_buffer
        cJSON_parsing -->|Updates| error
        
        cJSON_printing["cJSON_printing<br/><i>[cJSON_printing.md]</i>"] -->|Uses| cJSON
        
        cJSON_manipulation["cJSON_manipulation<br/><i>[cJSON_manipulation.md]</i>"] -->|Uses & Modifies| cJSON
    end

    style cJSON fill:#f9f,stroke:#333,stroke-width:2px
    style internal_hooks fill:#bbf,stroke:#333,stroke-width:1px
    style parse_buffer fill:#bbf,stroke:#333,stroke-width:1px
    style error fill:#bbf,stroke:#333,stroke-width:1px
```

---

## Component Details

### 1. `cJSON` Struct (Core Data Representation)
The `cJSON` structure represents a node in the JSON document tree. It can act as a primitive value, a string, an array, or an object.

- **Pointers**: `next` and `prev` form a doubly linked list for sibling elements (e.g., inside an object or array). `child` points to the head of a linked list if the node is an array or object.
- **Type Flags**: `type` bitfield indicates the data type (`cJSON_False`, `cJSON_True`, `cJSON_NULL`, `cJSON_Number`, `cJSON_String`, `cJSON_Array`, `cJSON_Object`, etc.) and memory ownership flags (`cJSON_IsReference`, `cJSON_StringIsConst`).
- **Values**: Stores string values (`valuestring`), integer values (`valueint`), and floating-point values (`valuedouble`).
- **Key**: `string` stores the key name if the item is a child of a JSON Object.

### 2. Memory Hooks (`internal_hooks`)
Defines function pointers for memory allocation, deallocation, and reallocation:
```c
typedef struct internal_hooks
{
    void *(CJSON_CDECL *allocate)(size_t size);
    void (CJSON_CDECL *deallocate)(void *pointer);
    void *(CJSON_CDECL *reallocate)(void *pointer, size_t size);
} internal_hooks;
```
Initialized via `cJSON_InitHooks` to allow users to plug in custom memory allocators.

### 3. Parsing Buffer (`parse_buffer`)
Tracks the state of input parsing across buffer offsets, string lengths, nesting depth, and associated hooks:
```c
typedef struct
{
    const unsigned char *content;
    size_t length;
    size_t offset;
    size_t depth;
    internal_hooks hooks;
} parse_buffer;
```

### 4. Error Tracking (`error`)
Records parsing errors with pointer locations:
```c
typedef struct {
    const unsigned char *json;
    size_t position;
} error;
```
Exposed to public API users via `cJSON_GetErrorPtr()`.

---

## Component Interaction & Process Flow

### Lifecycle & Deletion Flow (`cJSON_Delete`)
When a JSON tree is destroyed, `cJSON_Delete` traverses the linked list and hierarchy recursively, respecting reference and constancy flags before releasing memory through the configured deallocation hooks.

```mermaid
sequenceDiagram
    participant User
    participant cJSON_Delete
    participant InternalHooks as internal_hooks.deallocate

    User->>cJSON_Delete: cJSON_Delete(item)
    loop For each item in linked list
        alt item has child and not reference
            cJSON_Delete->>cJSON_Delete: Recursive call on item->child
        end
        alt valuestring != NULL and not reference
            cJSON_Delete->>InternalHooks: deallocate(item->valuestring)
        end
        alt string != NULL and not const
            cJSON_Delete->>InternalHooks: deallocate(item->string)
        end
        cJSON_Delete->>InternalHooks: deallocate(item)
    end
    InternalHooks-->>User: Memory freed
```

---

## Related Modules

- **Parsing**: Refer to [cJSON_parsing.md](cJSON_parsing.md) for details on how `parse_buffer` and input strings are tokenized into `cJSON` structures.
- **Printing**: Refer to [cJSON_printing.md](cJSON_printing.md) for how `cJSON` trees are serialized back into JSON string representations.
- **Manipulation**: Refer to [cJSON_manipulation.md](cJSON_manipulation.md) for adding, removing, replacing, and querying elements within `cJSON` trees.
