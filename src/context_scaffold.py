"""
Modulo per la risoluzione e generazione automatica dello Scaffold di Contesto Esterno (External Context Scaffold).

Fornisce a LLM Coder (Doc-to-Code), Tester (Pytest) ed al Test Harness:
1. Le definizioni dei tipi C/C++, struct, typedef, enum e costanti macro associate alla libreria.
2. Interfacce, costruttori e mock helper delle dipendenze esterne (evitando NameError e AttributeError).
3. Runtime standard C mock (allocazione, stringhe, stream).
"""

import os
import re
from typing import Dict, Any, List, Optional
from src.extract_metadata import CCodeExtractor

# Cache in memoria dei metadati degli header estratti per non ripetere il parsing AST Clang
_HEADER_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}

LIBRARY_HEADER_MAP = {
    "cjson": "dataset/sources/cJSON/cJSON.h",
    "tinyxml-2": "dataset/sources/TinyXML-2/tinyxml2.h",
    "tinyxml2": "dataset/sources/TinyXML-2/tinyxml2.h",
    "http-parser": "dataset/sources/http-parser/http_parser.h",
    "sds": "dataset/sources/sds/sds.h",
    "miniz": "dataset/sources/miniz/miniz.h",
    "opencv": "dataset/sources/OpenCV/fast_math.hpp"
}


def infer_library_name(func_name: str, signature: str = "", given_library: Optional[str] = None) -> str:
    """Inferisce deterministicamente la libreria di appartenenza di un simbolo."""
    if given_library and given_library.lower() not in ("none", "general", "unknown", ""):
        lib_clean = given_library.lower()
        if "cjson" in lib_clean:
            return "cJSON"
        if "tinyxml" in lib_clean or "xml" in lib_clean:
            return "TinyXML-2"
        if "http" in lib_clean:
            return "http-parser"
        if "sds" in lib_clean:
            return "sds"
        if "miniz" in lib_clean:
            return "miniz"
        if "opencv" in lib_clean or "cv" in lib_clean:
            return "OpenCV"

    fn_low = func_name.lower()
    sig_low = signature.lower()

    if fn_low.startswith("cjson") or "cjson" in sig_low:
        return "cJSON"
    if fn_low.startswith("xml") or "::" in func_name and any(x in fn_low for x in ["node", "element", "doc", "printer", "handle", "attribute", "text", "comment"]):
        return "TinyXML-2"
    if fn_low.startswith("http_") or "http_parser" in sig_low or "http_errno" in sig_low:
        return "http-parser"
    if fn_low.startswith("sds") or "sds " in sig_low or "sdshdr" in sig_low:
        return "sds"
    if fn_low.startswith("mz_") or "tdefl_" in fn_low or "tinfl_" in fn_low or "mz_" in sig_low:
        return "miniz"
    if fn_low.startswith("cv") or fn_low.startswith("cv::") or "cv::" in sig_low:
        return "OpenCV"

    return "General"


def get_library_ast_metadata(library: str, root_dir: str = ".") -> Optional[Dict[str, Any]]:
    """Estrae e memorizza in cache i metadati AST dell'header principale della libreria."""
    lib_key = library.lower()
    if lib_key in _HEADER_METADATA_CACHE:
        return _HEADER_METADATA_CACHE[lib_key]

    rel_path = LIBRARY_HEADER_MAP.get(lib_key)
    if not rel_path:
        for k, v in LIBRARY_HEADER_MAP.items():
            if k in lib_key or lib_key in k:
                rel_path = v
                break

    if not rel_path:
        return None

    abs_path = os.path.join(root_dir, rel_path) if not os.path.isabs(rel_path) else rel_path
    if not os.path.exists(abs_path):
        return None

    try:
        extractor = CCodeExtractor()
        meta = extractor.extract_metadata(abs_path)
        _HEADER_METADATA_CACHE[lib_key] = meta
        return meta
    except Exception as e:
        print(f"[WARN ContextScaffold] Impossibile estrarre metadati da {abs_path}: {e}")
        return None


