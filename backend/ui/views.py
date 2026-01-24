from django.shortcuts import render

# Create your views here.
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

FASTAPI_URL = "http://127.0.0.1:8001/predict"

def register_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        User.objects.create_user(username=username, password=password)
        return redirect("login")

    return render(request, "ui/register.html")


def login_view(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST["username"],
            password=request.POST["password"],
        )
        if user:
            login(request, user)
            return redirect("journal")

    return render(request, "ui/login.html")


@login_required
def journal_view(request):
    emotions = None

    if request.method == "POST":
        text = request.POST["text"]

        r = requests.post(FASTAPI_URL, json={"text": text})
        emotions = r.json()

    return render(
        request,
        "ui/journal.html",
        {"emotions": emotions},
    )
