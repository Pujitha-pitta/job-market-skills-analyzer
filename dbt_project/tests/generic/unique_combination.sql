{#
    Generic test: the combination of `columns` is unique in the model (its grain).
    Same idea as dbt_utils.unique_combination_of_columns, written by hand so the
    project has no package dependencies — and so you can see how generic tests work.
#}
{% test unique_combination(model, columns) %}

    select
        {{ columns | join(', ') }},
        count(*) as occurrences
    from {{ model }}
    group by {{ columns | join(', ') }}
    having count(*) > 1

{% endtest %}
