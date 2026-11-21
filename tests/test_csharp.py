from crapper.coverage import CoverageBundle, parse_cobertura
from crapper.languages.csharp import functions_in_source
from crapper.model import Function

SCORE = """
namespace Demo.Core;

public class Sample
{
    public int Score(bool a, bool b, int[] values)
    {
        foreach (var value in values) { }
        while (a) { a = false; }
        do { b = false; } while (b);
        if (a && b || values.Length > 0) { }
        try { return a ? 1 : 0; }
        catch (System.Exception ex) { return 2; }
    }

    public int Switched(int value)
    {
        switch (value)
        {
            case 1:
                if (value > 0) { return 1; }
                return 0;
            default:
                return 2;
        }
    }

    public string Arms(int value)
    {
        var label = value switch
        {
            0 => "zero",
            1 => "one",
            _ => "many",
        };
        return label ?? "none";
    }
}
"""

SHAPES = """
using System;

namespace Demo.Outer;

public class Board
{
    private int _x;

    public Board(int x) { if (true) { _x = x; } }

    public int X => _x > 0 ? _x : 0;

    public int Place(int x)
    {
        int Local(int y) => y > 0 ? y : -y;
        return Local(x);
    }

    public class Inner
    {
        public void Tick() { }
    }

    public int Flat() => 1;
}
"""

NO_NAMESPACE = """
public class Loose
{
    public int Pick(bool flag, int a, int b)
    {
        return flag ? a : b;
    }
}
"""

COBERTURA = """<?xml version="1.0" encoding="utf-8"?>
<coverage line-rate="0.5" branch-rate="0.5" version="1.9">
  <packages>
    <package name="Demo.Core" line-rate="0.5">
      <classes>
        <class name="Demo.Core.Board" filename="Board.cs" line-rate="0.5">
          <methods>
            <method name="Place" signature="(System.Int32)" line-rate="0.75">
              <lines>
                <line number="6" hits="1"/>
                <line number="7" hits="1"/>
                <line number="8" hits="1"/>
                <line number="9" hits="0"/>
              </lines>
            </method>
          </methods>
          <lines>
            <line number="6" hits="1"/>
            <line number="7" hits="1"/>
            <line number="8" hits="1"/>
            <line number="9" hits="0"/>
          </lines>
        </class>
        <class name="Demo.Core.Outer/Inner" filename="Outer.cs" line-rate="1">
          <methods>
            <method name="Work" signature="(System.Int32)" line-rate="1">
              <lines><line number="12" hits="3"/></lines>
            </method>
          </methods>
          <lines><line number="12" hits="3"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""


def unit(name, namespace, start_line, end_line=None, path="src/Board.cs"):
    return Function(
        name=name,
        namespace=namespace,
        complexity=1,
        start_line=start_line,
        end_line=end_line or start_line,
        path=path,
        language="csharp",
    )


def test_counts_the_same_decisions_as_the_other_languages():
    methods = functions_in_source(SCORE, "Sample.cs")
    assert [(method.name, method.complexity) for method in methods] == [
        ("Score", 9),
        ("Switched", 4),
        ("Arms", 5),
    ]
    assert {method.namespace for method in methods} == {"Demo.Core.Sample"}


def test_constructors_accessors_and_local_functions_are_not_entries():
    methods = functions_in_source(SHAPES, "src/Board.cs")
    assert [(method.namespace, method.name, method.complexity) for method in methods] == [
        ("Demo.Outer.Board", "Place", 2),
        ("Demo.Outer.Board.Inner", "Tick", 1),
        ("Demo.Outer.Board", "Flat", 1),
    ]


def test_a_file_without_a_namespace_uses_the_type_name():
    methods = functions_in_source(NO_NAMESPACE, "Loose.cs")
    assert [(method.namespace, method.name, method.complexity) for method in methods] == [
        ("Loose", "Pick", 2)
    ]


def test_keywords_in_comments_and_strings_are_not_decisions():
    source = """
    namespace Demo.Core;

    public class Sample
    {
        public int Stable()
        {
            var text = "if && || ?? ?: switch catch";
            // if && || ?? ?: switch catch
            /* if && || ?? ?: switch catch */
            return 1;
        }
    }
    """
    methods = functions_in_source(source, "Sample.cs")
    assert [(method.name, method.complexity) for method in methods] == [("Stable", 1)]


def test_cobertura_scores_a_method_and_a_nested_type():
    methods, lines = parse_cobertura(COBERTURA)
    bundle = CoverageBundle(cobertura=methods, cobertura_class=lines)
    assert bundle.percent_for(unit("Place", "Demo.Core.Board", 6, 9)) == 75.0
    assert bundle.percent_for(unit("Work", "Demo.Core.Outer.Inner", 12)) == 100.0


def test_a_method_missing_from_the_report_falls_back_to_its_class_lines():
    methods, lines = parse_cobertura(COBERTURA)
    bundle = CoverageBundle(cobertura=methods, cobertura_class=lines)
    assert bundle.percent_for(unit("Untold", "Demo.Core.Board", 6, 8)) == 100.0
    assert bundle.percent_for(unit("Elsewhere", "Other.Type", 1, 2)) is None