def format_ast_context_for_prompt(library: str, func_name: str, root_dir: str = ".") -> str:
    """
    Formatta una sintesi compatta delle definizioni AST (struct, enum, costanti)
    da includere nel prompt dell'LLM (Coder e Tester) per specificare il contesto esterno.
    """
    meta = get_library_ast_metadata(library, root_dir=root_dir)
    if not meta:
        return ""

    lines = []
    # 1. Enums
    enums = meta.get("enums", [])
    relevant_enums = []
    for e in enums:
        e_name = e.get("name", "")
        if not e_name or e_name.startswith("(unnamed"):
            continue
        vals = [f"{v['name']} = {v['value']}" for v in e.get("values", [])[:8]]
        if vals:
            relevant_enums.append(f"  enum {e_name} {{ {', '.join(vals)} ... }};")

    if relevant_enums:
        lines.append("Enums / Error Codes:")
        lines.extend(relevant_enums[:5])

    # 2. Structs & Classes
    items = meta.get("classes", []) + meta.get("structs", [])
    if items:
        lines.append("Type Definitions & Struct/Class Fields:")
        for it in items[:6]:
            it_name = it.get("name", "")
            if not it_name or it_name.startswith("_"):
                continue
            fields = [f"{f['type']} {f['name']}" for f in it.get("fields", [])[:8]]
            f_str = ", ".join(fields) if fields else "/* opaque / container */"
            lines.append(f"  struct/class {it_name} {{ {f_str} }};")

    # 3. Macro / Costanti numeriche principali
    macros = [m["name"] for m in meta.get("macros", []) if not m["name"].startswith("_") and not m["name"].startswith("TIXML") and len(m["name"]) > 2]
    if macros:
        lines.append(f"Associated Preprocessor Macros/Flags: {', '.join(macros[:12])}")

    return "\n".join(lines)


UNIVERSAL_C_RUNTIME = '''# === [UNIVERSAL RUNTIME] Standard C Library & Auto-Tolerant Mock Base ===
import builtins
import sys

class TolerantBaseMock:
    """
    Mock universale ultra-tollerante: qualsiasi attributo o metodo non esplicitamente
    implementato restituisce un callable che ritorna un nuovo TolerantBaseMock (o valore neutro),
    prevenendo AttributeError a catena sia durante il setup dei test sia nel codice.
    """
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._items = []

    def __getattr__(self, name):
        def _dynamic_fallback(*args, **kwargs):
            return TolerantBaseMock()
        return _dynamic_fallback

    def __getitem__(self, item):
        return TolerantBaseMock()

    def __setitem__(self, key, value):
        pass

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __bool__(self):
        return True

    def __str__(self):
        return ""

    def __len__(self):
        return 0

# C Standard Functions Simulation
def strcmp(s1, s2):
    str1 = s1.decode('latin1') if isinstance(s1, (bytes, bytearray)) else str(s1 or "")
    str2 = s2.decode('latin1') if isinstance(s2, (bytes, bytearray)) else str(s2 or "")
    if str1 == str2: return 0
    return 1 if str1 > str2 else -1

def strncmp(s1, s2, n):
    str1 = s1.decode('latin1') if isinstance(s1, (bytes, bytearray)) else str(s1 or "")
    str2 = s2.decode('latin1') if isinstance(s2, (bytes, bytearray)) else str(s2 or "")
    sub1, sub2 = str1[:int(n)], str2[:int(n)]
    if sub1 == sub2: return 0
    return 1 if sub1 > sub2 else -1

def strlen(s):
    if s is None: return 0
    if isinstance(s, (bytes, bytearray)): return len(s)
    return len(str(s))

def strcpy(dst, src):
    return src

def memcpy(dst, src, n):
    return dst

def memset(dst, val, n):
    return dst

def malloc(sz):
    return bytearray(int(sz)) if sz and int(sz) > 0 else bytearray()

def calloc(num, sz):
    total = int(num * sz)
    return bytearray(total) if total > 0 else bytearray()

def realloc(ptr, sz):
    new_size = int(sz)
    b = bytearray(new_size)
    if ptr:
        l = min(len(ptr), new_size)
        b[:l] = ptr[:l]
    return b

def free(ptr):
    pass
'''

