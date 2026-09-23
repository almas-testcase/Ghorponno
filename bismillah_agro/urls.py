from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse

from shop.models import Product, Category


handler404 = 'pages.views.custom_404'
handler500 = 'pages.views.custom_500'


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    def items(self):
        return Product.objects.filter(is_active=True)
    def location(self, obj):
        return f'/product/{obj.slug}/'


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    def items(self):
        return Category.objects.all()
    def location(self, obj):
        return f'/category/{obj.slug}/'


sitemaps = {'products': ProductSitemap, 'categories': CategorySitemap}


def robots_txt(request):
    return HttpResponse(
        "User-agent: *\nAllow: /\nSitemap: https://www.ghorponyo.com/sitemap.xml\n",
        content_type="text/plain"
    )


urlpatterns = [
    path('user_error_admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('', include('shop.urls')),
    path('', include('pages.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)