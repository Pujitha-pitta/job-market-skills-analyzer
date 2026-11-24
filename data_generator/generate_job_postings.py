"""
Generate a realistic (and intentionally a little messy) job postings dataset.

Why messy? Real job-portal data is never clean: city names are spelled
differently, salaries come in different formats, dates use mixed formats and
the same job is scraped twice. Cleaning that up is exactly what the dbt
staging layer is for.

Covers several countries (India, Sweden, Norway, Denmark, Germany, the
Netherlands, the UK and the US), each with its own cities, currency and
salary style ("12-18 LPA", "45 000 - 55 000 kr/mån", "£50k - £65k" ...).

Usage:
    python data_generator/generate_job_postings.py               # 12000 rows
    python data_generator/generate_job_postings.py --rows 20000  # more rows

Output: data/job_postings.csv
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------

# Each role: titles (title, level), salary model (LPA) and skill probabilities.
# level: "entry" -> 0-3 yrs, "senior" -> 5+ yrs, "any" -> anything
ROLES = {
    "Data Analyst": {
        "weight": 18,
        "titles": [("Data Analyst", "any"), ("Junior Data Analyst", "entry"),
                   ("Senior Data Analyst", "senior"), ("Business Analyst", "any"),
                   ("BI Analyst", "any"), ("Power BI Developer", "any"),
                   ("Data Analyst - Fresher", "entry")],
        "base_salary": 4.0, "per_year": 1.3,
        "skills": {"SQL": 0.85, "Excel": 0.70, "Power BI": 0.50, "Tableau": 0.35,
                   "Python": 0.50, "Statistics": 0.35, "Data Visualization": 0.40,
                   "Communication": 0.50, "Pandas": 0.15, "Looker": 0.08,
                   "Snowflake": 0.10, "dbt": 0.05, "Problem Solving": 0.30},
    },
    "Data Engineer": {
        "weight": 16,
        "titles": [("Data Engineer", "any"), ("Senior Data Engineer", "senior"),
                   ("Junior Data Engineer", "entry"), ("Big Data Engineer", "any"),
                   ("ETL Developer", "any"), ("Data Engineer II", "any"),
                   ("Lead Data Engineer", "senior")],
        "base_salary": 5.5, "per_year": 2.0,
        "skills": {"SQL": 0.90, "Python": 0.80, "Spark": 0.60, "Airflow": 0.45,
                   "AWS": 0.50, "Azure": 0.30, "GCP": 0.15, "Snowflake": 0.35,
                   "dbt": 0.25, "Kafka": 0.25, "ETL": 0.55, "Data Modeling": 0.40,
                   "Databricks": 0.30, "Docker": 0.20, "Git": 0.35, "Hadoop": 0.15,
                   "BigQuery": 0.10, "Redshift": 0.12},
    },
    "Analytics Engineer": {
        "weight": 5,
        "titles": [("Analytics Engineer", "any"), ("Senior Analytics Engineer", "senior")],
        "base_salary": 6.5, "per_year": 2.0,
        "skills": {"SQL": 0.95, "dbt": 0.80, "Snowflake": 0.60, "Data Modeling": 0.70,
                   "Git": 0.55, "Airflow": 0.30, "Looker": 0.30, "Python": 0.50,
                   "BigQuery": 0.20, "Tableau": 0.15, "Communication": 0.35},
    },
    "Data Scientist": {
        "weight": 10,
        "titles": [("Data Scientist", "any"), ("Senior Data Scientist", "senior"),
                   ("Junior Data Scientist", "entry"), ("Data Science Intern", "entry")],
        "base_salary": 6.0, "per_year": 2.2,
        "skills": {"Python": 0.95, "SQL": 0.70, "Machine Learning": 0.85,
                   "Statistics": 0.65, "Pandas": 0.50, "NumPy": 0.35,
                   "Scikit-learn": 0.45, "TensorFlow": 0.25, "PyTorch": 0.25,
                   "Deep Learning": 0.30, "NLP": 0.25, "LLM / GenAI": 0.20,
                   "Data Visualization": 0.25, "Spark": 0.10, "AWS": 0.15},
    },
    "ML Engineer": {
        "weight": 6,
        "titles": [("Machine Learning Engineer", "any"), ("ML Engineer", "any"),
                   ("AI Engineer", "any"), ("GenAI Engineer", "any"),
                   ("Senior ML Engineer", "senior")],
        "base_salary": 7.0, "per_year": 2.5,
        "skills": {"Python": 0.95, "Machine Learning": 0.80, "PyTorch": 0.50,
                   "TensorFlow": 0.35, "Docker": 0.45, "Kubernetes": 0.30,
                   "AWS": 0.40, "LLM / GenAI": 0.45, "Deep Learning": 0.45,
                   "NLP": 0.30, "FastAPI": 0.25, "Git": 0.35, "SQL": 0.30},
    },
    "Backend Developer": {
        "weight": 14,
        "titles": [("Backend Developer", "any"), ("Java Developer", "any"),
                   ("Python Developer", "any"), ("Software Engineer - Backend", "any"),
                   ("Senior Java Developer", "senior"), ("Back End Engineer", "any")],
        "base_salary": 4.5, "per_year": 2.0,
        "skills": {"Java": 0.55, "Spring Boot": 0.45, "Python": 0.40, "Django": 0.20,
                   "Flask": 0.10, "FastAPI": 0.10, "REST APIs": 0.60, "MySQL": 0.40,
                   "PostgreSQL": 0.30, "MongoDB": 0.20, "Docker": 0.35,
                   "Kubernetes": 0.20, "AWS": 0.35, "Git": 0.50, "SQL": 0.35,
                   "Agile": 0.25, "Golang": 0.08},
    },
    "Frontend Developer": {
        "weight": 9,
        "titles": [("Frontend Developer", "any"), ("React Developer", "any"),
                   ("UI Developer", "any"), ("Front End Engineer", "any"),
                   ("Senior Frontend Developer", "senior")],
        "base_salary": 4.0, "per_year": 1.8,
        "skills": {"JavaScript": 0.85, "React": 0.70, "TypeScript": 0.45,
                   "HTML/CSS": 0.75, "Git": 0.45, "REST APIs": 0.35,
                   "Node.js": 0.15, "Agile": 0.20, "Communication": 0.20},
    },
    "Full Stack Developer": {
        "weight": 9,
        "titles": [("Full Stack Developer", "any"), ("MERN Stack Developer", "any"),
                   ("Full-Stack Engineer", "any"), ("Senior Full Stack Developer", "senior")],
        "base_salary": 4.5, "per_year": 2.0,
        "skills": {"JavaScript": 0.85, "React": 0.65, "Node.js": 0.65, "MongoDB": 0.45,
                   "TypeScript": 0.35, "HTML/CSS": 0.50, "REST APIs": 0.50,
                   "Git": 0.45, "AWS": 0.25, "Docker": 0.20, "MySQL": 0.20},
    },
    "QA / Test Engineer": {
        "weight": 6,
        "titles": [("QA Engineer", "any"), ("Automation Test Engineer", "any"),
                   ("SDET", "any"), ("QA Analyst", "entry")],
        "base_salary": 3.5, "per_year": 1.4,
        "skills": {"Selenium": 0.70, "Java": 0.45, "Python": 0.35, "Jira": 0.45,
                   "Agile": 0.45, "SQL": 0.35, "REST APIs": 0.30, "Git": 0.25},
    },
    "DevOps / Cloud Engineer": {
        "weight": 6,
        "titles": [("DevOps Engineer", "any"), ("Cloud Engineer", "any"),
                   ("Site Reliability Engineer", "any"), ("AWS Cloud Engineer", "any"),
                   ("Senior DevOps Engineer", "senior")],
        "base_salary": 5.0, "per_year": 2.0,
        "skills": {"AWS": 0.70, "Azure": 0.35, "GCP": 0.15, "Docker": 0.75,
                   "Kubernetes": 0.65, "Linux": 0.60, "Git": 0.50, "Python": 0.35,
                   "Terraform": 0.40, "Jenkins": 0.35},
    },
    "Other": {
        "weight": 1,
        "titles": [("Technical Support Engineer", "any"), ("IT Support Executive", "entry")],
        "base_salary": 3.0, "per_year": 0.8,
        "skills": {"Linux": 0.30, "Communication": 0.60, "Problem Solving": 0.40,
                   "Excel": 0.20},
    },
}

# How a skill is actually written in postings (variety makes extraction realistic)
SKILL_FORMS = {
    "Power BI": ["Power BI", "PowerBI"],
    "Spark": ["Spark", "PySpark", "Apache Spark"],
    "AWS": ["AWS", "Amazon Web Services"],
    "GCP": ["GCP", "Google Cloud"],
    "Kubernetes": ["Kubernetes", "K8s"],
    "Git": ["Git", "GitHub", "Git/GitLab"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "Machine Learning": ["Machine Learning", "ML"],
    "Statistics": ["statistics", "statistical analysis"],
    "Data Modeling": ["data modeling", "data modelling", "dimensional data modeling"],
    "ETL": ["ETL", "ELT", "ETL/ELT"],
    "Data Visualization": ["data visualization", "data visualisation"],
    "REST APIs": ["REST APIs", "RESTful APIs", "REST API"],
    "LLM / GenAI": ["LLMs", "Generative AI", "GenAI"],
    "Node.js": ["Node.js", "NodeJS"],
    "React": ["React", "React.js", "ReactJS"],
    "HTML/CSS": ["HTML/CSS", "HTML5 and CSS3"],
    "Spring Boot": ["Spring Boot", "SpringBoot"],
    "Problem Solving": ["problem-solving", "problem solving"],
    "Agile": ["Agile", "Scrum", "Agile/Scrum"],
    "PostgreSQL": ["PostgreSQL", "Postgres"],
    "MongoDB": ["MongoDB", "Mongo"],
    "Golang": ["Golang"],
    "BigQuery": ["BigQuery", "Big Query"],
    "Communication": ["communication"],
}

# Salary premium (LPA) a skill adds on average -> makes salary insights interesting
SKILL_PREMIUM = {
    "Snowflake": 1.8, "dbt": 1.5, "Databricks": 1.6, "Spark": 1.4, "Kafka": 1.2,
    "Kubernetes": 1.3, "Terraform": 1.0, "PyTorch": 1.5, "LLM / GenAI": 2.5,
    "Deep Learning": 1.0, "Airflow": 0.8, "AWS": 0.8, "TypeScript": 0.6,
    "Golang": 1.5, "Excel": -0.5, "Selenium": -0.3,
}

# Skills whose popularity changes over the year (multiplier at start -> end)
SKILL_TREND = {
    "LLM / GenAI": (0.4, 1.6), "dbt": (0.7, 1.3), "Snowflake": (0.8, 1.25),
    "Databricks": (0.7, 1.3), "Hadoop": (1.3, 0.5), "PyTorch": (0.85, 1.2),
}

# Countries: share of postings, salary level and cities.
#   target_mid: typical yearly salary (local currency) of a mid-level data engineer,
#               used to scale every role's salary for that country.
#   cities:     name -> (weight, salary bonus, how the location shows up in raw data)
COUNTRIES = {
    "India": {
        "weight": 25, "currency": "INR", "target_mid": None,   # India keeps the LPA model
        "cities": {
            "Bangalore": (26, 1.12, ["Bangalore", "Bengaluru", "Bengaluru, Karnataka", "bangalore "]),
            "Hyderabad": (16, 1.05, ["Hyderabad", "Hyderabad, Telangana"]),
            "Pune": (12, 1.0, ["Pune", "Pune, Maharashtra"]),
            "Chennai": (10, 1.0, ["Chennai", "Chennai, Tamil Nadu"]),
            "Mumbai": (9, 1.06, ["Mumbai", "Mumbai, Maharashtra"]),
            "Gurgaon": (7, 1.08, ["Gurgaon", "Gurugram"]),
            "Noida": (6, 1.0, ["Noida", "Noida, Uttar Pradesh"]),
            "Delhi": (4, 1.0, ["New Delhi", "Delhi"]),
            "Kolkata": (3, 1.0, ["Kolkata"]),
            "Ahmedabad": (2, 1.0, ["Ahmedabad"]),
            "Remote": (5, 1.0, ["Remote", "Work from home", "WFH"]),
        },
    },
    "Sweden": {
        "weight": 20, "currency": "SEK", "target_mid": 624_000,
        "cities": {
            "Stockholm": (45, 1.08, ["Stockholm", "Stockholm, Sweden", "stockholm "]),
            "Gothenburg": (20, 1.0, ["Göteborg", "Gothenburg", "Gothenburg, Sweden"]),
            "Malmö": (14, 1.0, ["Malmö", "Malmo", "Malmö, Sweden"]),
            "Uppsala": (6, 0.97, ["Uppsala"]),
            "Linköping": (6, 0.97, ["Linköping", "Linkoping"]),
            "Lund": (4, 0.98, ["Lund"]),
            "Remote": (5, 1.0, ["Remote - Sweden", "Remote (Sweden)", "Distans"]),
        },
    },
    "Norway": {
        "weight": 5, "currency": "NOK", "target_mid": 750_000,
        "cities": {
            "Oslo": (60, 1.05, ["Oslo", "Oslo, Norway"]),
            "Bergen": (20, 1.0, ["Bergen"]),
            "Trondheim": (15, 0.98, ["Trondheim"]),
            "Remote": (5, 1.0, ["Remote - Norway"]),
        },
    },
    "Denmark": {
        "weight": 6, "currency": "DKK", "target_mid": 624_000,
        "cities": {
            "Copenhagen": (65, 1.05, ["Copenhagen", "København", "Copenhagen, Denmark"]),
            "Aarhus": (25, 1.0, ["Aarhus", "Århus"]),
            "Remote": (10, 1.0, ["Remote - Denmark"]),
        },
    },
    "Germany": {
        "weight": 12, "currency": "EUR", "target_mid": 68_000,
        "cities": {
            "Berlin": (35, 1.0, ["Berlin", "Berlin, Germany"]),
            "Munich": (25, 1.08, ["München", "Munich", "Munich, Germany"]),
            "Hamburg": (15, 1.02, ["Hamburg"]),
            "Frankfurt": (15, 1.05, ["Frankfurt am Main", "Frankfurt"]),
            "Remote": (10, 1.0, ["Remote - Germany", "Remote (DE)"]),
        },
    },
    "Netherlands": {
        "weight": 8, "currency": "EUR", "target_mid": 64_000,
        "cities": {
            "Amsterdam": (50, 1.05, ["Amsterdam", "Amsterdam, Netherlands"]),
            "Rotterdam": (18, 1.0, ["Rotterdam"]),
            "Utrecht": (14, 1.0, ["Utrecht"]),
            "Eindhoven": (12, 1.0, ["Eindhoven"]),
            "Remote": (6, 1.0, ["Remote - Netherlands"]),
        },
    },
    "United Kingdom": {
        "weight": 12, "currency": "GBP", "target_mid": 60_000,
        "cities": {
            "London": (55, 1.15, ["London", "London, UK", "Greater London"]),
            "Manchester": (15, 1.0, ["Manchester"]),
            "Edinburgh": (10, 1.0, ["Edinburgh"]),
            "Cambridge": (8, 1.05, ["Cambridge, UK"]),
            "Remote": (12, 1.0, ["Remote - UK", "Remote (UK)"]),
        },
    },
    "United States": {
        "weight": 12, "currency": "USD", "target_mid": 125_000,
        "cities": {
            "New York": (25, 1.15, ["New York, NY", "NYC", "New York"]),
            "San Francisco": (20, 1.25, ["San Francisco, CA", "SF Bay Area"]),
            "Seattle": (15, 1.12, ["Seattle, WA"]),
            "Austin": (12, 1.0, ["Austin, TX"]),
            "Chicago": (10, 0.98, ["Chicago, IL"]),
            "Remote": (18, 1.0, ["Remote - US", "Remote (USA)"]),
        },
    },
}

# A mid-level data engineer in India earns about this many LPA; other countries
# are scaled so that this job lands on their target_mid.
INDIA_REFERENCE_LPA = 17.0

# (raw text, min years, max years, weight)
EXPERIENCE = [
    ("Fresher", 0, 1, 8), ("0-1 years", 0, 1, 6), ("0-2 years", 0, 2, 10),
    ("1-3 years", 1, 3, 14), ("2-5 Yrs", 2, 5, 20), ("3-6 years", 3, 6, 16),
    ("5-8 years", 5, 8, 13), ("7-10 years", 7, 10, 7), ("8+ years", 8, 12, 6),
]

# Outside India postings say "Graduate" / "Entry level" instead of "Fresher"
EXPERIENCE_INTL = [
    ("Graduate", 0, 1, 6), ("Entry level", 0, 1, 8), ("0-2 years", 0, 2, 10),
    ("1-3 years", 1, 3, 14), ("2-5 years", 2, 5, 20), ("3+ years", 3, 6, 16),
    ("5+ years", 5, 8, 13), ("7-10 years", 7, 10, 7), ("8+ years", 8, 12, 6),
]

COMPANY_PREFIX = ["Nimbus", "Quantiq", "Bluepeak", "Kavya", "Tridenta", "Orbitline",
                  "Saffron", "Vertexa", "Lumen", "Ganga", "Zenith", "Indus",
                  "Pixelcraft", "Cobalt", "Redwood", "Aravali", "Monsoon", "Tejas",
                  "Fjord", "Norrsken", "Aurora", "Vasa", "Lagom", "Kite", "Harbor", "Elbe"]
COMPANY_SUFFIX = ["Analytics", "Technologies", "Labs", "Solutions", "Systems",
                  "Digital", "Fintech", "Health", "Retail", "Software"]

RESPONSIBILITIES = {
    "Data Analyst": ["You will build dashboards and reports for business teams.",
                     "You will turn raw data into clear insights for decision makers.",
                     "You will track KPIs and explain trends to stakeholders."],
    "Data Engineer": ["You will design and maintain scalable data pipelines.",
                      "You will build reliable batch and streaming data platforms.",
                      "You will own data quality across our warehouse."],
    "Analytics Engineer": ["You will build trusted, well-documented data models.",
                           "You will bridge the gap between data engineering and analytics."],
    "Data Scientist": ["You will build predictive models that drive product decisions.",
                       "You will run experiments and measure business impact."],
    "ML Engineer": ["You will take models from notebooks to production.",
                    "You will build and monitor model serving infrastructure."],
    "Backend Developer": ["You will build secure and scalable backend services.",
                          "You will design APIs used by millions of customers."],
    "Frontend Developer": ["You will build fast, accessible user interfaces.",
                           "You will turn designs into pixel-perfect web pages."],
    "Full Stack Developer": ["You will own features end to end, from database to UI.",
                             "You will ship product features quickly and safely."],
    "QA / Test Engineer": ["You will write automated test suites for our products.",
                           "You will make sure every release is bug free."],
    "DevOps / Cloud Engineer": ["You will automate infrastructure and deployments.",
                                "You will keep our platform highly available."],
    "Other": ["You will resolve customer technical issues.",
              "You will support internal teams with IT systems."],
}

WORK_MODES = ["On-site", "Onsite", "Work from office", "Hybrid", "hybrid", "Remote"]
SOURCES = ["portal_a", "portal_b", "portal_c", "company_careers_page"]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def indian_format(rupees: int) -> str:
    """600000 -> '6,00,000' (Indian digit grouping)."""
    s = str(rupees)
    if len(s) <= 3:
        return s
    last3, rest = s[-3:], s[:-3]
    groups = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return ",".join(groups) + "," + last3


def human_list(items):
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def pick_experience(level, country):
    table = EXPERIENCE if country == "India" else EXPERIENCE_INTL
    options = table
    if level == "entry":
        options = [e for e in table if e[1] <= 1]
    elif level == "senior":
        options = [e for e in table if e[1] >= 5]
    return random.choices(options, weights=[e[3] for e in options])[0]


def pick_skills(role, t):
    chosen = []
    for skill, prob in role["skills"].items():
        start, end = SKILL_TREND.get(skill, (1.0, 1.0))
        p = min(prob * (start + (end - start) * t), 0.98)
        if random.random() < p:
            chosen.append(skill)
    if not chosen:  # every posting mentions at least one skill
        chosen.append(max(role["skills"], key=role["skills"].get))
    random.shuffle(chosen)
    return chosen


def format_salary_india(mid_lpa):
    low = max(2, round(mid_lpa * random.uniform(0.80, 0.90)))
    high = max(low + 1, round(mid_lpa * random.uniform(1.10, 1.30)))
    r = random.random()
    if r < 0.25:
        return "Not disclosed"
    if r < 0.40:
        return f"₹ {indian_format(low * 100000)} - {indian_format(high * 100000)} PA"
    return f"{low}-{high} LPA"


def spaced(n):
    """45000 -> '45 000' (Scandinavian digit grouping)."""
    return f"{n:,}".replace(",", " ")


def dotted(n):
    """60000 -> '60.000' (German / Danish digit grouping)."""
    return f"{n:,}".replace(",", ".")


def format_salary_intl(country, yearly):
    """Write a yearly salary the way postings in that country usually do."""
    low_y = yearly * random.uniform(0.85, 0.92)
    high_y = yearly * random.uniform(1.08, 1.20)
    lo_m, hi_m = int(round(low_y / 12, -3)), int(round(high_y / 12, -3))   # monthly, to 1 000
    lo_y, hi_y = int(round(low_y, -3)), int(round(high_y, -3))             # yearly, to 1 000
    hi_m, hi_y = max(hi_m, lo_m + 1000), max(hi_y, lo_y + 1000)
    r = random.random()

    if country == "Sweden":          # pay is often hidden behind a collective agreement
        if r < 0.35:
            return random.choice(["Not disclosed", "Kollektivavtal", "Lön enligt överenskommelse"])
        if r < 0.70:
            return f"{spaced(lo_m)} - {spaced(hi_m)} kr/mån"
        if r < 0.90:
            return f"SEK {lo_m:,}-{hi_m:,} per month"
        return f"SEK {lo_y:,} - {hi_y:,} per year"
    if country == "Norway":
        if r < 0.35:
            return random.choice(["Not disclosed", "Competitive"])
        if r < 0.70:
            return f"NOK {spaced(lo_y)} - {spaced(hi_y)} per year"
        return f"kr {spaced(lo_m)} - {spaced(hi_m)} per måned"
    if country == "Denmark":
        if r < 0.35:
            return random.choice(["Not disclosed", "Competitive"])
        if r < 0.75:
            return f"DKK {dotted(lo_m)} - {dotted(hi_m)} pr. måned"
        return f"DKK {lo_y:,} - {hi_y:,} per year"
    if country == "Germany":
        if r < 0.40:
            return random.choice(["Not disclosed", "Competitive salary"])
        if r < 0.70:
            return f"{dotted(lo_y)} - {dotted(hi_y)} € p.a."
        if r < 0.90:
            return f"€{lo_y:,} - €{hi_y:,} per year"
        return f"€{lo_y // 1000}k - €{hi_y // 1000}k"
    if country == "Netherlands":
        if r < 0.30:
            return random.choice(["Not disclosed", "Competitive"])
        if r < 0.70:
            return f"€{lo_m:,} - €{hi_m:,} per month"
        return f"€{lo_y:,} - €{hi_y:,} per year"
    if country == "United Kingdom":
        if r < 0.20:
            return random.choice(["Competitive", "Not disclosed"])
        if r < 0.70:
            return f"£{lo_y:,} - £{hi_y:,} per annum"
        return f"£{lo_y // 1000}k - £{hi_y // 1000}k"
    # United States: many states require a salary range, so most postings show one
    if r < 0.15:
        return "Not disclosed"
    if r < 0.65:
        return f"${lo_y:,} - ${hi_y:,} a year"
    return f"${lo_y // 1000}K-${hi_y // 1000}K"


def build_description(title, company, role_name, skills, country):
    split = max(1, round(len(skills) * 0.6))
    must, nice = skills[:split], skills[split:]
    must_text = human_list([random.choice(SKILL_FORMS.get(s, [s])) for s in must])
    parts = [
        random.choice([
            f"{company} is hiring a {title}.",
            f"Join {company} as a {title}.",
            f"We are looking for a passionate {title} to join our growing team at {company}.",
        ] + ([f"{company} söker en {title}.", f"Vi söker nu en {title} till {company}."]
             if country == "Sweden" else [])),
        random.choice(RESPONSIBILITIES[role_name]),
        random.choice([
            f"Must have hands-on experience with {must_text}.",
            f"Required skills: {must_text}.",
            f"Strong knowledge of {must_text} is essential.",
        ]),
    ]
    if nice:
        nice_text = human_list([random.choice(SKILL_FORMS.get(s, [s])) for s in nice])
        parts.append(random.choice([
            f"Good to have: {nice_text}.",
            f"Exposure to {nice_text} is a plus.",
            f"Bonus points for {nice_text}.",
        ] + ([f"Meriterande: {nice_text}."] if country == "Sweden" else [])))
    parts.append(random.choice([
        "Immediate joiners preferred." if country == "India" else "Visa sponsorship available.",
        "We offer health insurance and flexible working hours.",
        "Great learning culture and mentorship.",
        "",
    ]))
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def generate(rows: int, seed: int, end_date: date):
    random.seed(seed)
    companies = [f"{p} {s}" for p in COMPANY_PREFIX for s in COMPANY_SUFFIX]
    random.shuffle(companies)
    companies = companies[:80]

    role_names = list(ROLES)
    role_weights = [ROLES[r]["weight"] for r in role_names]
    country_names = list(COUNTRIES)
    country_weights = [COUNTRIES[c]["weight"] for c in country_names]
    start_date = end_date - timedelta(days=364)

    records = []
    for i in range(1, rows + 1):
        # later dates slightly more likely -> hiring grows over the year
        t = random.random() ** 0.85
        posted = start_date + timedelta(days=int(t * 364))

        role_name = random.choices(role_names, weights=role_weights)[0]
        role = ROLES[role_name]
        title, level = random.choice(role["titles"])
        country = random.choices(country_names, weights=country_weights)[0]
        cinfo = COUNTRIES[country]
        exp_text, exp_min, exp_max, _ = pick_experience(level, country)
        skills = pick_skills(role, t)

        city_names = list(cinfo["cities"])
        city = random.choices(city_names, weights=[cinfo["cities"][c][0] for c in city_names])[0]
        _, city_bonus, spellings = cinfo["cities"][city]
        location = random.choice(spellings)
        work_mode = "Remote" if city == "Remote" else random.choice(WORK_MODES)

        # salary model in LPA (India scale), then converted to each country's level
        base_lpa = role["base_salary"] + role["per_year"] * (exp_min + exp_max) / 2
        skill_lpa = sum(SKILL_PREMIUM.get(s, 0) for s in skills)
        noise = random.uniform(0.85, 1.15)
        if country == "India":
            salary_text = format_salary_india((base_lpa + skill_lpa) * noise * city_bonus)
        else:
            # pay is less spread out abroad than in India -> compress role + experience,
            # then add the skill premium on top as a percentage (1 LPA of premium = +5%),
            # so in-demand skills (Snowflake +9%, GenAI +12.5% ...) still pay more
            yearly = (cinfo["target_mid"] * (base_lpa * noise / INDIA_REFERENCE_LPA) ** 0.4
                      * (1 + 0.05 * skill_lpa) * city_bonus)
            salary_text = format_salary_intl(country, yearly)

        # messy formatting
        posted_text = (posted.strftime("%d-%m-%Y") if random.random() < 0.10
                       else posted.isoformat())
        raw_title = f"  {title} " if random.random() < 0.05 else title
        company = random.choice(companies)

        records.append({
            "job_id": f"JOB{i:06d}",
            "job_title": raw_title,
            "company_name": company,
            "location": location,
            "experience_required": exp_text,
            "salary_range": salary_text,
            "work_mode": work_mode,
            "posted_date": posted_text,
            "job_description": build_description(title, company, role_name, skills, country),
            "source_site": random.choice(SOURCES),
        })

    # ~4% duplicates: the same job scraped twice (dbt staging removes them)
    dupes = random.sample(records, k=int(rows * 0.04))
    records.extend(dict(d) for d in dupes)
    random.shuffle(records)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=12000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent.parent / "data" / "job_postings.csv")
    args = parser.parse_args()

    records = generate(args.rows, args.seed, date.today())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(records)
    print(f"Wrote {len(records)} rows to {args.out}")


if __name__ == "__main__":
    main()