def get_library_runtime_scaffold(library: str, root_dir: str = ".") -> str:
    """
    Restituisce il codice Python puro eseguibile contenente mock, classi e costanti base
    da iniettare nel test runner prima del codice sintetizzato e della suite pytest.
    Include il runtime C universale, i mock specifici della libreria e gli stub auto-generati via AST.
    """
    lib_norm = library.lower()
    specific_scaffold = ""

    if "cjson" in lib_norm:
        specific_scaffold = '''# === [SCAFFOLD] cJSON Environment & Object Graph Mock ===
cJSON_Invalid = 0
cJSON_False = (1 << 0)
cJSON_True = (1 << 1)
cJSON_NULL = (1 << 2)
cJSON_Number = (1 << 3)
cJSON_String = (1 << 4)
cJSON_Array = (1 << 5)
cJSON_Object = (1 << 6)
cJSON_Raw = (1 << 7)
cJSON_IsReference = 256
cJSON_StringIsConst = 512

class cJSON(TolerantBaseMock):
    """Mock fedele e ultra-tollerante della struttura C cJSON per supportare traversamento e ispezione attributi."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next = kwargs.get("next", None)
        self.prev = kwargs.get("prev", None)
        self.child = kwargs.get("child", None)
        self.type = kwargs.get("type", kwargs.get("cjson_type", 0))
        self.valuestring = kwargs.get("valuestring", None)
        self.valueint = kwargs.get("valueint", 0)
        self.valuedouble = kwargs.get("valuedouble", 0.0)
        self.string = kwargs.get("string", kwargs.get("name", None))
        if args:
            if len(args) >= 1 and isinstance(args[0], int):
                self.type = args[0]
            if len(args) >= 2 and isinstance(args[1], str):
                self.valuestring = args[1]

    def __repr__(self):
        return f"<cJSON type={self.type} valuestring={self.valuestring!r} valueint={self.valueint}>"

class printbuffer(TolerantBaseMock):
    """Mock della struttura interna printbuffer di cJSON."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = kwargs.get("buffer", bytearray())
        if isinstance(self.buffer, str):
            self.buffer = bytearray(self.buffer.encode("utf-8"))
        self.length = kwargs.get("length", 0)
        self.offset = kwargs.get("offset", 0)
        self.depth = kwargs.get("depth", 0)
        self.noalloc = kwargs.get("noalloc", 0)
        self.format = kwargs.get("format", 0)
        self.buffer_is_dynamic = kwargs.get("buffer_is_dynamic", 0)
        self.hooks = kwargs.get("hooks", None)

def cJSON_CreateNull():
    return cJSON(type=cJSON_NULL)

def cJSON_CreateTrue():
    return cJSON(type=cJSON_True)

def cJSON_CreateFalse():
    return cJSON(type=cJSON_False)

def cJSON_CreateBool(b):
    return cJSON(type=cJSON_True if b else cJSON_False)

def cJSON_CreateNumber(num):
    v_int = int(num) if isinstance(num, (int, float)) else 0
    v_dbl = float(num) if isinstance(num, (int, float)) else 0.0
    return cJSON(type=cJSON_Number, valueint=v_int, valuedouble=v_dbl)

def cJSON_CreateString(string):
    return cJSON(type=cJSON_String, valuestring=str(string) if string is not None else None)

def cJSON_CreateArray():
    return cJSON(type=cJSON_Array)

def cJSON_CreateObject():
    return cJSON(type=cJSON_Object)

def cJSON_AddItemToArray(array, item):
    if not array or not item: return 0
    if not array.child:
        array.child = item
    else:
        c = array.child
        while c.next:
            c = c.next
        c.next = item
        item.prev = c
    return 1

def cJSON_AddItemToObject(obj, string, item):
    if not obj or not item: return 0
    item.string = string
    cJSON_AddItemToArray(obj, item)
    return 1

def cJSON_AddStringToObject(obj, name, string):
    s = cJSON_CreateString(string)
    cJSON_AddItemToObject(obj, name, s)
    return s

def cJSON_AddNumberToObject(obj, name, num):
    n = cJSON_CreateNumber(num)
    cJSON_AddItemToObject(obj, name, n)
    return n

def cJSON_AddBoolToObject(obj, name, b):
    val = cJSON_CreateBool(b)
    cJSON_AddItemToObject(obj, name, val)
    return val

def cJSON_AddNullToObject(obj, name):
    null_node = cJSON_CreateNull()
    cJSON_AddItemToObject(obj, name, null_node)
    return null_node

def cJSON_Delete(item):
    pass

def cJSON_free(ptr):
    pass

def cJSON_malloc(sz):
    return bytearray(sz)
'''

    elif "tinyxml" in lib_norm or "xml" in lib_norm:
        specific_scaffold = '''# === [SCAFFOLD] TinyXML-2 Environment & Classes Mock ===
XML_SUCCESS = 0
XML_NO_ATTRIBUTE = 1
XML_WRONG_ATTRIBUTE_TYPE = 2
XML_ERROR_FILE_NOT_FOUND = 3
XML_ERROR_FILE_COULD_NOT_BE_OPENED = 4
XML_ERROR_FILE_READ_ERROR = 5
XML_ERROR_PARSING_ELEMENT = 6
XML_ERROR_PARSING_ATTRIBUTE = 7
XML_ERROR_PARSING_TEXT = 8
XML_ERROR_PARSING_CDATA = 9
XML_ERROR_PARSING_COMMENT = 10
XML_ERROR_PARSING_DECLARATION = 11
XML_ERROR_PARSING_UNKNOWN = 12
XML_ERROR_EMPTY_DOCUMENT = 13
XML_ERROR_MISMATCHED_ELEMENT = 14
XML_ERROR_PARSING = 15
XML_CAN_NOT_CONVERT_TEXT = 16
XML_NO_TEXT_NODE = 17
XML_ELEMENT_DEPTH_EXCEEDED = 18
XML_ERROR_COUNT = 19

class _XMLErrorEnum:
    XML_SUCCESS = XML_SUCCESS
    XML_NO_ATTRIBUTE = XML_NO_ATTRIBUTE
    XML_WRONG_ATTRIBUTE_TYPE = XML_WRONG_ATTRIBUTE_TYPE
    XML_ERROR_FILE_NOT_FOUND = XML_ERROR_FILE_NOT_FOUND
    XML_ERROR_FILE_COULD_NOT_BE_OPENED = XML_ERROR_FILE_COULD_NOT_BE_OPENED
    XML_ERROR_FILE_READ_ERROR = XML_ERROR_FILE_READ_ERROR
    XML_ERROR_PARSING_ELEMENT = XML_ERROR_PARSING_ELEMENT
    XML_ERROR_PARSING_ATTRIBUTE = XML_ERROR_PARSING_ATTRIBUTE
    XML_ERROR_PARSING_TEXT = XML_ERROR_PARSING_TEXT
    XML_ERROR_PARSING_CDATA = XML_ERROR_PARSING_CDATA
    XML_ERROR_PARSING_COMMENT = XML_ERROR_PARSING_COMMENT
    XML_ERROR_PARSING_DECLARATION = XML_ERROR_PARSING_DECLARATION
    XML_ERROR_PARSING_UNKNOWN = XML_ERROR_PARSING_UNKNOWN
    XML_ERROR_EMPTY_DOCUMENT = XML_ERROR_EMPTY_DOCUMENT
    XML_ERROR_MISMATCHED_ELEMENT = XML_ERROR_MISMATCHED_ELEMENT
    XML_ERROR_PARSING = XML_ERROR_PARSING
    XML_CAN_NOT_CONVERT_TEXT = XML_CAN_NOT_CONVERT_TEXT
    XML_NO_TEXT_NODE = XML_NO_TEXT_NODE
    XML_ELEMENT_DEPTH_EXCEEDED = XML_ELEMENT_DEPTH_EXCEEDED
    XML_ERROR_COUNT = XML_ERROR_COUNT

XMLError = _XMLErrorEnum

class XMLNode(TolerantBaseMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parent = None
        self._firstChild = None
        self._lastChild = None
        self._prev = None
        self._next = None
        self._value = kwargs.get("value", "")
        self._document = kwargs.get("doc", None)
    def Value(self): return self._value
    def SetValue(self, val): self._value = str(val)
    def FirstChild(self): return self._firstChild
    def LastChild(self): return self._lastChild
    def NextSibling(self): return self._next
    def PreviousSibling(self): return self._prev
    def InsertFirstChild(self, node):
        if not node: return node
        node._parent = self
        node._next = self._firstChild
        if self._firstChild:
            self._firstChild._prev = node
        self._firstChild = node
        if not self._lastChild:
            self._lastChild = node
        return node
    def InsertEndChild(self, node):
        if not node: return node
        node._parent = self
        node._prev = self._lastChild
        if self._lastChild:
            self._lastChild._next = node
        self._lastChild = node
        if not self._firstChild:
            self._firstChild = node
        return node
    def ToElement(self): return self if isinstance(self, XMLElement) else None
    def ToDocument(self): return self if isinstance(self, XMLDocument) else None
    def ToDeclaration(self): return self if isinstance(self, XMLDeclaration) else None

class XMLDeclaration(XMLNode):
    def __init__(self, text="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._text = text

class XMLDocument(XMLNode):
    def __init__(self, processEntities=True, whitespaceMode=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hasBOM = kwargs.get("hasBOM", False)
        self._errorID = XML_SUCCESS
    def HasBOM(self): return self._hasBOM
    def ErrorID(self): return self._errorID
    def Parse(self, text, *args, **kwargs):
        if text is None:
            self._errorID = XML_ERROR_EMPTY_DOCUMENT
            return self._errorID
        s = str(text)
        self._hasBOM = s.startswith('\\ufeff')
        self._errorID = XML_SUCCESS
        return self._errorID
    def NewElement(self, name): return XMLElement(name=name, doc=self)
    def NewDeclaration(self, text=""): return XMLDeclaration(text=text)
    def Clear(self): pass

class XMLElement(XMLNode):
    def __init__(self, name="item", doc=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._document = doc
        self._attributes = {}
        if "attributes" in kwargs and isinstance(kwargs["attributes"], dict):
            self._attributes.update(kwargs["attributes"])
    def Name(self): return self._name
    def SetAttribute(self, name, val):
        self._attributes[name] = str(val)
        return XML_SUCCESS
    def Attribute(self, name): return self._attributes.get(name)
    def FindAttribute(self, name):
        if name in self._attributes:
            return XMLAttribute(name=name, value=self._attributes[name])
        return None
    def QueryStringAttribute(self, name, value=None):
        if name in self._attributes:
            if value is not None and isinstance(value, list):
                if len(value) > 0:
                    value[0] = self._attributes[name]
                else:
                    value.append(self._attributes[name])
            return XML_SUCCESS
        return XML_NO_ATTRIBUTE

class XMLAttribute(TolerantBaseMock):
    def __init__(self, name="", value="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._value = str(value)
    def Name(self): return self._name
    def Value(self): return self._value
    def IntValue(self):
        try:
            return int(self._value)
        except (ValueError, TypeError):
            return 0
    def QueryIntValue(self, value=None):
        try:
            val = int(self._value)
            if value is not None and isinstance(value, list):
                if len(value) > 0:
                    value[0] = val
                else:
                    value.append(val)
            return XML_SUCCESS
        except (ValueError, TypeError):
            return XML_WRONG_ATTRIBUTE_TYPE

class XMLPrinter(XMLNode):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._buffer = []
    def PushHeader(self, writeBOM=False, writeDec=True): pass
    def CStr(self): return "".join(self._buffer)

class XMLHandle(TolerantBaseMock):
    def __init__(self, node=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node = node
    def FirstChild(self):
        if self._node and hasattr(self._node, "FirstChild"):
            return XMLHandle(self._node.FirstChild())
        return XMLHandle(None)
    def NextSibling(self):
        if self._node and hasattr(self._node, "NextSibling"):
            return XMLHandle(self._node.NextSibling())
        return XMLHandle(None)
    def ToDeclaration(self):
        if self._node is not None and hasattr(self._node, "ToDeclaration"):
            return self._node.ToDeclaration()
        return self._node if isinstance(self._node, XMLDeclaration) else None
    def ToElement(self):
        if self._node is not None and hasattr(self._node, "ToElement"):
            return self._node.ToElement()
        return self._node if isinstance(self._node, XMLElement) else None
    def ToNode(self):
        return self._node
'''

    elif "http" in lib_norm:
        specific_scaffold = '''# === [SCAFFOLD] http-parser Environment & Enums Mock ===
HTTP_REQUEST = 1
HTTP_RESPONSE = 2
HTTP_BOTH = 3

class http_parser(TolerantBaseMock):
    def __init__(self, parser_type=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = parser_type
        self.flags = 0
        self.state = 0
        self.header_state = 0
        self.nread = 0
        self.content_length = 0
        self.http_major = 1
        self.http_minor = 1
        self.status_code = 0
        self.method = 0
        self.http_errno = 0
        self.data = None

class http_parser_settings(TolerantBaseMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_message_begin = None
        self.on_url = None
        self.on_status = None
        self.on_header_field = None
        self.on_header_value = None
        self.on_headers_complete = None
        self.on_body = None
        self.on_message_complete = None
        self.on_chunk_header = None
        self.on_chunk_complete = None

def http_parser_init(parser, parser_type=0):
    if parser is not None:
        parser.type = parser_type
        parser.state = 0
        parser.http_errno = 0
    return 0

def http_parser_settings_init(settings):
    return 0

HTTP_ERRNO_MAP = {
    0: "HPE_OK",
    1: "HPE_CB_message_begin",
    2: "HPE_CB_url",
    3: "HPE_CB_header_field",
    4: "HPE_CB_header_value",
    5: "HPE_CB_headers_complete",
    6: "HPE_CB_body",
    7: "HPE_CB_message_complete",
    8: "HPE_CB_status",
    9: "HPE_CB_chunk_header",
    10: "HPE_CB_chunk_complete",
    11: "HPE_INVALID_EOF_STATE",
    12: "HPE_HEADER_OVERFLOW",
    13: "HPE_CLOSED_CONNECTION",
    14: "HPE_INVALID_VERSION",
    15: "HPE_INVALID_STATUS",
    16: "HPE_INVALID_METHOD",
    17: "HPE_INVALID_URL",
    18: "HPE_INVALID_HOST",
    19: "HPE_INVALID_PORT",
    20: "HPE_INVALID_PATH",
    21: "HPE_INVALID_QUERY_STRING",
    22: "HPE_INVALID_FRAGMENT",
    23: "HPE_LF_EXPECTED",
    24: "HPE_INVALID_HEADER_TOKEN",
    25: "HPE_INVALID_CONTENT_LENGTH",
    26: "HPE_UNEXPECTED_CONTENT_LENGTH",
    27: "HPE_INVALID_CHUNK_SIZE",
    28: "HPE_INVALID_CONSTANT",
    29: "HPE_INVALID_INTERNAL_STATE",
    30: "HPE_STRICT",
    31: "HPE_PAUSED",
    32: "HPE_UNKNOWN"
}
'''

    elif "sds" in lib_norm:
        specific_scaffold = '''# === [SCAFFOLD] sds (Simple Dynamic Strings) Environment Mock ===
SDS_TYPE_5 = 0
SDS_TYPE_8 = 1
SDS_TYPE_16 = 2
SDS_TYPE_32 = 3
SDS_TYPE_64 = 4
SDS_TYPE_MASK = 7
SDS_TYPE_BITS = 3

class sdshdr(TolerantBaseMock):
    def __init__(self, len=0, alloc=0, flags=0, buf=b"", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.len = len
        self.alloc = alloc
        self.flags = flags
        self.buf = bytearray(buf)

def sdsnew(init=""):
    return bytearray(init.encode("utf-8")) if isinstance(init, str) else bytearray(init or b"")

def sdsempty():
    return bytearray()

def sdsfree(s):
    pass

def sdslen(s):
    return len(s) if s is not None else 0

def sdsavail(s):
    return 0

def sdsfreesplitres(tokens, count=0):
    pass
'''

    elif "miniz" in lib_norm:
        specific_scaffold = '''# === [SCAFFOLD] miniz Environment Mock ===
MZ_OK = 0
MZ_STREAM_END = 1
MZ_NEED_DICT = 2
MZ_ERRNO = -1
MZ_STREAM_ERROR = -2
MZ_DATA_ERROR = -3
MZ_MEM_ERROR = -4
MZ_BUF_ERROR = -5
MZ_VERSION_ERROR = -6
MZ_PARAM_ERROR = -10000

MZ_NO_FLUSH = 0
MZ_PARTIAL_FLUSH = 1
MZ_SYNC_FLUSH = 2
MZ_FULL_FLUSH = 3
MZ_FINISH = 4
MZ_BLOCK = 5

class mz_stream(TolerantBaseMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next_in = b""
        self.avail_in = 0
        self.total_in = 0
        self.next_out = bytearray()
        self.avail_out = 0
        self.total_out = 0
        self.msg = None
        self.state = None
        self.data_type = 0
        self.adler = 0
        self.reserved = 0
'''

    elif "opencv" in lib_norm:
        specific_scaffold = '''# === [SCAFFOLD] OpenCV Primitive Math & Types Mock ===
import math

def cvRound(val):
    return int(round(val))

def cvFloor(val):
    return int(math.floor(val))

def cvCeil(val):
    return int(math.ceil(val))

def cvIsNaN(val):
    return math.isnan(val)

def cvIsInf(val):
    return math.isinf(val)
'''

    # Auto-generazione automatica di stub per tutte le funzioni C estratte dall'header via Clang AST
    ast_stubs = []
    meta = get_library_ast_metadata(library, root_dir=root_dir)
    if meta:
        for f in meta.get("functions", []):
            fn_name = f.get("name", "")
            if not fn_name or "::" in fn_name or fn_name.startswith("_"):
                continue
            # Non sovrascrivere se già presente in specific_scaffold o builtins
            if fn_name in specific_scaffold or fn_name in UNIVERSAL_C_RUNTIME:
                continue
            ast_stubs.append(f"if '{fn_name}' not in globals():\n    def {fn_name}(*args, **kwargs): return TolerantBaseMock()")

    ast_stubs_str = "\n".join(ast_stubs)
    if ast_stubs_str:
        ast_stubs_str = f"\n# --- Auto-Generated AST Function Stubs for {library} ---\n{ast_stubs_str}\n"

    return f"{UNIVERSAL_C_RUNTIME}\n{specific_scaffold}\n{ast_stubs_str}"

