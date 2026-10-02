# Documentation for `fmt` Module

### 1. Introduction

The `fmt` module, primarily defined in `format.h`, is the core of the {fmt} library, a modern C++ formatting library. It provides a safe, fast, and extensible alternative to traditional C-style `printf` and C++ iostreams for formatting text. The module focuses on efficient string manipulation, numerical conversions, and locale-aware formatting, all while offering a user-friendly API.

### 2. Core Functionality

The `fmt` module offers a wide range of functionalities, including:

*   **Type-Safe Formatting**: Prevents common errors associated with `printf`-style formatting by performing type checks at compile-time or runtime.
*   **Efficient Output**: Utilizes optimized algorithms and memory management (e.g., `basic_memory_buffer`) to minimize allocations and maximize performance.
*   **Extensible Formatting**: Allows users to define custom formatters for their own types.
*   **Numerical Formatting**: Comprehensive support for integer, floating-point (including `float128` and `double-double`), and hexadecimal formatting, with options for precision, width, alignment, and sign.
*   **Locale-Aware Formatting**: Provides mechanisms for localized output of numbers and dates (though date formatting details might reside in other modules, the infrastructure for locale is here).
*   **String and Character Handling**: Supports various string types, character escaping for debug output, and UTF-8/UTF-16 conversions.
*   **Error Handling**: Reports formatting errors through `fmt::format_error` exceptions or system error reporting functions.
*   **Compile-Time Format String Checks**: With `FMT_STRING`, format strings can be validated at compile time, catching errors early.

### 3. Architecture and Component Relationships

The `fmt` module is designed with a layered architecture, separating concerns such as buffer management, parsing, argument handling, and type-specific formatting.

#### 3.1. High-Level Module Structure

The module's core components interact to process format strings and arguments, producing the final output.

```mermaid
graph TD
    A[fmt::format / fmt::format_to] --> B(detail::format_handler);
    B --> C{Parse Format String};
    C --> D[detail::arg_formatter];
    C --> E[detail::default_arg_formatter];
    D --> F{Type-Specific Write Functions};
    E --> F;
    F --> G[detail::basic_memory_buffer];
    F --> H[FILE* / OutputIt];
    G --> H;
    D --&gt; I[detail::dynamic_spec_getter];
    I --&gt; D;
    B --&gt; J[fmt::format_error];
```

*   **`fmt::format` / `fmt::format_to`**: The primary entry points for formatting.
*   **`detail::format_handler`**: Orchestrates the formatting process, iterating through the format string and dispatching to appropriate handlers for text and arguments.
*   **`detail::arg_formatter` / `detail::default_arg_formatter`**: Visitors that handle the actual formatting of individual arguments based on their type and specified format `specs`.
*   **Type-Specific Write Functions**: A family of `detail::write` functions (e.g., `detail::write_int`, `detail::write_float`, `detail::write_char`, `detail::write_bytes`) that perform the low-level conversion and output.
*   **`detail::basic_memory_buffer`**: A flexible, dynamically growing buffer used to store the formatted output before it's written to the final destination.
*   **`FILE* / OutputIt`**: The ultimate destination for the formatted output, either a C-style file pointer or a C++ output iterator.
*   **`detail::dynamic_spec_getter`**: Used when format specifications (like width or precision) are provided by arguments rather than literals.
*   **`fmt::format_error`**: The exception type thrown for various formatting errors.

#### 3.2. Numerical Formatting Subsystem

Numerical formatting, especially for floating-point numbers, is a complex task requiring high precision and adherence to standards. The `fmt` module employs sophisticated algorithms like Dragonbox for this purpose.

```mermaid
graph TD
    A[Floating-Point Value (T)] --> B{detail::is_fast_float};
    B -- Yes --> C[dragonbox::to_decimal];
    B -- No --> D[detail::basic_fp];
    D --> E[detail::bigint];
    E --> F[detail::format_dragon];
    C --> G[detail::decimal_fp];
    G --> H[detail::write_float];
    F --> H;
    H --> I[detail::write_padded];
    I --> J[Output Buffer];
    K[detail::float_info] --> C;
    K --> D;
    K --> F;
    L[detail::digit_grouping] --> H;
    M[Locale Information] --> L;
```

