from fastapi import FastAPI
from pydantic import BaseModel
import json


app = FastAPI()



class RunRequest(BaseModel):
    budget_tokens:int
    steps:list



# -----------------------------
# Canonicalize arguments
# -----------------------------

def normalize(obj):

    if isinstance(obj, dict):

        result={}

        for k in sorted(obj.keys()):

            if k == "client_ts":
                continue

            result[k]=normalize(obj[k])


        return result


    elif isinstance(obj,list):

        return [
            normalize(x)
            for x in obj
        ]


    elif isinstance(obj,str):

        return " ".join(
            obj.split()
        )


    else:

        return obj



def call_signature(step):

    return (
        step.get("tool"),
        json.dumps(
            normalize(step.get("args",{})),
            sort_keys=True
        )
    )



# -----------------------------
# Detect same call 3 times
# -----------------------------

def repeated_three(steps):

    if len(steps)<3:
        return False


    last3=steps[-3:]


    sigs=[
        call_signature(x)
        for x in last3
    ]


    return (
        sigs[0]==sigs[1]==sigs[2]
    )



# -----------------------------
# Detect A B cycle
# -----------------------------

def detect_cycle(steps):

    if len(steps)<6:
        return False


    last6=steps[-6:]


    sigs=[
        call_signature(x)
        for x in last6
    ]


    return (
        sigs[0]==sigs[2]==sigs[4]
        and
        sigs[1]==sigs[3]==sigs[5]
        and
        sigs[0]!=sigs[1]
    )




# -----------------------------
# API
# -----------------------------

@app.post("/")
def guard(req:RunRequest):


    steps=req.steps

    budget=req.budget_tokens



    total=sum(
        step.get(
            "tokens_used",
            0
        )
        for step in steps
    )


    # Budget check first

    if total >= budget:

        return {
            "decision":"halt",
            "reason":
            f"Cumulative tokens_used ({total}) has reached the budget ({budget})."
        }



    # Loop checks

    if repeated_three(steps):

        return {
            "decision":"halt",
            "reason":
            "Detected repeated identical tool calls."
        }



    if detect_cycle(steps):

        return {
            "decision":"halt",
            "reason":
            "Detected repeating two-step tool cycle."
        }



    return {

        "decision":"continue",

        "reason":
        "Within budget and no loop detected."

    }



@app.get("/")
def home():

    return {
        "status":"running"
    }