# app.py
import os
from flask import Flask, send_file, abort

application = Flask(__name__)


@application.route("/covid/<path:subtypes>")
def get_covid_data(subtypes):
    data_file = os.path.join(application.root_path, "data", "covid", subtypes)
    if os.path.exists(data_file):
        return send_file(data_file)
    else:
        abort(404)


if __name__ == "__main__":
    application.run(debug=True)
