from flask import Flask, request, jsonify, render_template, session, abort
import tripoli
import requests
import ujson as json

JSON_TYPE = 0
TEXT_TYPE = 1

app = Flask(__name__)
app.config['json_encoder'] = json

with open('secret_key', 'rb') as f:
    app.secret_key = f.read()


class NetworkError(Exception):
    def __index__(self, err):
        self.err = err


class ParseError(Exception):
    def __index__(self, err):
        self.err = err


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
    try:
        resp = requests.get(manifest_url)
    except Exception as e:
        raise NetworkError(e)
    try:
        man = json.loads(resp.text)
    except Exception as e:
        raise ParseError(e)
    return man


@app.route('/', methods=['GET'])
def index():
    manifest_url = request.args.get('manifest')

    if manifest_url:
        return validate_manifest(manifest_url)
    else:
        return index_get()


def index_get():
    val = {"message": "GET with query parameter 'manifest' to validate.",
           "version": tripoli.tripoli.__version__}
    return val_with_content_type(val, 'index.html')


def validate_manifest(manifest_url):
    if manifest_url:
        try:
            man = fetch_manifest(manifest_url)
        except NetworkError as e:
            resp = jsonify({"message": "Could not retrieve json at '{}'".format(manifest_url)})
            resp.status_code = 400
            return resp
        except ParseError as e:
            resp = jsonify({"message": "Could not parse json at '{}'".format(manifest_url)})
            resp.status_code = 400
            return resp

        iv = tripoli.IIIFValidator()
        iv.fail_fast = False
        iv.logger.setLevel("CRITICAL")
        iv.validate(man)

        resp = {"errors": [str(err) for err in sorted(iv.errors)],
                "warnings": [str(warn) for warn in sorted(iv.warnings)],
                "is_valid": iv.is_valid,
                "manifest_url": manifest_url,
                "version": tripoli.tripoli.__version__}
        return val_with_content_type(resp, 'index.html')

if __name__ == "__main__":
    app.run()
