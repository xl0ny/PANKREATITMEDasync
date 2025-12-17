from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from zoneinfo import ZoneInfo

import time
import random
import requests
import json

from concurrent import futures



CALLBACK_URL = "http://localhost:80/api/"
STATUS = ['completed', 'rejected']
MODER = {
	"login": "moderEvgeniy",
	"password": "mypass"
}
JWT = ''
KEY = 'A9F3C47E2B8D1C6A'

executor = futures.ThreadPoolExecutor(max_workers=3)

def get_JWT(force=False):
    global JWT
    if JWT is not None and not force: return JWT
    aurl = str(CALLBACK_URL+"users/auth/login")
    JWT = requests.post(aurl, timeout=3, json=MODER).json()["access_token"]
    return JWT

    
def get_ranson_score_and_mortality_risk(id):
    get_JWT()
    print(JWT)
    HEADERS = {"Authorization": "Bearer " + JWT}
    nurl = str(CALLBACK_URL+"pankreatitorders/"+str(id))
    resp = requests.get(nurl, timeout=3, headers=HEADERS)
    if resp.status_code == 401:
        get_JWT(force=True)  # принудительно обновляем токен
        HEADERS["Authorization"] = f"Bearer {JWT}"
        resp = requests.get(nurl, timeout=3, headers=HEADERS)
    result = resp.json()
    # print(result)
    ranson_score = sum([(int(i["value_num"]) if i["value_num"] is not None else 0) > int(i["criterion"]["RefHigh"]) if i["criterion"]["RefHigh"] is not None else (int(i["value_num"]) if i["value_num"] is not None else 0) < int(i["criterion"]["RefLow"]) for i in result["criteria"]])
    mortality_risk = ranson_score * 100 / 11
    return {
      "ranson_score": ranson_score,
      "mortality_risk": str(round(mortality_risk)) + "%"
    }


def get_random_status(id):
    time.sleep(5)
    ranson_score_and_mortality_risk = get_ranson_score_and_mortality_risk(id)
    return {
      "id": id,
      "status": STATUS[random.randint(0, 1)],
      "finished_at": datetime.now(ZoneInfo("Europe/Moscow")).isoformat(),
      "ranson_score": ranson_score_and_mortality_risk["ranson_score"],
      "mortality_risk": ranson_score_and_mortality_risk["mortality_risk"],
      "key": KEY
    }

def status_callback(task):
    try:
      result = task.result()
      print(result)
    except futures._base.CancelledError:
      return
    
    nurl = str(CALLBACK_URL+"setranson")

    resp = requests.put(nurl, data=json.dumps(task.result()), timeout=3)
    print(resp.status_code)
    print(resp.text)

@api_view(['POST'])
def set_status(request):
    if "id" in request.data.keys():   
        id = request.data["id"]        

        task = executor.submit(get_random_status, id)
        task.add_done_callback(status_callback)        
        return Response(status=status.HTTP_200_OK)
    return Response(status=status.HTTP_400_BAD_REQUEST)
