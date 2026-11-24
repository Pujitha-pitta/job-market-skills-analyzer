{#
    True when `text` mentions the skill described by the regex fragment `pattern`.

    The fragment is wrapped in "word boundaries" so that:
      - 'java'  does NOT match 'javascript'
      - 'sql'   does NOT match 'mysql' or 'postgresql'
      - 'excel' does NOT match 'excellent'
    (+ and # count as word characters so 'c++' / 'c#' work.)
#}
{% macro text_contains_skill(text, pattern) %}
    regexp_instr(
        lower({{ text }}),
        '(^|[^a-z0-9+#])(' || {{ pattern }} || ')([^a-z0-9+#]|$)'
    ) > 0
{% endmacro %}
