from fastapi import FastAPI
from pydantic import BaseModel
import json


app = FastAPI()


class RunRequest(BaseModel):
    budget_tokens: int
    steps: list



# -----------------------------
# Normalize arguments
# -----------------------------

def normalize(obj):

    if isinstance(obj, dict):

        new = {}

        for k in sorted(obj.keys()):

            # ignore tracing field
            if k == "client_ts":
                continue

            new[k] = normalize(obj[k])

        return new


    elif isinstance(obj, list):

        return [
            normalize(x)
            for x in obj
        ]


    elif isinstance(obj, str):

        # remove whitespace differences
        return " ".join(obj.split())


    else:
        return obj



def signature(step):

    return (
        step.get("tool"),
        json.dumps(
            normalize(step.get("args", {})),
            sort_keys=True
        )
    )



# -----------------------------
# Same call 3+ times
# -----------------------------

def three_repeat(steps):

    if len(steps) < 3:
        return False


    sigs = [
        signature(x)
        for x in steps
    ]


    return (
        sigs[-1] == sigs[-2]
        and
        sigs[-2] == sigs[-3]
    )



# -----------------------------
# A B A B A B cycle
# -----------------------------

def period_two_loop(steps):

    if len(steps) < 6:
        return False


    last = steps[-6:]


    s = [
        signature(x)
        for x in last
    ]


    return (
        s[0] == s[2] == s[4]
        and
        s[1] == s[3] == s[5]
        and
        s[0] != s[1]
    )



# -----------------------------
# Main decision
# -----------------------------


@app.post("/")
def guard(req: RunRequest):


    steps=req.steps

    budget=req.budget_tokens


    total=sum(
        int(
            x.get(
                "tokens_used",
                0
            )
        )
        for x in steps
    )


    # budget always wins

    if total >= budget:

        return {
            "decision":"halt",
            "reason":
            f"Cumulative tokens_used ({total}) has reached the budget ({budget})."
        }



    # loop detection

    if three_repeat(steps):

        return {
            "decision":"halt",
            "reason":
            "Detected three identical consecutive tool calls."
        }



    if period_two_loop(steps):

        return {
            "decision":"halt",
            "reason":
            "Detected repeating two-step cycle."
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