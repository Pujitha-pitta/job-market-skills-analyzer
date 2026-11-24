{#
    Map a messy job title ("Sr. Data Engineer II", "Systemutvecklare", "IT-tekniker" ...)
    to a clean role family. English and Swedish titles.
    Order matters: the most specific rules come first.
#}
{% macro classify_role(title) %}
    case
        when {{ title }} ilike '%analytics engineer%'                               then 'Analytics Engineer'
        when {{ title }} ilike any ('%machine learning%', '%ml engineer%', '%ai engineer%', '%ai-utvecklare%',
                                    '%ai-ingenjör%', '%ai developer%', '%mlops%')     then 'ML Engineer'
        when {{ title }} ilike '%data scien%'                                        then 'Data Scientist'
        when {{ title }} ilike any ('%data engineer%', '%dataingenjör%', '%etl developer%', '%etl-utvecklare%',
                                    '%data platform engineer%')                      then 'Data Engineer'
        when {{ title }} ilike any ('%data analyst%', '%dataanalytiker%', '%business analyst%', '%bi analyst%',
                                    '%bi developer%', '%bi-utvecklare%', '%bi-analytiker%', '%bi-specialist%',
                                    '%verksamhetsanalytiker%', '%analytiker%')       then 'Data Analyst'
        when {{ title }} ilike any ('%security%', '%säkerhet%', '%soc analyst%', '%pentest%')
                                                                                     then 'Cyber Security'
        when {{ title }} ilike any ('%projektledare%', '%project manager%', '%scrum master%', '%product owner%',
                                    '%produktägare%', '%delivery manager%', '%agile coach%')
                                                                                     then 'IT Project Manager'
        when {{ title }} ilike any ('%arkitekt%', '%architect%')                      then 'Architect'
        when {{ title }} ilike any ('%ux%', '%ui designer%', '%designer%')             then 'UX / Design'
        when {{ title }} ilike any ('%embedded%', '%inbyggda%', '%firmware%')         then 'Embedded Developer'
        when {{ title }} ilike any ('%full stack%', '%full-stack%', '%fullstack%', '%mern%')
                                                                                     then 'Full Stack Developer'
        when {{ title }} ilike any ('%front%end%', '%react developer%', '%ui developer%', '%webbutvecklare%')
                                                                                     then 'Frontend Developer'
        when {{ title }} ilike any ('%qa %', '%qa', '%test%', '%sdet%', '%kvalitetssäkr%')
                                                                                     then 'QA / Test Engineer'
        when {{ title }} ilike any ('%devops%', '%cloud%', '%moln%', '%site reliability%', '%sre%',
                                    '%platform engineer%', '%plattform%')           then 'DevOps / Cloud Engineer'
        when {{ title }} ilike any ('%it-tekniker%', '%it tekniker%', '%support%', '%nätverk%', '%network%',
                                    '%drift%', '%server%', '%systemadministrat%', '%tekniker%', '%technician%',
                                    '%infrastruktur%', '%infrastructure%', '%helpdesk%', '%servicedesk%',
                                    '%service desk%', '%systemspecialist%')          then 'IT Support & Infrastructure'
        when {{ title }} ilike any ('%affärsutvecklare%', '%business developer%', '%verksamhetsutvecklare%')
                                                                                     then 'Other'
        when {{ title }} ilike any ('%backend%', '%back end%', '%back-end%', '%java developer%', '%javautvecklare%',
                                    '%python developer%', '%software engineer%', '%software developer%',
                                    '%systemutvecklare%', '%mjukvaruutvecklare%', '%utvecklare%', '%developer%',
                                    '%programmerare%', '%engineer%', '%ingenjör%')   then 'Backend Developer'
        else 'Other'
    end
{% endmacro %}
