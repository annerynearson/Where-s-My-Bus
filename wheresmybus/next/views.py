import re
import logging

from django.shortcuts import render_to_response, get_object_or_404
from django.core.context_processors import csrf
from django.template import RequestContext
from django.template.loader import render_to_string
from django.http import HttpResponseBadRequest

from wheresmybus.next.models import Stop
from wheresmybus.next.urls import STOP_ID_REGEX

# = max_distance (in m) / 110 977
MAX_DISTANCE = 0.0009010
# Max number of stops
NUMBER_OF_STOPS = 4

STOP_ID_RE = re.compile("(" + STOP_ID_REGEX + ")")
LINE_ID_REGEX = re.compile(r"((?:\b\d{2}\b)|(?:\b\w\b))")

logger = logging.getLogger("wheresmybus")


def for_stop_id(request, stop_id):
    if stop_id:
        s = get_object_or_404(Stop, stop_id=stop_id)
        s.update_predictions()

        predictions_content = render_to_string("predictions.html", {"stops": (s, )})

        return render_to_response("for_stop_id.html", {"predictions_content": predictions_content},
            context_instance=RequestContext(request))


def api_for_stop_id(request, stop_id):
    if stop_id:
        print stop_id
        s = get_object_or_404(Stop, stop_id=stop_id)
        s.update_predictions()

        return render_to_response("predictions.html", {"stops": (s, )})


def api_for_location(request):
    lat = request.POST.get("lat", "")
    lon = request.POST.get("lon", "")

    try:
        here = {"lat": float(lat), "lon": float(lon)}
    except:
        return HttpResponseBadRequest("Can't understand lat and lon.")

    # Find stops in the neighborhood (about 100 m)
    stops = Stop.objects.raw_query({"loc": {'$near': here}, "maxDistance": MAX_DISTANCE})[:NUMBER_OF_STOPS*2]

    # If there are no stops, find nearest stops (max NUMBER_OF_STOPS)
    if len(stops) == 0:
        stops = Stop.objects.raw_query({"loc": {'$near': here}})[:NUMBER_OF_STOPS]

    for s in stops:
        s.update_predictions()

    if len(stops) == 0:
        logger.warning("There maybe no stops in the database. See documentation to install them.")

    return render_to_response("predictions.html", {"stops": stops})


def home(request):
    c = {}
    c = c.update(csrf(request))
    return render_to_response("index.html", c, context_instance=RequestContext(request))


def debug(request):
    return render_to_response("debug.html", {}, context_instance=RequestContext(request))
