"""
Job Market Skills Analyzer — Streamlit dashboard on top of the dbt marts.

Works in two places without code changes:
  * locally:  cd dashboard; ..\.venv\Scripts\python.exe run_dashboard.py
              (asks for your Snowflake login; or use .streamlit/secrets.toml
               with `python -m streamlit run streamlit_app.py`)
  * Streamlit in Snowflake: paste this file into a new Streamlit app in Snowsight
"""

import altair as alt
import pandas as pd
import streamlit as st

MARTS = "JOB_MARKET_DB.MARTS"
ALL = "All countries"
DEFAULT_COUNTRY = "Sweden"          # change to your own country
DEFAULT_ROLE = "Data Engineer"
REAL = "🇸🇪 Real Swedish job ads (live)"
SAMPLE = "🌍 Sample data (8 countries)"

st.set_page_config(page_title="Job Market Skills Analyzer", page_icon="📊", layout="wide")


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------

@st.cache_resource
def get_session():
    try:  # running inside Streamlit in Snowflake
        from snowflake.snowpark.context import get_active_session
        return get_active_session()
    except Exception:  # running locally
        import os
        if os.environ.get("SNOWFLAKE_USER") and os.environ.get("SNOWFLAKE_PASSWORD"):
            # started by run_dashboard.py, which asked for the login in the terminal
            from snowflake.snowpark import Session
            return Session.builder.configs({
                "account": os.environ["SNOWFLAKE_ACCOUNT"],
                "user": os.environ["SNOWFLAKE_USER"],
                "password": os.environ["SNOWFLAKE_PASSWORD"],
                "role": "REPORTER",
                "warehouse": "TRANSFORM_WH",
                "database": "JOB_MARKET_DB",
                "schema": "MARTS",
            }).create()
        return st.connection("snowflake").session()  # uses .streamlit/secrets.toml


@st.cache_data(ttl=600, show_spinner=False)
def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Run SQL with ? placeholders (bound safely, never string-formatted)."""
    df = get_session().sql(sql, params=list(params) if params else None).to_pandas()
    df.columns = [c.lower() for c in df.columns]
    return df


def in_clause(values):
    return "(" + ", ".join("?" for _ in values) + ")"


SYMBOLS = {"EUR": "€", "GBP": "£", "USD": "$", "INR": "₹"}


def fmt_salary(yearly, currency, shown_as):
    """Show a yearly salary the way people in that country talk about pay."""
    if yearly is None or pd.isna(yearly):
        return "n/a"
    yearly = float(yearly)
    if shown_as == "LPA":
        return f"₹{yearly / 100000:.1f} LPA"
    if shown_as == "month":
        return f"{yearly / 12 / 1000:.0f}k {currency} / month"
    return f"{SYMBOLS.get(currency, currency + ' ')}{yearly / 1000:.0f}k / year"


# --------------------------------------------------------------------------
# Sidebar filters
# --------------------------------------------------------------------------

with st.sidebar:
    st.header("Data")
    data_choice = st.radio("Which job ads?", [REAL, SAMPLE], label_visibility="collapsed",
                           help="Real: every live Data/IT ad on Arbetsförmedlingen's Platsbanken (JobTech API). "
                                "Sample: synthetic postings for 8 countries, including salaries.")
source = "Real" if data_choice == REAL else "Sample"
is_real = source == "Real"

country_info = run_query(f"""
    select country, any_value(currency) as currency, any_value(salary_shown_as) as salary_shown_as,
           count(*) as postings
    from {MARTS}.fct_job_postings
    where data_source = ?
    group by country
    order by postings desc
""", (source,))
if country_info.empty:
    st.error(f"No {source.lower()} postings loaded yet. Run run_pipeline.py first.")
    st.stop()
countries = country_info["country"].tolist()
roles = run_query(f"""
    select role_family, count(*) as n from {MARTS}.fct_job_postings
    where data_source = ? group by 1 order by n desc
