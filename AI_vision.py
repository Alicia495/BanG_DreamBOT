import json
import requests

def AI_judge(image_path):
    url="https://bangdreammain-prediction.cognitiveservices.azure.com/customvision/v3.0/Prediction/6455ec24-120e-4f80-8aa9-57ca95b08ba7/classify/iterations/Iteration9/image"
    headers={'content-type':'application/octet-stream','Prediction-Key':'c436d26eafa04bec80123d7b77cc970d'}
    response =requests.post(url,data=open(image_path,"rb"),headers=headers)
    response.raise_for_status()

    analysis = response.json()

    name, pred = analysis["predictions"][0]["tagName"], analysis["predictions"][0]["probability"]
    print(name, pred)
    if(name == "illust"):
        return pred
    
    name, pred = analysis["predictions"][1]["tagName"], analysis["predictions"][1]["probability"]
    print(name, pred)
    if(name == "illust"):
        return pred
    

