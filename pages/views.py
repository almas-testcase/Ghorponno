from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ContactMessage, Review



def contact_us(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        ContactMessage.objects.create(name=name, email=email, message=message)
        messages.success(request, 'Thank you! Your message has been sent successfully. We will get back to you soon.')
        return redirect('pages:contact_us')

    return render(request, 'pages/contact_us.html')



@require_POST
def submit_review(request):
    name = request.POST.get('name', '').strip()
    rating = request.POST.get('rating', 5)
    comment = request.POST.get('comment', '').strip()

    if name and comment:
        Review.objects.create(name=name, rating=rating, comment=comment)
        return JsonResponse({
            'success': True,
            'message': 'ধন্যবাদ! আপনার রিভিউ যাচাইয়ের পর দেখানো হবে।'
        })
    return JsonResponse({'success': False, 'message': 'সব ফিল্ড পূরণ করুন।'})




def custom_404(request, exception):
    return render(request, 'pages/404.html', status=404)

def custom_500(request):
    return render(request, 'pages/500.html', status=500)