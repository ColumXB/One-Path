from django.http import HttpResponse

def landing(request):
    return render(request, "core/landing.html")

def hello_world(request):
    return HttpResponse("Hello, World!")
