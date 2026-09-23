from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'pages'

urlpatterns = [
    path('contact-us/', views.contact_us, name='contact_us'),
    path('faq/', TemplateView.as_view(template_name='pages/faq.html'), name='faq'),
    path('our-mission/', TemplateView.as_view(template_name='pages/our_mission.html'), name='our_mission'),
    path('refund-policy/', TemplateView.as_view(template_name='pages/refund_policy.html'), name='refund_policy'),
    path('exchange-policy/', TemplateView.as_view(template_name='pages/exchange_policy.html'), name='exchange_policy'),
    path('privacy-policy/', TemplateView.as_view(template_name='pages/privacy_policy.html'), name='privacy_policy'),
    path('terms-and-conditions/', TemplateView.as_view(template_name='pages/terms_conditions.html'), name='terms_conditions'),
    path('submit-review/', views.submit_review, name='submit_review'),
]