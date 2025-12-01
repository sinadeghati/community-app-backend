from django .http import HttpResponse

def home(request):
    return HttpResponse("به صفحه اصلی اپلیکیشن ایرانی خوش آمدید!")  