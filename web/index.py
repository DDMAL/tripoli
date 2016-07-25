from flask import Flask, request, jsonify, render_template
from tripoli import IIIFValidator
import requests
import ujson as json

JSON_TYPE = 0
TEXT_TYPE = 1

app = Flask(__name__)
app.config['json_encoder'] = json


def val_with_content_type(value, template):
    """Return either json or text/html with value dict."""
    mimes = request.accept_mimetypes
    json_score = mimes['application/json'] if 'application/json' in mimes else 0
    text_html_score = mimes['text/html'] if 'text/html' in mimes else 0
    if json_score > text_html_score:
        return jsonify(value)
    else:
        return render_template(template, **value)


def fetch_manifest(manifest_url):
    resp = requests.get(manifest_url)
    man = json.loads(resp.text)
    return man


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return index_post()
    if request.method == 'GET':
        return index_get()


def index_get():
    val = {"message": "POST with key 'manifest' to validate."}
    return val_with_content_type(val, 'index.html')


def index_post():
    if request.content_type == 'application/json':
        manifest_url = request.json.get("manifest")
    else:
        manifest_url = request.form.get('manifest')

    if manifest_url:
        try:
            man = fetch_manifest(manifest_url)
        except Exception as e:
            return jsonify({"exception": str(e)})

        iv = IIIFValidator()
        iv.fail_fast = False
        iv.logger.setLevel("CRITICAL")
        iv.validate(man)

        resp = {"errors": [str(err) for err in iv.errors],
                "warnings": [str(warn) for warn in iv.warnings],
                "is_valid": iv.is_valid,
                "manifest_url": manifest_url}
        return val_with_content_type(resp, 'index.html')
    return jsonify({'exception': "Missing 'manifest' key in request."})

if __name__ == "__main__":
    app.run()