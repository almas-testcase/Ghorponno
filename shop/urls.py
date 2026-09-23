from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),  

    # Cart URLs
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),

    # Checkout URLs
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),

    # Promo code URLs
    path('apply-promo/', views.apply_promo, name='apply_promo'),      
    path('remove-promo/', views.remove_promo, name='remove_promo'),      

    # Track Order URL
    path('track-order/', views.track_order, name='track_order'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'), 
    path('set-delivery-area/', views.set_delivery_area, name='set_delivery_area'),
    path('combo-offers/', views.combo_offers, name='combo_offers'),

]