""", (source,))["role_family"].tolist()
bands = ["All", "Fresher (0-1 yrs)", "Junior (2-3 yrs)", "Mid (4-6 yrs)", "Senior (7+ yrs)", "Unknown"]

with st.sidebar:
    st.header("Filters")
    if is_real:
        country = "Sweden"
        st.markdown("**Country:** Sweden")
    else:
        country_options = [ALL] + countries
        country = st.selectbox("Country", country_options,
                               index=country_options.index(DEFAULT_COUNTRY) if DEFAULT_COUNTRY in countries else 0)
    role = st.selectbox("Target role", roles, index=roles.index(DEFAULT_ROLE) if DEFAULT_ROLE in roles else 0)

    if country == ALL:
        cities = []
    else:
        cities = run_query(f"""
            select city, count(*) as n from {MARTS}.fct_job_postings
            where data_source = ? and country = ? group by 1 order by n desc
        """, (source, country))["city"].tolist()
    selected_cities = st.multiselect("Cities (empty = all)", cities, disabled=not cities,
                                     help="Pick a country first to filter by city.")
    band = st.selectbox("Experience level", bands)
    top_n = st.slider("Number of skills to show", 5, 30, 15)

# key used by the marts: 'All Countries' rows hold the totals
country_key = "All Countries" if country == ALL else country
if country == ALL:
    currency, shown_as, salary_col = "EUR", "year", "salary_mid_eur"
else:
    info = country_info.set_index("country").loc[country]
    currency, shown_as, salary_col = info["currency"], info["salary_shown_as"], "salary_mid_yearly"

where = ["data_source = ?", "role_family = ?"]
params = [source, role]
if country != ALL:
    where.append("country = ?")
    params.append(country)
if selected_cities:
    where.append(f"city in {in_clause(selected_cities)}")
    params += selected_cities
if band != "All":
    where.append("experience_band = ?")
    params.append(band)
where_sql = " and ".join(where)
params = tuple(params)

place = "all countries" if country == ALL else (", ".join(selected_cities) or country)
st.title("📊 Job Market Skills Analyzer")
st.caption(f"Which skills should I learn to get a job?  Showing **{role}** jobs in **{place}**. "
           "Built on Snowflake + dbt.")
if is_real:
    st.caption("🔴 **Live data:** real ads from Arbetsförmedlingen's Platsbanken (JobTech open API), "
               "refreshed each time the pipeline runs.")
else:
    st.caption("🧪 **Sample data:** synthetic postings — great for exploring salaries and comparing countries.")

# --------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------

kpi = run_query(f"""
    select
        count(*)                                  as postings,
        avg(iff(is_salary_disclosed, 1, 0))       as pct_salary_disclosed,
        median({salary_col})                      as median_salary,
        avg(skill_count)                          as avg_skills
    from {MARTS}.fct_job_postings
    where {where_sql}
""", params).iloc[0]

if not kpi["postings"]:
    st.warning("No postings match these filters. Try removing a filter.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Job postings", f"{int(kpi['postings']):,}")
if is_real and pd.isna(kpi["median_salary"]):
    c2.metric("Median salary", "Not published",
              help="Swedish job ads almost never state the pay ('Lön enligt överenskommelse'). "
                   "Switch to Sample data to explore salaries.")
else:
    c2.metric("Median salary", fmt_salary(kpi["median_salary"], currency, shown_as),
              help="Midpoint of the advertised range. 'All countries' is converted to EUR at fixed rates.")
c3.metric("Avg skills asked per job", f"{float(kpi['avg_skills']):.1f}")
c4.metric("Postings showing salary", f"{float(kpi['pct_salary_disclosed']):.0%}")

# --------------------------------------------------------------------------
# Shared data: skill demand (for these filters) + salary premium (country + role)
# --------------------------------------------------------------------------

demand = run_query(f"""
    with jobs as (
        select job_id from {MARTS}.fct_job_postings where {where_sql}
    )
    select
        s.skill_name,
        s.skill_category,
        count(distinct s.job_id)                                   as postings,
        count(distinct s.job_id) / (select count(*) from jobs)     as share
    from {MARTS}.fct_job_skills s
    inner join jobs j on s.job_id = j.job_id
    group by 1, 2
    order by postings desc
""", params)
demand["share"] = demand["share"].astype(float)
top_skills = demand.head(int(top_n))

premium = run_query(f"""
    select skill_name, salary_premium_pct, avg_salary_with_skill, avg_salary_without_skill
    from {MARTS}.mart_salary_by_skill
    where data_source = ? and role_family = ? and country = ?