*   **`Floating-Point Value (T)`**: The input floating-point number.
*   **`detail::is_fast_float`**: A trait to determine if a float type can use faster, specialized algorithms (like Dragonbox's direct path).
*   **`dragonbox::to_decimal`**: For "fast floats" (typically `float` and `double`), this function directly converts the binary floating-point representation to a decimal significand and exponent.
*   **`detail::basic_fp`**: Represents a floating-point number as a significand and binary exponent, used for more general or arbitrary-precision floating-point types.
*   **`detail::bigint`**: An arbitrary-precision integer class, essential for the `format_dragon` algorithm to handle large intermediate calculations without loss of precision.
*   **`detail::format_dragon`**: Implements the core Dragonbox algorithm (or a variation) to convert binary floating-point numbers to their shortest or fixed-precision decimal string representation.
*   **`detail::decimal_fp`**: A struct holding the decimal significand and exponent, the output of `dragonbox::to_decimal`.
*   **`detail::write_float`**: The main function for writing formatted floating-point numbers, which dispatches to `format_dragon` or `dragonbox::to_decimal` based on type and context.
*   **`detail::write_padded`**: Applies padding and alignment to the final string.
*   **`Output Buffer`**: The `basic_memory_buffer` or direct output iterator.
*   **`detail::float_info`**: Provides metadata about floating-point types (e.g., exponent bits, significand bits) to the Dragonbox implementation.
*   **`detail::digit_grouping`**: Handles locale-specific digit grouping for the integral part of the number.
*   **`Locale Information`**: Retrieved via `detail::thousands_sep_impl` and `detail::decimal_point_impl`.

Integer formatting follows a similar pattern but is generally less complex, relying on `count_digits`, `do_format_decimal`, and `format_base2e` for different bases. `format_int` provides a fast, specialized path for common integer types.

#### 3.3. Character Encoding and String Utilities

The module includes utilities for handling different character encodings and string manipulations.

```mermaid
graph TD
    A[Input String (UTF-8/UTF-16/UTF-32)] --> B{detail::to_utf8 / detail::utf8_to_utf16};
    B --> C[detail::basic_memory_buffer];
    C --> D[Formatted String];
    E[detail::find_escape] --> F{detail::write_escaped_cp};
    F --> G[detail::write_escaped_string];
    G --> D;
    H[detail::display_width_of] --> I{String Width Calculation};
    I --> J[detail::write_padded];
```

*   **`detail::to_utf8` / `detail::utf8_to_utf16`**: Classes for converting between UTF-8 and UTF-16/UTF-32 encodings. They use `basic_memory_buffer` for temporary storage.
*   **`detail::find_escape`**: Scans a string for characters that need escaping (e.g., control characters, quotes) for debug output.
*   **`detail::write_escaped_cp`**: Writes a single escaped code point (e.g., `\n`, `\x20`, `\u1234`).
*   **`detail::write_escaped_string`**: Iterates through a string, escaping characters as needed, typically for debug (`?`) format specifier.
*   **`detail::display_width_of`**: Determines the display width of a Unicode code point, crucial for correct alignment with wide characters.
*   **`String Width Calculation`**: Uses `display_width_of` to calculate the actual display width of a string, which can differ from its byte size due to wide characters.
*   **`detail::write_padded`**: Used to apply padding and alignment based on the calculated display width.

#### 3.4. Locale and Customization

The `fmt` module provides mechanisms for integrating with C++ locales and for extending its formatting capabilities.

```mermaid
graph TD
    A[fmt::locale_ref] --> B[detail::thousands_sep_impl];
    A --> C[detail::decimal_point_impl];
    B --> D[detail::digit_grouping];
    C --> D;
    D --> E[detail::write_int / detail::write_float];
    F[fmt::format_facet] --> G[fmt::loc_value];
    G --> H[detail::loc_writer];
    H --> E;
    I[User-Defined Type (T)] --> J[fmt::formatter<T>];
    J --> K[FormatContext];
    K --> E;
```

*   **`fmt::locale_ref`**: A lightweight wrapper for locale information, allowing locale-aware formatting without heavy `<locale>` dependencies.
*   **`detail::thousands_sep_impl` / `detail::decimal_point_impl`**: Functions to retrieve locale-specific thousands separators and decimal points.
*   **`detail::digit_grouping`**: Uses locale information to apply correct digit grouping during integer and fixed-point floating-point formatting.
*   **`fmt::format_facet`**: A locale facet that can be used to customize localized formatting behavior.
*   **`fmt::loc_value`**: A wrapper for values that are intended to be formatted using locale-specific rules.
*   **`detail::loc_writer`**: A visitor that applies locale-specific formatting to various types.
*   **`fmt::formatter<T>`**: The primary extension point for user-defined types. Users can specialize this template to provide custom parsing of format specifications and formatting logic for their types.
*   **`FormatContext`**: The context object passed to formatters, providing access to output iterators, arguments, and locale.

### 4. How the Module Fits into the Overall System

The `fmt` module is designed to be a standalone, high-performance formatting engine that can be integrated into any C++ application. It aims to replace or augment standard library formatting facilities (`printf`, `iostream`) by offering:

*   **Improved Safety**: Compile-time format string checks (with `FMT_STRING`) and type-safe argument handling reduce the risk of undefined behavior.
*   **Enhanced Performance**: Optimized algorithms and minimal overhead make it suitable for performance-critical applications.
*   **Modern C++ Idioms**: Leverages C++11 features and beyond (variadic templates, `constexpr`, user-defined literals) to provide a modern and ergonomic API.
*   **Portability**: Designed to work across various compilers and platforms.

Developers typically use `fmt::format` or `fmt::print` (if `fmt/os.h` or `fmt/ostream.h` are included) to produce formatted strings or output directly to streams. Its modular design allows for selective inclusion of features, minimizing binary size. For example, applications that don't need locale-aware formatting can avoid the associated overhead.

### 5. References

*   [core.md](core.md): For details on fundamental types, error handling, and basic utilities.
*   [os.md](os.md): For operating system-specific formatting functions.
*   [ostream.md](ostream.md): For integration with C++ iostreams.
*   [chrono.md](chrono.md): For date and time formatting.
*   [ranges.md](ranges.md): For formatting of ranges and containers.
