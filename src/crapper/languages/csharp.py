"""C# methods and cyclomatic complexity, following the Java rules.

A method with a body is one entry. Constructors, property accessors, and
operators are not entries of their own, and a local function stays inside the
enclosing method, the way a Python nested function does. Nested member types
become their own namespace (`Demo.Outer.Inner`) so uml-viewer can attach
scores to that class, and the declared namespace sits in front of it for the
Cobertura lookup.

Decision points: `if`, `for`, `foreach`, `while`, `do`, each `catch`, `?:`,
each `switch` section and `switch` expression arm, plus `&&`, `||`, and `??`.
"""

from crapper.languages.treesitter import (
    child_of_type,
    complexity,
    end_line,
    node_text,
    parse,
    start_line,
)
from crapper.model import Function

_TYPE_KINDS = {
    "class_declaration",
    "struct_declaration",
    "record_declaration",
    "record_struct_declaration",
    "interface_declaration",
    "enum_declaration",
    "delegate_declaration",
}
_NAMESPACE_KINDS = {"namespace_declaration", "file_scoped_namespace_declaration"}
_EXECUTABLE_KINDS = {
    "method_declaration",
    "constructor_declaration",
    "destructor_declaration",
    "operator_declaration",
    "local_function_statement",
    "accessor_declaration",
    "lambda_expression",
    "anonymous_method_expression",
}
_DECISIONS = {
    "if_statement",
    "for_statement",
    "foreach_statement",
    "while_statement",
    "do_statement",
    "catch_clause",
    "conditional_expression",
    "switch_section",
    "switch_expression_arm",
}
_LOGIC_TOKENS = {"&&", "||", "??"}
_BODIES = {"block", "arrow_expression_clause"}


def _is_logic(node) -> bool:
    return node.type == "binary_expression" and any(
        child.type in _LOGIC_TOKENS for child in node.children
    )


def _is_decision(node) -> bool:
    return node.type in _DECISIONS or _is_logic(node)


def _skip(node) -> bool:
    return node.type in _TYPE_KINDS


def _inside_executable(node) -> bool:
    current = node.parent
    while current is not None:
        if current.type in _EXECUTABLE_KINDS:
            return True
        current = current.parent
    return False


def _node_name(data: bytes, node) -> str | None:
    named = node.child_by_field_name("name")
    if named is None:
        named = child_of_type(node, "identifier")
    if named is None:
        return None
    return node_text(data, named)


def _chain(data: bytes, node, kinds: set[str]) -> list[str]:
    names: list[str] = []
    current = node.parent
    while current is not None:
        if current.type in kinds:
            name = _node_name(data, current)
            if name:
                names.append(name)
        current = current.parent
    names.reverse()
    return names


def _file_namespace(data: bytes, root) -> list[str]:
    """A file-scoped `namespace Demo.Core;` is a sibling of the types, not a parent."""

    for child in root.children:
        if child.type == "file_scoped_namespace_declaration":
            name = _node_name(data, child)
            if name:
                return [name]
    return []


def _qualify(namespaces: list[str], types: list[str]) -> str:
    return ".".join([*namespaces, *types])


def has_body(node) -> bool:
    return any(child_of_type(node, kind) is not None for kind in _BODIES)


def functions_in_source(
    source: str, path: str, project_root: str | None = None
) -> list[Function]:
    del project_root
    data, tree = parse(source, "csharp")
    prefix = _file_namespace(data, tree.root_node)
    found: list[Function] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type == "method_declaration" and not _inside_executable(node):
            name = _node_name(data, node)
            types = _chain(data, node, _TYPE_KINDS)
            if name and types and has_body(node):
                found.append(
                    Function(
                        name=name,
                        namespace=_qualify(
                            [*prefix, *_chain(data, node, _NAMESPACE_KINDS)], types
                        ),
                        complexity=complexity(node, _is_decision, _skip),
                        start_line=start_line(node),
                        end_line=end_line(node),
                        path=path,
                        language="csharp",
                        start_byte=node.start_byte,
                        end_byte=node.end_byte,
                    )
                )
            continue
        stack.extend(reversed(node.children))
    return found
