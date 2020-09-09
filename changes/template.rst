
Upgrade instructions are available at
https://docs.funkwhale.audio/admin/upgrading.html

{% for section, _ in sections.items() %}
{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section]%}
{{ definitions[category]['name'] }}:

{% if definitions[category]['showcontent'] %}
{% for text in sections[section][category].keys()|sort() %}
- {{ text }}
{% endfor %}

{% else %}
- {{ sections[section][category]['']|join(', ') }}

{% endif %}
{% if sections[section][category]|length == 0 %}
No significant changes.

{% else %}
{% endif %}

{% endfor %}
{% else %}
No significant changes.


{% endif %}
{% endfor %}