""", (source, role, country_key))
premium["salary_premium_pct"] = premium["salary_premium_pct"].astype(float)

all_skills = run_query(f"select skill_name from {MARTS}.dim_skills order by overall_rank")["skill_name"].tolist()

# --------------------------------------------------------------------------
# Personal learning path
# --------------------------------------------------------------------------

st.divider()
st.subheader("🎯 Your learning path")
st.caption(f"Tell us what you already know — we'll rank what to learn next for **{role}** jobs in **{place}**, "
           "based on how often employers ask for each skill, whether it pays more, and how well it fits "
           "with what you know.")

known = st.multiselect("Skills you already know", all_skills, placeholder="e.g. SQL, Python, Excel",
                       key="known_skills")

# skills that are often asked together with what you know
fit = pd.DataFrame(columns=["skill_name", "goes_with", "lift"])
if known:
    pairs_known = run_query(f"""
        select skill_a, skill_b, lift
        from {MARTS}.mart_skill_pairs
        where data_source = ? and role_family = ? and country = ?
          and (skill_a in {in_clause(known)} or skill_b in {in_clause(known)})
          and lift > 1
    """, (source, role, country_key, *known, *known))
    if not pairs_known.empty:
        pairs_known["lift"] = pairs_known["lift"].astype(float)
        a_known = pairs_known["skill_a"].isin(known)
        fit = pd.DataFrame({
            "skill_name": pairs_known["skill_b"].where(a_known, pairs_known["skill_a"]),
            "goes_with": pairs_known["skill_a"].where(a_known, pairs_known["skill_b"]),
            "lift": pairs_known["lift"],
        })
        fit = fit[~fit["skill_name"].isin(known)].sort_values("lift", ascending=False)
        fit = fit.drop_duplicates("skill_name")

candidates = demand.head(30).merge(premium[["skill_name", "salary_premium_pct"]], on="skill_name", how="left")
candidates = candidates.merge(fit, on="skill_name", how="left")
candidates = candidates[~candidates["skill_name"].isin(known)].copy()
candidates["score"] = (
    candidates["share"] * 100                                        # how often it is asked
    + candidates["salary_premium_pct"].fillna(0).clip(0, 30) * 0.5   # does it pay more
    + candidates["goes_with"].notna() * 8                            # fits what you know
)
candidates = candidates.sort_values("score", ascending=False)

# job-readiness: share of the top skills' demand you already cover
top15 = demand.head(15)
readiness = (top15.loc[top15["skill_name"].isin(known), "share"].sum() / top15["share"].sum()
             if not top15.empty else 0.0)
st.progress(min(float(readiness), 1.0),
            text=f"Job-readiness for {role} in {place}: **{readiness:.0%}** of the most requested skills covered")


def reason(row):
    parts = [f"Asked in **{row['share']:.0%}** of jobs"]
    if pd.notna(row.get("salary_premium_pct")):
        sign = "+" if row["salary_premium_pct"] >= 0 else ""
        parts.append(f"salary **{sign}{row['salary_premium_pct']:.0f}%** when required")
    if pd.notna(row.get("goes_with")):
        parts.append(f"often asked together with **{row['goes_with']}** (you know it)")
    return " · ".join(parts)


if candidates.empty:
    st.success("You know every top skill for this role — time to apply! 🚀")
else:
    steps = candidates.head(3).reset_index(drop=True)
    cols = st.columns(len(steps))
    for i, (col, (_, row)) in enumerate(zip(cols, steps.iterrows()), start=1):
        with col.container(border=True):
            st.markdown(f"**Step {i}**")
            st.markdown(f"### {row['skill_name']}")
            st.caption(row["skill_category"])
            st.markdown(reason(row))

    later = candidates.iloc[3:8]["skill_name"].tolist()
    if later:
        st.markdown("**After that:** " + " → ".join(f"`{s}`" for s in later))
    if not known:
        st.info("👆 Pick the skills you already know to personalise this plan.")

    with st.expander("See the full ranking"):
        show = candidates.head(20)[["skill_name", "skill_category", "share", "salary_premium_pct", "goes_with"]].rename(
            columns={"skill_name": "Skill", "skill_category": "Category", "share": "% of jobs",
                     "salary_premium_pct": "Salary premium %", "goes_with": "Goes with (you know)"})
        show["% of jobs"] = (show["% of jobs"] * 100).round(1)
        st.dataframe(show, hide_index=True, width="stretch")

# --------------------------------------------------------------------------
# Jobs that match you
# --------------------------------------------------------------------------

st.divider()
st.subheader("💼 Jobs that match you")
if not known:
    st.info("👆 Pick the skills you already know above to see which jobs you already match.")
else:
    jobs = run_query(f"""
        select job_id, job_title, company_name, city, posted_date, job_url, skills_list, skill_count
        from {MARTS}.fct_job_postings
        where {where_sql} and skill_count > 0
    """, params)
    known_set = set(known)
    jobs["skills"] = jobs["skills_list"].fillna("").apply(lambda s: set(x for x in s.split(", ") if x))
    jobs["have"] = jobs["skills"].apply(lambda s: sorted(s & known_set))
    jobs["missing"] = jobs["skills"].apply(lambda s: sorted(s - known_set))
    jobs["match"] = jobs.apply(lambda r: len(r["have"]) / max(len(r["skills"]), 1), axis=1)

    ready = int((jobs["match"] >= 0.8).sum())
    one_away = jobs[jobs["missing"].apply(len) == 1]
    unlock = one_away["missing"].apply(lambda m: m[0]).value_counts()

    m1, m2, m3 = st.columns(3)
    m1.metric("Jobs you match ≥ 80%", f"{ready:,}", help="You know at least 80% of the skills the ad mentions.")
    m2.metric("Jobs just 1 skill away", f"{len(one_away):,}")
    if not unlock.empty:
        m3.metric("Best skill to unlock more jobs", unlock.index[0],
                  delta=f"+{int(unlock.iloc[0])} jobs", delta_color="normal",
                  help="The missing skill that appears most often in jobs where it is the only thing you lack.")

    top_jobs = jobs.sort_values(["match", "posted_date"], ascending=[False, False]).head(25)
    table = pd.DataFrame({
        "Job": top_jobs["job_title"],
        "Company": top_jobs["company_name"],
        "City": top_jobs["city"],
        "Posted": pd.to_datetime(top_jobs["posted_date"]).dt.date,
        "Match": (top_jobs["match"] * 100).round(0),
        "You have": top_jobs["have"].apply(", ".join),
        "Missing": top_jobs["missing"].apply(", ".join),
    })
    column_config = {"Match": st.column_config.ProgressColumn("Match", format="%d%%", min_value=0, max_value=100)}
    if is_real:
        table["Ad"] = top_jobs["job_url"].values
        column_config["Ad"] = st.column_config.LinkColumn("Ad", display_text="Open ↗")
    else:
        st.caption("These are sample (synthetic) postings — switch to Real Swedish job ads for real jobs you can apply to.")
    st.dataframe(table, hide_index=True, width="stretch", column_config=column_config)

# --------------------------------------------------------------------------
# Top skills + salary premium
# --------------------------------------------------------------------------

st.divider()
left, right = st.columns([3, 2])

with left:
    st.subheader(f"Most requested skills — {role}")
    chart = (
        alt.Chart(top_skills)
        .mark_bar()
        .encode(
            x=alt.X("share:Q", title="% of postings", axis=alt.Axis(format="%")),
            y=alt.Y("skill_name:N", sort="-x", title=None),
            color=alt.Color("skill_category:N", title="Category"),
            tooltip=["skill_name", "skill_category", "postings", alt.Tooltip("share:Q", format=".1%")],
        )
        .properties(height=max(300, 24 * len(top_skills)))
    )
    st.altair_chart(chart, width="stretch")

with right:
    st.subheader("Which skills pay more?")
    st.caption(f"Avg salary of postings with the skill vs. without it (same role, {'all countries, in EUR' if country == ALL else country}).")
    if is_real:
        st.info("Swedish job ads almost never publish the salary — employers write "
                "*“Lön enligt överenskommelse”* (salary by agreement) instead. "
                "Switch to **Sample data** in the sidebar to explore salary premiums.")
    elif premium.empty:
        st.info("Not enough salary data for this role here. Try 'All countries'.")
    else:
        prem = premium.sort_values("salary_premium_pct", ascending=False).head(int(top_n)).copy()
        prem["with skill"] = [fmt_salary(v, currency, shown_as) for v in prem["avg_salary_with_skill"]]
        prem["without"] = [fmt_salary(v, currency, shown_as) for v in prem["avg_salary_without_skill"]]
        prem_chart = (
            alt.Chart(prem)
            .mark_bar()
            .encode(
                x=alt.X("salary_premium_pct:Q", title="Salary premium (%)"),
                y=alt.Y("skill_name:N", sort="-x", title=None),
                color=alt.condition("datum.salary_premium_pct > 0",
                                    alt.value("#2e7d32"), alt.value("#c62828")),
                tooltip=["skill_name", "salary_premium_pct", "with skill", "without"],
            )
            .properties(height=max(300, 24 * len(prem)))
        )
        st.altair_chart(prem_chart, width="stretch")

# --------------------------------------------------------------------------
# Countries, trends, pairs, freshers, cities
# --------------------------------------------------------------------------

st.divider()
tab_country, tab_trend, tab_pairs, tab_fresher, tab_city = st.tabs(
    ["🌍 Compare countries", "📈 Skill trends", "🔗 Skills asked together", "🎓 For freshers", "🏙️ Cities"])

with tab_country:
    st.caption(f"{role} jobs in every country. Salaries converted to EUR per year at fixed rates so they can be compared."
               + (" **Uses the sample data** — the real ads cover Sweden only." if is_real else ""))
    by_country = run_query(f"""
        select country,
               count(*)                                  as postings,
               round(median(salary_mid_eur), 0)          as median_salary_eur,
               avg(iff(work_mode in ('Remote', 'Hybrid'), 1, 0)) as share_remote_or_hybrid,
               avg(iff(experience_band = 'Fresher (0-1 yrs)', 1, 0)) as share_fresher
        from {MARTS}.fct_job_postings
        where data_source = 'Sample' and role_family = ?
        group by country
        order by postings desc
    """, (role,))
    if by_country.empty:
        st.info(f"The sample data has no '{role}' jobs to compare. Pick another role.")
    for c in ["median_salary_eur", "share_remote_or_hybrid", "share_fresher"]:
        by_country[c] = by_country[c].astype(float)
    by_country["selected"] = by_country["country"] == country
    st.altair_chart(
        alt.Chart(by_country).mark_bar().encode(
            x=alt.X("median_salary_eur:Q", title="Median salary (EUR / year)"),
            y=alt.Y("country:N", sort="-x", title=None),
            color=alt.condition("datum.selected", alt.value("#f4a261"), alt.value("#457b9d")),
            tooltip=["country", "postings", alt.Tooltip("median_salary_eur:Q", format=",.0f"),
                     alt.Tooltip("share_remote_or_hybrid:Q", format=".0%", title="remote / hybrid"),
                     alt.Tooltip("share_fresher:Q", format=".0%", title="fresher jobs")],
        ).properties(height=320),
        width="stretch",
    )
    top_by_country = run_query(f"""
        select country, listagg(skill_name, ', ') within group (order by demand_rank) as top_5_skills
        from {MARTS}.mart_skill_demand
        where data_source = 'Sample' and role_family = ? and country <> 'All Countries' and demand_rank <= 5
        group by country
    """, (role,))
    table = by_country.drop(columns="selected").merge(top_by_country, on="country", how="left")
    table["share_remote_or_hybrid"] = (table["share_remote_or_hybrid"] * 100).round(0)
    table["share_fresher"] = (table["share_fresher"] * 100).round(0)
    st.dataframe(table.rename(columns={
        "country": "Country", "postings": "Postings", "median_salary_eur": "Median salary (EUR/yr)",
        "share_remote_or_hybrid": "% remote/hybrid", "share_fresher": "% fresher jobs",
        "top_5_skills": "Top 5 skills"}), hide_index=True, width="stretch")

with tab_trend:
    default_trend = top_skills["skill_name"].head(5).tolist()
    trend_skills = st.multiselect("Skills to compare", all_skills, default=default_trend)
    if trend_skills:
        trends = run_query(f"""
            select posted_month, skill_name, share_of_postings
            from {MARTS}.mart_skill_trends
            where data_source = ? and role_family = ? and country = ? and skill_name in {in_clause(trend_skills)}
            order by posted_month
        """, (source, role, country_key, *trend_skills))
        trends["share_of_postings"] = trends["share_of_postings"].astype(float)
        st.altair_chart(
            alt.Chart(trends).mark_line(point=True).encode(
                x=alt.X("posted_month:T", title="Month"),
                y=alt.Y("share_of_postings:Q", title="% of postings", axis=alt.Axis(format="%")),
                color=alt.Color("skill_name:N", title="Skill"),
                tooltip=["posted_month:T", "skill_name", alt.Tooltip("share_of_postings:Q", format=".1%")],
            ).properties(height=380),
            width="stretch",
        )
        if is_real:
            st.caption("Live ads grouped by the month they were published. Older months only include ads "
                       "that are still open, so the most recent months are the most reliable.")
        elif country != ALL:
            st.caption("Smaller countries have fewer postings per month, so their lines are noisier.")

with tab_pairs:
    pairs = run_query(f"""
        select skill_a, skill_b, pair_count, share_of_postings, lift
        from {MARTS}.mart_skill_pairs
        where data_source = ? and role_family = ? and country = ?
        order by pair_count desc
        limit 15
    """, (source, role, country_key))
    st.caption("Lift > 1 means employers ask for the two skills together more often than by chance.")
    pairs["share_of_postings"] = (pairs["share_of_postings"].astype(float) * 100).round(1)
    st.dataframe(pairs.rename(columns={"skill_a": "Skill A", "skill_b": "Skill B",
                                       "pair_count": "Postings", "share_of_postings": "% of postings",
                                       "lift": "Lift"}),
                 hide_index=True, width="stretch")

with tab_fresher:
    fresher = run_query(f"""
        select skill_name, postings_with_skill, fresher_postings, share_of_fresher_postings
        from {MARTS}.mart_fresher_skills
        where data_source = ? and role_family = ? and country = ?
        order by demand_rank
        limit 10
    """, (source, role, country_key))
    if fresher.empty:
        st.info("No entry-level postings for this role here. Try 'All countries'.")
    else:
        st.caption(f"Based on {int(fresher['fresher_postings'].iloc[0]):,} entry-level / graduate postings (0-1 years).")
        fresher["share_of_fresher_postings"] = fresher["share_of_fresher_postings"].astype(float)
        st.altair_chart(
            alt.Chart(fresher).mark_bar(color="#5e60ce").encode(
                x=alt.X("share_of_fresher_postings:Q", title="% of entry-level postings",
                        axis=alt.Axis(format="%")),
                y=alt.Y("skill_name:N", sort="-x", title=None),
                tooltip=["skill_name", "postings_with_skill",
                         alt.Tooltip("share_of_fresher_postings:Q", format=".1%")],
            ).properties(height=320),
            width="stretch",
        )

with tab_city:
    city_sql = f"""
        select country, city, total_postings, median_salary_yearly, median_salary_eur,
               fresher_postings, share_remote_or_hybrid
        from {MARTS}.mart_city_overview
        where data_source = ? and role_family = ?
    """
    city_params = [source, role]
    if country != ALL:
        city_sql += " and country = ?"
        city_params.append(country)
    city_df = run_query(city_sql + " order by total_postings desc", tuple(city_params))
    y_col = "median_salary_eur" if country == ALL else "median_salary_yearly"
    y_title = "Median salary (EUR / year)" if country == ALL else f"Median salary ({currency} / year)"
    city_df[y_col] = city_df[y_col].astype(float)
    st.altair_chart(
        alt.Chart(city_df).mark_circle().encode(
            x=alt.X("total_postings:Q", title="Job postings"),
            y=alt.Y(f"{y_col}:Q", title=y_title, scale=alt.Scale(zero=False)),
            size=alt.Size("fresher_postings:Q", title="Fresher postings"),
            color=alt.Color("country:N", title="Country"),
            tooltip=["country", "city", "total_postings", alt.Tooltip(f"{y_col}:Q", format=",.0f"),
                     "fresher_postings"],
        ).properties(height=380),
        width="stretch",
    )
    city_df["median salary"] = [
        fmt_salary(v, currency, shown_as) for v in city_df[y_col]
    ]
    city_df["share_remote_or_hybrid"] = (city_df["share_remote_or_hybrid"].astype(float) * 100).round(1)
    st.dataframe(city_df[["country", "city", "total_postings", "median salary", "fresher_postings",
                          "share_remote_or_hybrid"]].rename(columns={
                     "country": "Country", "city": "City", "total_postings": "Postings",
                     "median salary": "Median salary", "fresher_postings": "Fresher postings",
                     "share_remote_or_hybrid": "% remote/hybrid"}),
                 hide_index=True, width="stretch")

st.caption("Real data: live Data/IT ads from Arbetsförmedlingen's JobTech API (open data). "
           "Sample data: synthetic postings from data_generator/. "
           "EUR conversions use the fixed rates in dbt_project/seeds/countries.csv.")
