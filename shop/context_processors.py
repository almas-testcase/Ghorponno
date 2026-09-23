from .models import Category
from .cart import Cart
from django.conf import settings

def categories(request):
    return {
        'nav_categories': Category.objects.all()
    }

def cart(request):
    return {
        'cart': Cart(request)
    }


def meta_pixel(request):
    return {'META_PIXEL_ID': settings.META_PIXEL_ID}
