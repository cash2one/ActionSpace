from django.http import HttpResponse
# from django.shortcuts import render


# Create your views here.
def index(_):
    return HttpResponse("<script language='javascript'>document.location = 'om/'</script>")
