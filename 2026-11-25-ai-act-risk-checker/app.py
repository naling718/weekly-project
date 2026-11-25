from flask import Flask, jsonify, render_template_string, request

from classifier import classify

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Act Risk Checker</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 16px;line-height:1.5;color:#1d1d1f}
 textarea{width:100%;min-height:8rem;font:inherit;padding:.5rem;box-sizing:border-box}
 button{font:inherit;padding:.5rem 1.2rem;margin-top:.5rem}
 .tier{display:inline-block;padding:.2rem .7rem;border-radius:4px;font-weight:700;color:#fff}
 .unacceptable{background:#b00020}.high{background:#c25e00}.limited{background:#1f6fb2}.minimal{background:#2e7d32}
 .note{color:#555;font-size:.9rem}
</style></head><body>
<h1>EU AI Act risk checker</h1>
<p class="note">Describe an AI system in plain English. This is a keyword-based first pass, not legal advice.</p>
<form method="post">
 <label for="d">AI system description</label>
 <textarea id="d" name="description" maxlength="5000" required>{{ description }}</textarea>
 <button type="submit">Check risk tier</button>
</form>
{% if error %}<p role="alert">{{ error }}</p>{% endif %}
{% if result %}
<h2>Tier: <span class="tier {{ result.tier }}">{{ result.tier|upper }}</span></h2>
{% if result.matches %}<h3>Why</h3><ul>
{% for m in result.matches %}<li><b>{{ m.ref }}</b> {{ m.title }}. Matched "{{ m.evidence }}".</li>{% endfor %}
</ul>{% else %}<p>No rule matched, so it falls under minimal risk.</p>{% endif %}
<h3>What applies</h3><ul>{% for o in result.obligations %}<li>{{ o }}</li>{% endfor %}</ul>
{% endif %}
</body></html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    description, result, error = "", None, None
    if request.method == "POST":
        description = request.form.get("description", "")
        try:
            result = classify(description)
        except ValueError as e:
            error = str(e)
    return render_template_string(PAGE, description=description, result=result, error=error)


@app.post("/api/classify")
def api_classify():
    body = request.get_json(silent=True) or {}
    try:
        return jsonify(classify(body.get("description")))
    except ValueError as e:
        return jsonify(error=str(e)), 400


if __name__ == "__main__":
    app.run(debug=False, port=5000)
