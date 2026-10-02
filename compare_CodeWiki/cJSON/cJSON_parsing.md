# cJSON Parsing Module Documentation

## Introduction

The `cJSON_parsing` module is responsible for deserializing JSON text strings into hierarchical `cJSON` data structures. It utilizes the core utilities and data types defined in the [cJSON_core_types.md](cJSON_core_types.md) module—specifically relying on `parse_buffer`, `internal_hooks`, and the `error` tracking mechanism—to tokenize and parse JSON values, arrays, objects, strings, numbers, booleans, and nulls with robust error reporting and depth-limit checks.

---

## Architecture & Core Components

The parsing module processes raw unsigned character strings through a sequential set of parsing functions guided by the `parse_buffer` state. 

```mermaid
graph TD
    subgraph cJSON_parsing
        direction TB
        cJSON_Parse["cJSON_Parse / cJSON_ParseWithOpts<br/><i>Entry Points</i>"] --> parse_buffer_setup["Initialize parse_buffer"]
        parse_buffer_setup --> parse_value["parse_value<br/><i>Dispatcher by Token</i>"]
        
        parse_value --> parse_number["parse_number<br/><i>Number Parsing</i>"]
        parse_value --> parse_string["parse_string<br/><i>String & Escape Decoding</i>"]
        parse_value --> parse_array["parse_array<br/><i>Array Iteration & Child Linking</i>"]
        parse_value --> parse_object["parse_object<br/><i>Object Key-Value Parsing</i>"]
        parse_value --> parse_literal["parse_literal<br/><i>true / false / null</i>"]
    end

    subgraph Related Modules
        cJSON_parsing -->|Uses Types & Buffers| cJSON_core_types["cJSON_core_types<br/><i>[cJSON_core_types.md]</i>"]
    end

    style cJSON_Parse fill:#f9f,stroke:#333,stroke-width:2px
    style parse_value fill:#bbf,stroke:#333,stroke-width:1px
    style parse_buffer_setup fill:#bbf,stroke:#333,stroke-width:1px
```

---

## Component Details

### 1. Entry Point Functions
- **`cJSON_Parse(const char *value)`**: Convenience wrapper around `cJSON_ParseWithOpts` with default options (no explicit return parse end pointer, requiring full consumption or successful parse).
- **`cJSON_ParseWithOpts(const char *value, const char **return_parse_end, cJSON_bool require_null_terminated)`**: Configures buffer parameters, initializes the parsing state, handles buffer length calculation, enforces memory hooks, and manages error tracking locations if parsing fails.

### 2. Value Dispatcher (`parse_value`)
The core routing function that inspects whitespace and leading characters in the `parse_buffer` to dispatch parsing to the appropriate handler:
- `"` or `u8'"'` $\rightarrow$ `parse_string`
- `[` $\rightarrow$ `parse_array`
- `{` $\rightarrow$ `parse_object`
- `-` or `0-9` $\rightarrow$ `parse_number`
- `t`, `f`, `n` $\rightarrow$ `parse_literal` (`true`, `false`, `null`)

### 3. Specialized Parsers
- **`parse_number`**: Parses integer and floating-point representations, handling scientific notation (`e`/`E`), negative signs, exponents, and validating numeric boundaries into `valuedouble` and `valueint`.
- **`parse_string`**: Handles quoted strings, decodes UTF-8 sequences and JSON escape characters (`\n`, `\t`, `\r`, `\b`, `\f`, `\/`, `\"`, and Unicode `\uXXXX` surrogate pairs).
- **`parse_array`**: Iterates through comma-separated values inside square brackets `[...]`, building a doubly linked list of sibling `cJSON` nodes linked via `child`. Enforces maximum nesting depth limits (`cJSON_NESTING_LIMIT`).
- **`parse_object`**: Parses key-value pairs inside curly braces `{...}`, where each item's `string` field holds the parsed object key and `child` points to the value subtree.
- **`parse_literal`**: Validates and constructs boolean (`cJSON_True`, `cJSON_False`) and null (`cJSON_NULL`) nodes.

---

## Component Interaction & Process Flow

### JSON Parsing Sequence Flow

The following sequence diagram illustrates how `cJSON_ParseWithOpts` orchestrates the parsing process using `parse_buffer` and delegates to specific parsing functions:

```mermaid
sequenceDiagram
    participant User
    participant cJSON_Parse as cJSON_ParseWithOpts
    participant ParseBuffer as parse_buffer
    participant ParseValue as parse_value
    participant SpecificParser as parse_array / parse_object / parse_string / etc.

    User->>cJSON_Parse: cJSON_ParseWithOpts(value, &end, require_null)
    cJSON_Parse->>ParseBuffer: Initialize buffer (content, length, offset=0, depth=0)
    cJSON_Parse->>ParseValue: parse_value(item, &buffer)
    
    activate ParseValue
    ParseValue->>ParseBuffer: Skip whitespace / buffer buffer peek
    alt Is Array '['
        ParseValue->>SpecificParser: parse_array(item, &buffer)
        loop For each element
            SpecificParser->>ParseValue: parse_value(child_item, &buffer)
        end
    else Is Object '{'
        ParseValue->>SpecificParser: parse_object(item, &buffer)
        loop For each key-value pair
            SpecificParser->>ParseValue: parse_string(key, &buffer)
            SpecificParser->>ParseValue: parse_value(value_item, &buffer)
        end
    else Is String / Number / Literal
        ParseValue->>SpecificParser: parse_string / parse_number / parse_literal
    end
    SpecificParser-->>ParseValue: Return parsed cJSON node
    ParseValue-->>cJSON_Parse: Return success / failure
    deactivate ParseValue

    alt Parsing Success & require_null check
        cJSON_Parse-->>User: Return root cJSON pointer
    else Parsing Error
        cJSON_Parse->>cJSON_Parse: Record error position
        cJSON_Parse-->>User: Return NULL (sets global error pointer)
    end
```

---

## Related Modules

- **Core Types & Buffers**: Refer to [cJSON_core_types.md](cJSON_core_types.md) for the definition of `parse_buffer`, `internal_hooks`, and the `cJSON` struct populated during parsing.
- **Printing**: Refer to [cJSON_printing.md](cJSON_printing.md) for serializing parsed `cJSON` trees back into JSON string format.
- **Manipulation**: Refer to [cJSON_manipulation.md](cJSON_manipulation.md) for querying, modifying, adding, and removing elements in the resulting `cJSON` structure.
