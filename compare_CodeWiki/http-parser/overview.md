# HTTP Parser Module Documentation

## Introduction

The `http-parser` module is a high-performance, event-driven HTTP request/response parser written in C. It is designed to be lightweight and fast, suitable for use in network applications that require efficient processing of HTTP messages. The parser operates as a state machine, invoking user-defined callbacks as various parts of an HTTP message are parsed (e.g., URL, headers, body).

## Architecture Overview

The `http-parser` module consists primarily of two files: `http_parser.h` and `http_parser.c`.

*   **`http_parser.h`**: This header file defines the public API, including the core data structures (`http_parser`, `http_parser_settings`, `http_parser_url`), enumerations for HTTP methods, status codes, and error types, and function prototypes for initializing and executing the parser.
*   **`http_parser.c`**: This file contains the implementation of the HTTP parser's state machine logic and helper functions. It processes incoming byte streams, transitions through various HTTP message states, and invokes the appropriate callbacks defined in `http_parser_settings`.

The module's architecture is centered around a state machine that processes HTTP messages byte by byte. It uses a callback-based mechanism to notify the embedding application about parsed elements.

```mermaid
graph TD
    A[Input Byte Stream] --> B{http_parser_execute};
    B --> C[http_parser State Machine];
    C --> D{Callbacks (http_parser_settings)};
    D -- on_message_begin --> E[Application Logic];
    D -- on_url --> E;
    D -- on_header_field --> E;
    D -- on_header_value --> E;
    D -- on_headers_complete --> E;
    D -- on_body --> E;
    D -- on_message_complete --> E;
    E --> F[Parsed Data (http_parser, http_parser_url)];
```

## Core Functionality

The `http-parser` module provides the following core functionalities:

### 1. HTTP Message Parsing (`http_parser`)

The `http_parser` structure is the central component that maintains the state of the parsing process. It holds information about the current HTTP message being parsed, such as:

*   `type`: Whether the parser is expecting an HTTP request, response, or both.
*   `flags`: Internal flags indicating various message properties (e.g., chunked encoding, keep-alive, upgrade).
*   `state`, `header_state`: Internal state variables for the state machine.
*   `nread`: Number of bytes read.
*   `content_length`: The expected length of the message body.
*   `http_major`, `http_minor`: HTTP protocol version.
*   `status_code`: HTTP status code (for responses).
*   `method`: HTTP request method (for requests).
*   `http_errno`: The last error encountered during parsing.
*   `upgrade`: Flag indicating if an upgrade header was present.
*   `data`: A user-defined pointer to associate arbitrary data with the parser instance.

The `http_parser_init` function initializes an `http_parser` instance, setting its type and initial state. The `http_parser_execute` function is the main entry point for feeding data to the parser. It processes a buffer of data and updates the parser's internal state, invoking callbacks as it identifies different parts of the HTTP message.

### 2. Callback Settings (`http_parser_settings`)

The `http_parser_settings` structure defines a set of callback functions that the parser invokes at specific events during the parsing process. These callbacks allow the embedding application to extract information from the HTTP message as it is being parsed.

*   `on_message_begin`: Called at the start of a new HTTP message.
*   `on_url`: Called when a URL segment is parsed (for requests).
*   `on_status`: Called when the status line is parsed (for responses).
*   `on_header_field`: Called when a header field name is parsed.
*   `on_header_value`: Called when a header field value is parsed.
*   `on_headers_complete`: Called when all headers have been parsed. This callback can return special values (1 or 2) to indicate that no body is expected or that the connection should be closed.
*   `on_body`: Called when a chunk of the message body is parsed.
*   `on_message_complete`: Called when the entire HTTP message has been parsed.
*   `on_chunk_header`: Called at the beginning of a new chunk in chunked transfer encoding.
*   `on_chunk_complete`: Called at the end of a chunk in chunked transfer encoding.

The `http_parser_settings_init` function initializes an `http_parser_settings` structure, setting all callbacks to NULL.

### 3. URL Parsing (`http_parser_url`)

The `http_parser_url` structure is used to store the parsed components of a URL. The `http_parser_parse_url` function takes a URL string and populates this structure with offsets and lengths for various URL fields:

*   `UF_SCHEMA`: The protocol scheme (e.g., "http", "https").
*   `UF_HOST`: The hostname.
*   `UF_PORT`: The port number.
*   `UF_PATH`: The path component.
*   `UF_QUERY`: The query string.
*   `UF_FRAGMENT`: The URL fragment.
*   `UF_USERINFO`: User information (e.g., "user:pass@").

The `http_parser_url_init` function initializes an `http_parser_url` structure.

### 4. Utility Functions

The module also provides several utility functions:

*   `http_parser_version()`: Returns the library's version number.
*   `http_should_keep_alive()`: Determines if the connection should be kept alive after the current message.
*   `http_method_str()`: Returns the string representation of an HTTP method enum.
*   `http_status_str()`: Returns the string representation of an HTTP status code enum.
*   `http_errno_name()`: Returns the name of an HTTP parser error.
*   `http_errno_description()`: Returns a human-readable description of an HTTP parser error.
*   `http_parser_pause()`: Pauses or unpauses the parser.
*   `http_body_is_final()`: Checks if the body parsing is complete.
*   `http_parser_set_max_header_size()`: Allows changing the maximum allowed header size at runtime.

## How the Module Fits into the Overall System

The `http-parser` module serves as a fundamental building block for any system that needs to process raw HTTP data. It abstracts away the complexities of HTTP protocol parsing, allowing higher-level components to focus on application-specific logic.

For example, in a web server or proxy, `http-parser` would be used to:
1.  Receive raw TCP data.
2.  Feed the data to `http_parser_execute`.
3.  Utilize the callbacks to extract the URL, headers, and body.
4.  Based on the parsed information, route requests, generate responses, or apply business logic.

In a client application, it would parse the HTTP responses received from a server. Its event-driven nature makes it suitable for asynchronous I/O models, where data arrives in chunks.
