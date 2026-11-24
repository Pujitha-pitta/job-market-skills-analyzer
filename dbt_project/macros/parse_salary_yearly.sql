{#
    Turn a raw salary string into a YEARLY amount in the posting's own currency.
    position = 1 -> lower bound, 2 -> upper bound

    Handles (examples from the raw data):
        '6-10 LPA'                         India, lakhs per annum
        '₹ 6,00,000 - 10,00,000 PA'        India, Indian digit grouping
        '45 000 - 55 000 kr/mån'           Sweden, monthly, space grouping
        'SEK 45,000-55,000 per month'      monthly, comma grouping
        'DKK 45.000 - 52.000 pr. måned'    Denmark, monthly, dot grouping
        '60.000 - 75.000 € p.a.'           Germany, yearly, dot grouping
        '£50k - £65k' / '$110K-$140K'      thousands written as k
        'Not disclosed' / 'Competitive' / 'Kollektivavtal'  -> null
#}
{% macro parse_salary_yearly(salary_text, position) %}
    case
        when {{ salary_text }} is null
          or {{ salary_text }} ilike any ('%not disclosed%', '%competitive%', '%kollektivavtal%',
                                          '%överenskommelse%', '%negotiable%')
            then null

        when {{ salary_text }} ilike '%lpa%'
            then try_to_decimal(regexp_substr({{ salary_text }}, '[0-9.]+', 1, {{ position }}), 10, 2) * 100000

        when {{ salary_text }} like '%₹%'
            then try_to_decimal(regexp_substr(replace({{ salary_text }}, ',', ''), '[0-9]+', 1, {{ position }}), 14, 0)

        else
            -- remove thousand separators (space, dot or comma before 3 digits), twice for millions
            try_to_decimal(regexp_substr(
                regexp_replace(
                    regexp_replace({{ salary_text }}, '([0-9])[ .,]([0-9]{3})', '\\1\\2'),
                    '([0-9])[ .,]([0-9]{3})', '\\1\\2'),
                '[0-9]+', 1, {{ position }}), 14, 0)
            * iff(regexp_like({{ salary_text }}, '.*[0-9][kK].*'), 1000, 1)                 -- '£50k'
            * iff({{ salary_text }} ilike any ('%month%', '%mån%', '%/mo%'), 12, 1)            -- monthly -> yearly
    end
{% endmacro %}
