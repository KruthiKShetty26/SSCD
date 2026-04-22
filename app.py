from flask import Flask, request, jsonify
from flask_cors import CORS
from myparser import parse

app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/analyze', methods=['POST'])
def analyze():
    data   = request.get_json(force=True)
    source = data.get('source', '').strip()
    if not source:
        return jsonify({'error': 'Empty source code'}), 400
    try:
        symbols, errors, tokens = parse(source)
    except Exception as e:
        return jsonify({'error': f'Parse error: {str(e)}'}), 500
    stats = {
        'total':      len(symbols),
        'variables':  sum(1 for s in symbols if s['kind'] == 'variable'),
        'functions':  sum(1 for s in symbols if s['kind'] == 'function'),
        'parameters': sum(1 for s in symbols if s['kind'] == 'parameter'),
    }
    return jsonify({'symbols': symbols, 'tokens': tokens, 'errors': errors, 'stats': stats})

if __name__ == '__main__':
    print("Backend running on http://localhost:5000")
    app.run(debug=True, port=5000)