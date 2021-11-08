
from django.http import HttpResponse, JsonResponse
from django.views import View

class VendorIndexAPI(View):
    """
    docstring
    """
    def get(self, request, *args, **kwargs):
        print('index api')
        return HttpResponse('<h1>Welcome to vendor APIs<h1>')