# cJSON Printing Module Documentation

## Introduction

The `cJSON_printing` module is responsible for serializing `cJSON` data structures back into valid JSON string representations. It provides robust mechanisms for both formatted (pretty-printed with indentation and newlines) and unformatted (compact) JSON output, as well as buffer management during the printing process.

---

## Architecture & Core Components

The printing module operates on the foundational data structures defined in the [cJSON_core_types.md](cJSON_core_types.md) module, taking a `cJSON` tree root and transforming it into a dynamically allocated string buffer (`printbuffer`).

```mermaid
graph TD
    subgraph cJSON_printing
        direction TB
        printbuffer["printbuffer<br/><i>Buffer State & Allocation Management</i>"] --> print_value["print_value<br/><i>Dispatcher for JSON Types</i>"]
        print_value --> print_string["print_string / ensure"]
        print_value --> print_number["print_number"]
        print_value --> print_array["print_array"]
        print_value --> print_object["print_object"]
    end

    subgraph Dependencies
        cJSON_core_types["cJSON_core_types<br/><i>[cJSON_core_types.md]</i>"] -->|Provides cJSON struct & hooks| cJSON_printing
    end

    style printbuffer fill:#f9f,stroke:#333,stroke-width:2px
    style print_value fill:#bbf,stroke:#333,stroke-width:1px
```

---

## Component Details

### 1. Print Buffer (`printbuffer`)
The printing routines use an internal `printbuffer` structure to manage memory allocation, buffer growth, current write position, and formatting options (formatted vs. unformatted printing):
- **Buffer Management**: Automatically reallocates memory using custom memory hooks (`internal_hooks`) when the buffer capacity is exceeded.
- **Buffer Growth Strategy**: Employs exponential or incremental growth algorithms (`ensure`) to minimize reallocation overhead.
- **Formatting Flags**: Tracks indentation depth and whether spacing/newlines should be inserted (`format` boolean).

### 2. Serialization Functions
- **`cJSON_Print` & `cJSON_PrintUnformatted`**: Public API entry points that allocate a top-level `printbuffer`, invoke the root serialization, and return a null-terminated C string.
- **`cJSON_PrintBuffered`**: Allows printing into a pre-allocated or user-managed buffer size.
- **`cJSON_PrintPreallocated`**: Prints directly into a provided fixed-size buffer, ensuring safe memory bounds for embedded or memory-constrained environments.

- **Type-Specific Printers**:
  - `print_value`: Dispatches serialization based on the `cJSON` node type (`cJSON_True`, `cJSON_False`, `cJSON_NULL`, `cJSON_Number`, `cJSON_String`, `cJSON_Array`, `cJSON_Object`).
  - `print_string`: Handles string escaping (control characters, quotes, backslashes, Unicode escaping where applicable).
  - `print_number`: Formats integer and floating-point values accurately into string representation.
  - `print_array` & `print_object`: Iterates through linked-list child elements, handling separators (commas), brackets/braces (`[]`, `{}`), keys, and indentation formatting.

---

## Component Interaction & Process Flow

### Printing Execution Flow
The diagram below illustrates how a `cJSON` tree is serialized into a string buffer:

```mermaid
sequenceDiagram
    participant User
    participant PublicAPI as cJSON_Print / cJSON_PrintUnformatted
    participant PrintBuffer as printbuffer Management
    participant PrintValue as print_value & Type Printers
    participant Hooks as internal_hooks.allocate

    User->>PublicAPI: cJSON_Print(root)
    PublicAPI->>Hooks: allocate initial printbuffer
    Hooks-->>PublicAPI: buffer instance
    PublicAPI->>PrintValue: print_value(root, 0, format, buffer)
    
    loop For each node in cJSON tree
        alt Object or Array
            PrintValue->>PrintBuffer: ensure buffer space / append delimiters & indentation
        else Primitive / String / Number
            PrintValue->>PrintBuffer: ensure buffer space / format & append value
        end
    end
    
    PrintValue-->>PublicAPI: serialization complete
    PublicAPI-->>User: returns null-terminated JSON string
```

---

## Related Modules

- **Core Types**: Refer to [cJSON_core_types.md](cJSON_core_types.md) for definitions of the `cJSON` struct and memory allocation hooks.
- **Parsing**: Refer to [cJSON_parsing.md](cJSON_parsing.md) for how incoming JSON strings are converted into `cJSON` structures.
- **Manipulation**: Refer to [cJSON_manipulation.md](cJSON_manipulation.md) for modifying `cJSON` trees before printing.
