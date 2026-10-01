# TinyXML-2 Module Documentation

## Introduction

TinyXML-2 is a small, fast, and simple C++ XML parser that can load, save, and parse XML documents. It is designed for ease of use and efficiency, making it suitable for projects where a full-featured XML library might be overkill. The module provides a Document Object Model (DOM) interface to interact with XML data, allowing developers to navigate, query, and modify XML structures programmatically.

## Architecture Overview

The TinyXML-2 module is structured around a hierarchical set of classes that represent the various components of an XML document. The core of the architecture is the `XMLDocument` class, which acts as the container for the entire XML tree. All other XML nodes (`XMLElement`, `XMLText`, `XMLComment`, `XMLDeclaration`, `XMLUnknown`) are children of the `XMLDocument` or other `XMLNode` derived classes.

Attributes (`XMLAttribute`) are associated with `XMLElement`s but are not part of the main node hierarchy. Utility classes like `XMLUtil`, `StrPair`, and memory management components (`MemPool`, `DynArray`) support the parsing and manipulation of XML data.

### High-Level Component Diagram

```mermaid
graph TD
    XMLDocument -- manages --> XMLNode
    XMLNode <|-- XMLElement
    XMLNode <|-- XMLText
    XMLNode <|-- XMLComment
    XMLNode <|-- XMLDeclaration
    XMLNode <|-- XMLUnknown
    XMLElement -- has --> XMLAttribute
    XMLDocument -- uses --> XMLUtil
    XMLDocument -- uses --> StrPair
    XMLDocument -- uses --> MemPool
    XMLDocument -- uses --> DynArray
    XMLDocument -- uses --> XMLPrinter
    XMLDocument -- accepts --> XMLVisitor
    XMLHandle -- wraps --> XMLNode
    XMLConstHandle -- wraps --> XMLNode
```

## Core Functionality and Sub-modules

The TinyXML-2 module can be logically divided into several sub-modules, each responsible for a specific aspect of XML processing:

*   **Core XML Structures**: Handles the fundamental building blocks of an XML document, such as elements, text, comments, and declarations.
*   **Document Management**: Provides the main interface for loading, saving, parsing, and navigating the XML document.
*   **Parsing and Utility**: Contains helper functions and classes for parsing XML strings, handling character references, and general string utilities.
*   **Memory Management**: Manages the allocation and deallocation of XML objects efficiently using memory pools.
*   **Serialization and Printing**: Offers mechanisms to convert the in-memory XML structure back into a string or file format.

Detailed documentation for each sub-module can be found in their respective files:

*   [TinyXML-2_Core_XML_Structures.md](TinyXML-2_Core_XML_Structures.md)
*   [TinyXML-2_Document_Management.md](TinyXML-2_Document_Management.md)
*   [TinyXML-2_Parsing_and_Utility.md](TinyXML-2_Parsing_and_Utility.md)
*   [TinyXML-2_Memory_Management.md](TinyXML-2_Memory_Management.md)
*   [TinyXML-2_Serialization_and_Printing.md](TinyXML-2_Serialization_and_Printing.md)
